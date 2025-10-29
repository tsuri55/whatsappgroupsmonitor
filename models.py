"""Database models for WhatsApp Groups Monitor."""
from datetime import datetime
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession


class Group(SQLModel, table=True):
    """WhatsApp group model."""

    __tablename__ = "groups"

    id: Optional[int] = Field(default=None, primary_key=True)
    group_jid: str = Field(unique=True, index=True, description="WhatsApp Group JID")
    group_name: Optional[str] = Field(default=None, description="Group name")
    managed: bool = Field(default=True, description="Whether to monitor this group")
    last_summary_sync: datetime = Field(
        default_factory=datetime.now, description="Last time summary was sent"
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    messages: list["Message"] = Relationship(back_populates="group")

    async def get_messages_since_last_summary(
        self, session: AsyncSession, exclude_sender_jid: Optional[str] = None
    ) -> list["Message"]:
        """Get all messages since last summary."""
        query = (
            select(Message)
            .where(Message.group_jid == self.group_jid)
            .where(Message.timestamp >= self.last_summary_sync)
            .order_by(Message.timestamp.asc())
        )

        if exclude_sender_jid:
            query = query.where(Message.sender_jid != exclude_sender_jid)

        result = await session.exec(query)
        return list(result.all())

    async def get_messages_today(
        self, session: AsyncSession, exclude_sender_jid: Optional[str] = None
    ) -> list["Message"]:
        """Get all messages from today (00:00 to now)."""
        # Get start of today at 00:00
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        query = (
            select(Message)
            .where(Message.group_jid == self.group_jid)
            .where(Message.timestamp >= today_start)
            .order_by(Message.timestamp.asc())
        )

        if exclude_sender_jid:
            query = query.where(Message.sender_jid != exclude_sender_jid)

        result = await session.exec(query)
        return list(result.all())


class Message(SQLModel, table=True):
    """WhatsApp message model."""

    __tablename__ = "messages"

    id: Optional[int] = Field(default=None, primary_key=True)
    message_id: str = Field(unique=True, index=True, description="WhatsApp Message ID")
    group_jid: str = Field(foreign_key="groups.group_jid", index=True)
    sender_jid: str = Field(index=True, description="Sender's WhatsApp JID")
    sender_name: Optional[str] = Field(default=None, description="Sender's display name")
    content: str = Field(description="Message content")
    message_type: str = Field(default="text", description="Message type (text, image, etc.)")
    timestamp: datetime = Field(default_factory=datetime.now, index=True)
    created_at: datetime = Field(default_factory=datetime.now)

    # Relationships
    group: Optional[Group] = Relationship(back_populates="messages")


class SummaryLog(SQLModel, table=True):
    """Log of generated summaries."""

    __tablename__ = "summary_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    group_jid: str = Field(foreign_key="groups.group_jid", index=True)
    summary_text: str = Field(description="Generated summary")
    message_count: int = Field(description="Number of messages summarized")
    start_time: datetime = Field(description="Start of summarized period")
    end_time: datetime = Field(description="End of summarized period")
    sent_successfully: bool = Field(default=False, description="Whether summary was sent")
    error_message: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
