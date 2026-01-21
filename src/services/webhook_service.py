# src/services/webhook_service.py

import uuid
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.db_models import tb_r_ticket_customer_mapping
from database.db_helper import get_ticket_from_db, save_ticket_to_db
from schema import JiraWebhookPayload, JiraWebhookResponse

class WebhookService:
    """Service layer for processing Jira webhooks."""
    
    def __init__(self, db_session: AsyncSession, logger: logging.Logger):
        self.db_session = db_session
        self.logger = logger
    
    async def process_webhook(
        self,
        payload: JiraWebhookPayload,
        triggered_by_user: Optional[str] = None,
    ) -> JiraWebhookResponse:
        """
        Process incoming Jira webhook.
        
        Args:
            payload: Jira webhook payload
            triggered_by_user: Optional user ID from query parameter
            
        Returns:
            JiraWebhookResponse with processing result
        """
        # Extract basic information
        project_key, project_name = self.extract_project_info(payload)
        user_name = self.extract_ticket_fields_v2(payload.user, "displayName")
        is_closed = self.is_transition_to_close(payload.changelog)
        issue_key = self.extract_ticket_fields_v2(payload.issue, "key")
        
        self.logger.info(
            "Received Jira webhook: issue_key=%s - status=%s - project=%s - triggeredByUser=%s - userName=%s",
            issue_key,
            is_closed,
            project_key,
            triggered_by_user,
            user_name,
        )

        if not issue_key:
            self.logger.info("Ignoring webhook: Received webhook with missing issue key")
            return self._create_response(
                status="ignored",
                message="Missing issue key"
            )
        
        # Rule 1: Only process 'Close' transitions
        if not is_closed:
            self.logger.info(
                "Ignoring webhook: ticket %s not transitioned to 'Close'",
                issue_key
            )
            return self._create_response(
                status="ignored",
                message="Not a transition to 'Close' status",
                issue_key=issue_key,
                project_key=project_key,
                project_name=project_name,
                user_name=user_name,
            )
        
        # Rule 2: Check for duplicate (idempotency)
        existing_ticket = await get_ticket_from_db(
            ticket_key=issue_key,
            session=self.db_session
        )
        
        if existing_ticket:
            self.logger.info(
                "Ignoring webhook: ticket %s already exists.",
                issue_key
            )
            return self._create_response(
                status="ignored",
                message=f"Ticket {issue_key} already exists in database",
                issue_key=issue_key,
                project_key=project_key,
                project_name=project_name,
                user_name=user_name,
            )
        
        # Extract and save ticket
        return await self._save_new_ticket(
            payload=payload,
            issue_key=issue_key,
            project_key=project_key,
            project_name=project_name,
            user_name=user_name,
        )
    
    async def _save_new_ticket(
        self,
        payload: JiraWebhookPayload,
        issue_key: str,
        project_key: Optional[str],
        project_name: Optional[str],
        user_name: Optional[str],
    ) -> JiraWebhookResponse:
        """Save new ticket to database."""
        try:
            ticket_data = self.extract_ticket_fields(payload, issue_key)
            
            mapping_id = str(uuid.uuid4())
            new_ticket = tb_r_ticket_customer_mapping(
                mapping_id=mapping_id,
                ticket_key=issue_key,
                customer_id=ticket_data["customer_id"],
                customer_phone=ticket_data["customer_phone"],
                transaction_id=ticket_data["transaction_id"],
                ticket_summary=ticket_data["ticket_summary"],
                ticket_url=ticket_data["ticket_url"],
                priority=ticket_data["priority"],
                intention_type=0,
                complaint_data=payload.issue,
                close_notified=True,
                close_notified_on=datetime.now(),
                close_notified_by=user_name,
            )
            
            saved_ticket = await save_ticket_to_db(
                ticket=new_ticket,
                session=self.db_session
            )
            
            self.logger.info(
                "Successfully processed and saved ticket %s to database",
                issue_key,
            )
            
            return self._create_response(
                status="processed",
                message="Webhook processed and ticket saved successfully",
                issue_key=issue_key,
                project_key=project_key,
                project_name=project_name,
                user_name=user_name,
                saved_at=saved_ticket.created_on.isoformat(),
            )
            
        except Exception as e:
            self.logger.error(
                "Error while saving ticket %s: %s",
                issue_key, str(e)
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": f"Error while saving ticket: {str(e)}",
                    "issueKey": issue_key,
                }
            )
    
    def _create_response(
        self,
        status: str,
        message: str,
        issue_key: Optional[str] = None,
        project_key: Optional[str] = None,
        project_name: Optional[str] = None,
        user_name: Optional[str] = None,
        saved_at: Optional[datetime] = None,
    ) -> JiraWebhookResponse:
        """Create standardized webhook response."""
        return JiraWebhookResponse(
            status=status,
            message=message,
            issueKey=issue_key,
            projectKey=project_key,
            projectName=project_name,
            triggeredByUser=user_name,
            savedAt=saved_at if saved_at else None,
        )
    
    def is_transition_to_close(self, changelog: Optional[Dict[str, Any]]) -> bool:
        """
        Check if the webhook represents a transition to 'Close' status.
        
        Args:
            changelog: The changelog object from webhook payload
            
        Returns:
            True if status changed to 'Close', False otherwise
        """
        if not changelog:
            return False
        
        for item in changelog.get("items", []):
            field = (item.get("field") or "").lower()
            field_id = (item.get("fieldId") or "").lower()
            to_string = item.get("toString")
            
            if (field == "status" or field_id == "status") and to_string == "Close":
                return True
        
        return False

    def extract_project_info(self, payload: JiraWebhookPayload) -> Tuple[Optional[str], Optional[str]]:
        """
        Extract project key and name from payload.
        
        Returns:
            Tuple of (project_key, project_name)
        """
        fields = payload.issue.get("fields", {})
        project = fields.get("project", {})
        
        if isinstance(project, dict):
            return project.get("key"), project.get("name")
        
        return None, None

    def extract_priority(self, fields: Dict[str, Any]) -> str:
        """Extract priority from fields."""
        priority_obj = fields.get("priority", {})
        if isinstance(priority_obj, dict):
            return priority_obj.get("name", "Unknown")
        return "Unknown"

    def extract_ticket_fields(self, payload: JiraWebhookPayload, issue_key: str) -> Dict[str, Any]:
        """
        Extract all relevant ticket fields from payload.
        
        Returns:
            Dictionary containing all extracted fields
        """
        fields = payload.issue.get("fields", {})
        
        return {
            "customer_id": (
                self.extract_ticket_fields_v2(fields, "customfield_10496") or  # might be customer code
                self.extract_ticket_fields_v2(fields, "customfield_10019") or  # might contain customer info
                self.extract_ticket_fields_v2(fields, "customfield_11227") or  # Fallback to user Customer ID
                "UNKNOWN"
            ),
            "customer_phone": self.extract_ticket_fields_v2(fields, "customfield_11227"),
            "transaction_id": self.extract_ticket_fields_v2(fields, "customfield_11226"),
            "ticket_summary": self.extract_ticket_fields_v2(fields, "summary"),
            "ticket_url": payload.issue.get("self", f"https://inovasidayasolusimultibiller.atlassian.net/browse/{issue_key}"),
            "priority": self.extract_priority(fields),
        }

    def extract_ticket_fields_v2(self, fields: Dict[str, Any], key: str) -> Dict[str, Any] | str:
        return fields.get(key)
