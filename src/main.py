# src/main.py

from typing import Any, Dict, Optional
import uvicorn
import uuid
import logging
from fastapi import Body, Depends, FastAPI, Query, Request, HTTPException
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from schema import JiraWebhookPayload, JiraWebhookResponse
from database.db_session import get_db_session, init_db
from services.webhook_service import WebhookService
from utils.loggingUtils import RequestIDMiddleware, configure_logging

configure_logging(log_level="INFO")
logger = logging.getLogger("Main")

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

def extract_project(fields: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    project = fields.get("project", {})
    if isinstance(project, dict):
        return project.get("key"), project.get("name")
    return None, None


def extract_user_name(payload: JiraWebhookPayload) -> Optional[str]:
    if isinstance(payload.user, dict):
        return payload.user.get("displayName")
    return None

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
    service = WebhookService(db_session=db_session, logger=logger)
    
    try:
        response = await service.process_webhook(
            payload=payload,
            triggered_by_user=triggered_by_user
        )
        return response
        
    except HTTPException:
        # Re-raise HTTP exceptions from service layer
        raise
    except Exception as e:
        logger.error(
            "Unexpected error processing webhook: %s",
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": "Internal server error occurred",
            }
        )

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000)

