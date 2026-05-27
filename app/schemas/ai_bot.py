"""Schemas for Bot-as-a-Service module."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import AuditSchema


class BotBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    slug: str = Field(..., min_length=1, max_length=160)
    industry: str | None = Field(None, max_length=100)
    description: str | None = None
    tone: str = Field(default="friendly", max_length=50)
    personality: str | None = Field(None, max_length=100)
    system_prompt: str | None = Field(None, min_length=10)
    welcome_message: str | None = None
    primary_color: str | None = Field(None, max_length=20)
    logo_url: str | None = Field(None, max_length=500)
    ui_config: dict[str, Any] | None = None
    enabled_plugins: list[str] = Field(default_factory=list)
    supported_languages: list[str] = Field(default_factory=lambda: ["en"])
    is_published: bool = False


class BotCreate(BotBase):
    company_id: int | None = None


class BotUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=150)
    slug: str | None = Field(None, min_length=1, max_length=160)
    industry: str | None = Field(None, max_length=100)
    description: str | None = None
    tone: str | None = Field(None, max_length=50)
    personality: str | None = Field(None, max_length=100)
    system_prompt: str | None = Field(None, min_length=10)
    welcome_message: str | None = None
    primary_color: str | None = Field(None, max_length=20)
    logo_url: str | None = Field(None, max_length=500)
    ui_config: dict[str, Any] | None = None
    enabled_plugins: list[str] | None = None
    supported_languages: list[str] | None = None
    is_published: bool | None = None
    is_active: bool | None = None


class BotListResponse(BaseModel):
    id: int
    company_id: int | None = None
    name: str
    slug: str
    industry: str | None = None
    tone: str
    personality: str | None = None
    primary_color: str | None = None
    is_published: bool
    is_active: bool
    knowledge_source_count: int = 0
    conversation_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BotResponse(BotBase, AuditSchema):
    id: int
    company_id: int | None = None
    is_active: bool
    knowledge_source_count: int = 0
    conversation_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BotKnowledgeBase(BaseModel):
    source_type: str = Field(..., min_length=1, max_length=50)
    title: str = Field(..., min_length=1, max_length=255)
    file_url: str | None = Field(None, max_length=500)
    website_url: str | None = Field(None, max_length=500)
    raw_text: str | None = None
    status: str = Field(default="ready", max_length=50)
    embedding_provider: str | None = Field(None, max_length=100)
    embedding_reference: str | None = Field(None, max_length=255)
    metadata_json: dict[str, Any] | None = None


class BotKnowledgeCreate(BotKnowledgeBase):
    pass


class BotKnowledgeUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    file_url: str | None = Field(None, max_length=500)
    website_url: str | None = Field(None, max_length=500)
    raw_text: str | None = None
    status: str | None = Field(None, max_length=50)
    embedding_provider: str | None = Field(None, max_length=100)
    embedding_reference: str | None = Field(None, max_length=255)
    metadata_json: dict[str, Any] | None = None
    is_active: bool | None = None


class BotKnowledgeResponse(BotKnowledgeBase, AuditSchema):
    id: int
    bot_id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class BotConversationCreate(BaseModel):
    visitor_name: str | None = Field(None, max_length=150)
    visitor_email: str | None = Field(None, max_length=255)
    channel: str = Field(default="web", max_length=50)
    language: str = Field(default="en", max_length=20)
    mood: str | None = Field(None, max_length=50)


class BotConversationResponse(AuditSchema):
    id: int
    bot_id: int
    user_id: int | None = None
    visitor_name: str | None = None
    visitor_email: str | None = None
    channel: str
    language: str
    mood: str | None = None
    summary: str | None = None
    last_message_at: datetime | None = None
    is_active: bool
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class BotMessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    detected_mood: str | None = Field(None, max_length=50)
    message_metadata: dict[str, Any] | None = None


class BotMessageResponse(AuditSchema):
    id: int
    conversation_id: int
    role: str
    content: str
    detected_mood: str | None = None
    message_metadata: dict[str, Any] | None = None
    token_count: int | None = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class BotChatResponse(BaseModel):
    user_message: BotMessageResponse
    assistant_message: BotMessageResponse


class BotAnalyticsResponse(BaseModel):
    total_bots: int
    published_bots: int
    total_conversations: int
    total_messages: int
    top_industries: list[dict[str, Any]]


class PublicBotResponse(BaseModel):
    id: int
    name: str
    slug: str
    industry: str | None = None
    description: str | None = None
    tone: str
    personality: str | None = None
    welcome_message: str | None = None
    primary_color: str | None = None
    logo_url: str | None = None
    supported_languages: list[str] = []

    model_config = ConfigDict(from_attributes=True)
