# src/main/main.py

from typing import Any, Dict, Optional
import uvicorn
import uuid
import logging
from fastapi import Body, Depends, FastAPI, Query, Request, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from database.db_session import get_db_session, init_db
from database.db_models import tb_r_ticket_customer_mapping
from database.db_helper import get_ticket_from_db, save_ticket_to_db
from utils.loggingUtils import RequestIDMiddleware, configure_logging

configure_logging(log_level="INFO")
logger = logging.getLogger("Main")
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
# )

class JiraWebhookPayload(BaseModel):
    timestamp: int
    webhookEvent: str
    issue_event_type_name: Optional[str] = None
    user: Dict[str, Any]
    issue: Dict[str, Any]
    changelog: Optional[Dict[str, Any]] = None

class JiraWebhookResponse(BaseModel):
    status: str
    message: str
    issueKey: Optional[str] = None
    projectKey: Optional[str] = None
    projectName: Optional[str] = None
    triggeredByUser: Optional[str] = None
    savedAt: Optional[str] = None

# @app.on_event("startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    try:
        await init_db()
        logger.info("✅ Database initialized")
        yield
    finally:
        logger.info("✅ Database closed")

app = FastAPI(
    lifespan=lifespan,
    title="Jira Webhook Receiver",
    description="Simple FastAPI application to receive Jira webhooks.",
    version="1.0.0",
)
app.add_middleware(RequestIDMiddleware)

def transitioned_to_close(changelog: dict | None) -> bool:
    if not changelog:
        return False
    for it in changelog.get("items", []):
        field = (it.get("field") or "").lower()
        field_id = (it.get("fieldId") or "").lower()
        to_string = it.get("toString")
        if (field == "status" or field_id == "status") and to_string == "Close":
            return True
    return False


@app.post("/jira-webhook", response_model=JiraWebhookResponse)
async def jira_webhook(
    request: Request,
    triggered_by_user: Optional[str] = Query(
        default=None,
        alias="triggeredByUser",
        description="Optional user identifier passed as query param",
    ),
    payload: JiraWebhookPayload = Body(...),
    db_session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Endpoint to receive Jira webhooks.
    
    Business Logic:
    1. Only process if status is 'Close'
    2. Ignore if ticket key already exists in database
    
    Example final URL (on your VPS) to configure in Jira:
    https://your-domain-or-ip/jira-webhook?triggeredByUser=641d629d9d6383e32a3342b8
    """

    headers = dict(request.headers)
    webhook_id = request.headers.get("X-Atlassian-Webhook-Identifier")
    # Extract issue information safely
    issue_key = payload.issue.get("key")
    if not issue_key:
        logger.warning("Received webhook with missing issue key")
        return {"status": "ignored", "message": "Missing issue key"}
    fields = payload.issue.get("fields", {})
    
    # Safely extract status
    issue_status = transitioned_to_close(payload.changelog)
    
    project = fields.get("project", {})
    project_key = project.get("key") if isinstance(project, dict) else None
    project_name = project.get("name") if isinstance(project, dict) else None
    user_name = payload.user.get("displayName") if payload.user else None

    logger.info(
        "Received Jira webhook: issue_key=%s - status=%s - project=%s - triggeredByUser=%s - userName=%s",
        issue_key,
        issue_status,
        project_key,
        triggered_by_user,
        user_name,
    )

    # Use Case 1: Ignore if status is not 'Close'
    if not issue_status:
        logger.info(
            "Ignoring webhook: status '%s' is not 'Close' for ticket %s",
            issue_status,
            issue_key,
        )
        return {
            "status": "ignored",
            "message": f"Not a transition to 'Close'. Webhook ignored.",
            "issueKey": issue_key,
        }

    # Use Case 2: Check if ticket already exists in database
    if issue_key:
        existing_ticket = await get_ticket_from_db(ticket_key=issue_key, session=db_session)
        
        if existing_ticket:
            logger.info(
                "Ignoring webhook: ticket %s already exists in database (created: %s)",
                issue_key,
                existing_ticket.created_on,
            )
            return JiraWebhookResponse(
                status="ignored",
                message=f"Ticket {issue_key} already exists in database. Webhook ignored.",
                issueKey=issue_key
            )

    # Extract additional fields from Jira payload
    ticket_summary = fields.get("summary", "")
    issue_self = payload.issue.get("self", "")
    
    # Construct ticket URL (fallback to self URL or build from key)
    ticket_url = issue_self or f"https://inovasidayasolusimultibiller.atlassian.net/browse/{issue_key}"
    
    # Extract priority
    priority_obj = fields.get("priority", {})
    priority = priority_obj.get("name", "Unknown") if isinstance(priority_obj, dict) else "Unknown"
    
    # Extract transaction_id from custom field (customfield_11226 = Trx Id)
    transaction_id = fields.get("customfield_11226")
    # Try to extract customer_id from various possible sources
    customer_id = (
        fields.get("customfield_10496") or  # might be customer code
        fields.get("customfield_10019") or  # might contain customer info
        fields.get("customfield_11227") or  # Fallback to user Customer ID
        "UNKNOWN"
    )
    
    # extract customer_phone
    customer_phone = fields.get("customfield_11227", None)
    intention_type = 0
    
    # Process the webhook: Save ticket to database
    try:
        mapping_id = str(uuid.uuid4())
        
        new_ticket = await save_ticket_to_db(
            ticket=tb_r_ticket_customer_mapping(
                mapping_id=mapping_id,
                ticket_key=issue_key,
                customer_id=customer_id,
                customer_phone=customer_phone,
                transaction_id=transaction_id,
                ticket_summary=ticket_summary,
                ticket_url=ticket_url,
                priority=priority,
                intention_type=intention_type,
                complaint_data=payload.issue,
                close_notified=True,
                close_notified_on=datetime.now(),
                close_notified_by=user_name,
            ),
            session=db_session,
        )
        
        logger.info(
            "Successfully processed and saved ticket %s (mapping_id: %s) to database",
            issue_key,
            new_ticket.mapping_id,
        )
        
        client_host = request.client.host if request.client else None
        
        return {
            "status": "processed",
            "message": "Jira webhook received and ticket saved to database",
            "webhookEvent": payload.webhookEvent,
            "issueKey": issue_key,
            "projectKey": project_key,
            "projectName": project_name,
            "triggeredByUser": triggered_by_user,
            "clientHost": client_host,
            "mappingId": new_ticket.mapping_id,
            "savedAt": new_ticket.created_on.isoformat(),
        }
    except Exception as e:
        logger.error(
            "Error saving ticket %s to database: %s",
            issue_key,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
        status_code=500,
        detail={
            "status": "error",
            "message": f"Internal error: {str(e)}",
            "issueKey": issue_key,
        }
    )

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000)

