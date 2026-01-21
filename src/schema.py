from pydantic import BaseModel
from typing import Optional, Dict, Any

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