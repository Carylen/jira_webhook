# src/database/db_helper.py
from database.db_session import get_db_session
from database.db_models import tb_r_ticket_customer_mapping
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)

async def save_ticket_to_db(ticket: tb_r_ticket_customer_mapping, session: AsyncSession):
    try:
        session.add(ticket)
        await session.commit()
        await session.refresh(ticket)
        return ticket
    except Exception as e:
        await session.rollback()
        logger.error(f"Error saving ticket to database: {e}")
        raise e

async def get_ticket_from_db(ticket_key: str, session: AsyncSession):
    try:
        result = await session.execute(select(tb_r_ticket_customer_mapping).where(tb_r_ticket_customer_mapping.ticket_key == ticket_key))
        existing_ticket = result.scalar_one_or_none()
        if existing_ticket:
            return existing_ticket
        else:
            return None
    except Exception as e:
        logger.error(f"Error getting ticket from database: {e}")
        raise e
