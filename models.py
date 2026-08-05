"""Pydantic models for type-safe ticket and message data."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# Type aliases for better readability
TicketStatus = Literal["open", "in_progress", "resolved", "closed"]
TicketPriority = Literal["low", "medium", "high", "urgent"]
TicketCategory = Literal["bug", "feature", "support", "question", "other"]


class TicketBase(BaseModel):
    """Base model for ticket data."""

    title: str = Field(..., min_length=3, max_length=200, description="Ticker symbol")
    status: TicketStatus = "open"
    priority: TicketPriority = "medium"
    category: Optional[TicketCategory] = None
    created_by: str = Field(..., min_length=2, max_length=100)
    last_price: float = Field(..., ge=0, description="Stock last price (required, can be 0)")

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, v: str) -> str:
        """Ensure title is not just whitespace."""
        if not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip().upper()  # Normalize to uppercase (AAPL, MSFT, etc.)

    @field_validator("last_price")
    @classmethod
    def price_reasonable(cls, v: float) -> float:
        """Warn if price seems unreasonable."""
        if v > 1_000_000:
            raise ValueError("Price seems unreasonably high (> $1,000,000)")
        return v

    @field_validator("created_by")
    @classmethod
    def created_by_not_empty(cls, v: str) -> str:
        """Ensure creator name is valid."""
        if not v.strip():
            raise ValueError("Creator name cannot be empty")
        return v.strip()


class TicketCreate(TicketBase):
    """Model for creating a new ticket."""

    pass


class TicketUpdate(BaseModel):
    """Model for updating an existing ticket (all fields optional for PATCH-style updates)."""

    title: Optional[str] = Field(None, min_length=3, max_length=200)
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None
    last_price: Optional[float] = Field(None, ge=0)

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty_if_provided(cls, v: Optional[str]) -> Optional[str]:
        """If title is provided, ensure it's not empty."""
        if v is not None and not v.strip():
            raise ValueError("Title cannot be empty or whitespace")
        return v.strip().upper() if v else None

    @field_validator("last_price")
    @classmethod
    def price_reasonable_if_provided(cls, v: Optional[float]) -> Optional[float]:
        """If price is provided, ensure it's reasonable."""
        if v is not None and v > 1_000_000:
            raise ValueError("Price seems unreasonably high (> $1,000,000)")
        return v


class Ticket(TicketBase):
    ticket_id: str 
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True, "populate_by_name": True}


class MessageCreate(BaseModel):
    """Model for creating a new message."""

    message_text: str = Field(..., min_length=1, max_length=5000)
    author: str = Field(..., min_length=2, max_length=100)

    @field_validator("message_text")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Message cannot be empty or whitespace")
        return v.strip()

    @field_validator("author")
    @classmethod
    def author_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Author name cannot be empty")
        return v.strip()


class Message(MessageCreate):
    message_id: str 
    ticket_id: str
    message_text: str 
    created_at: datetime
    model_config = {"from_attributes": True, "populate_by_name": True}


class TicketStats(BaseModel):
    """Statistics about tickets."""

    total: int
    open: int
    in_progress: int
    resolved: int
    closed: int
    by_priority: dict[str, int]
    by_category: dict[str, int]
