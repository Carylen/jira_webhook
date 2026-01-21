# # src/utils/extractors.py

# """
# Utility functions for extracting data from Jira webhook payloads.
# """

# from typing import Optional, Dict, Any, Tuple

# from schemas import JiraWebhookPayload
# from utils.constants import (
#     JIRA_BASE_URL,
#     CUSTOM_FIELD_TRANSACTION_ID,
#     CUSTOM_FIELD_CUSTOMER_PHONE,
#     CUSTOM_FIELD_CUSTOMER_ID_PRIMARY,
#     CUSTOM_FIELD_CUSTOMER_ID_SECONDARY,
#     CUSTOM_FIELD_CUSTOMER_ID_TERTIARY,
# )


# def is_transition_to_close(changelog: Optional[Dict[str, Any]]) -> bool:
#     """
#     Check if the webhook represents a transition to 'Close' status.
    
#     Args:
#         changelog: The changelog object from webhook payload
        
#     Returns:
#         True if status changed to 'Close', False otherwise
#     """
#     if not changelog:
#         return False
    
#     for item in changelog.get("items", []):
#         field = (item.get("field") or "").lower()
#         field_id = (item.get("fieldId") or "").lower()
#         to_string = item.get("toString")
        
#         if (field == "status" or field_id == "status") and to_string == "Close":
#             return True
    
#     return False


# def extract_issue_key(payload: JiraWebhookPayload) -> Optional[str]:
#     """Extract issue key from payload."""
#     return payload.issue.get("key")


# def extract_project_info(payload: JiraWebhookPayload) -> Tuple[Optional[str], Optional[str]]:
#     """
#     Extract project key and name from payload.
    
#     Returns:
#         Tuple of (project_key, project_name)
#     """
#     fields = payload.issue.get("fields", {})
#     project = fields.get("project", {})
    
#     if isinstance(project, dict):
#         return project.get("key"), project.get("name")
    
#     return None, None


# def extract_user_name(payload: JiraWebhookPayload) -> Optional[str]:
#     """Extract user display name from payload."""
#     if isinstance(payload.user, dict):
#         return payload.user.get("displayName")
#     return None


# def extract_customer_id(fields: Dict[str, Any]) -> str:
#     """
#     Extract customer ID from custom fields with fallback logic.
    
#     Priority order:
#     1. customfield_10496 (customer code)
#     2. customfield_10019 (customer info)
#     3. customfield_11227 (customer ID)
#     4. "UNKNOWN" as last resort
#     """
#     return (
#         fields.get(CUSTOM_FIELD_CUSTOMER_ID_PRIMARY) or
#         fields.get(CUSTOM_FIELD_CUSTOMER_ID_SECONDARY) or
#         fields.get(CUSTOM_FIELD_CUSTOMER_ID_TERTIARY) or
#         "UNKNOWN"
#     )


# def extract_priority(fields: Dict[str, Any]) -> str:
#     """Extract priority from fields."""
#     priority_obj = fields.get("priority", {})
#     if isinstance(priority_obj, dict):
#         return priority_obj.get("name", "Unknown")
#     return "Unknown"


# def extract_ticket_url(issue: Dict[str, Any], issue_key: str) -> str:
#     """
#     Extract or construct ticket URL.
    
#     Args:
#         issue: Issue object from payload
#         issue_key: The issue key (e.g., "SDO-123")
        
#     Returns:
#         Full URL to the Jira ticket
#     """
#     # Try to get from 'self' field first
#     issue_self = issue.get("self", "")
#     if issue_self:
#         return issue_self
    
#     # Fallback: construct URL from base URL and key
#     return f"{JIRA_BASE_URL}/browse/{issue_key}"


# def extract_ticket_fields(payload: JiraWebhookPayload, issue_key: str) -> Dict[str, Any]:
#     """
#     Extract all relevant ticket fields from payload.
    
#     Returns:
#         Dictionary containing all extracted fields
#     """
#     fields = payload.issue.get("fields", {})
    
#     return {
#         "customer_id": extract_customer_id(fields),
#         "customer_phone": fields.get(CUSTOM_FIELD_CUSTOMER_PHONE),
#         "transaction_id": fields.get(CUSTOM_FIELD_TRANSACTION_ID),
#         "ticket_summary": fields.get("summary", ""),
#         "ticket_url": extract_ticket_url(payload.issue, issue_key),
#         "priority": extract_priority(fields),
#     }