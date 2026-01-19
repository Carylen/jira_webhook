"""
Database models for Jira webhook receiver
"""
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy import Column, DateTime, JSON, TEXT, text
from sqlmodel import SQLModel, Field


class tb_r_ticket_customer_mapping(SQLModel, table=True):
    """Table To Map Jira Tickets to Customers Who Make Complaints"""
    __tablename__ = "tb_r_ticket_customer_mapping"
    
    mapping_id: str = Field(primary_key=True, max_length=36)
    ticket_key: str = Field(max_length=50, unique=True, index=True)
    customer_id: str = Field(max_length=255)
    customer_phone: Optional[str] = Field(max_length=50, default=None)
    transaction_id: Optional[str] = Field(max_length=255, default=None)
    ticket_summary: str = Field(sa_type=TEXT)
    ticket_url: str = Field(max_length=500)
    priority: Optional[str] = Field(max_length=50, default=None)
    intention_type: int = Field()
    complaint_data: Dict = Field(sa_column=Column(JSON, nullable=False))
    created_on: datetime = Field(
        sa_column=Column[datetime](
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP")
        )
    )
    updated_on: datetime = Field(
        sa_column=Column[datetime](
            DateTime,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP"),
            onupdate=text("CURRENT_TIMESTAMP")
        )
    )
    close_notified: bool = Field(default=False)
    close_notified_on: Optional[datetime] = Field(default=None)
    close_notified_by: Optional[str] = Field(default=None)
