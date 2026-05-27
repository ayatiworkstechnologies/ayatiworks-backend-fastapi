"""
AI bot management models for Bot-as-a-Service.
"""

from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, BaseModel


class AIBot(BaseModel, AuditMixin):
    """Configurable chatbot definition."""

    __tablename__ = "ai_bots"

    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)
    name = Column(String(150), nullable=False)
    slug = Column(String(160), nullable=False, unique=True, index=True)
    industry = Column(String(100), nullable=True, index=True)
    description = Column(Text, nullable=True)
    tone = Column(String(50), nullable=False, default="friendly")
    personality = Column(String(100), nullable=True)
    system_prompt = Column(Text, nullable=False)
    welcome_message = Column(Text, nullable=True)
    primary_color = Column(String(20), nullable=True)
    logo_url = Column(String(500), nullable=True)
    ui_config = Column(JSON, nullable=True)
    enabled_plugins = Column(JSON, nullable=True)
    supported_languages = Column(JSON, nullable=True)
    is_published = Column(Boolean, nullable=False, default=False)

    knowledge_sources = relationship(
        "BotKnowledgeSource",
        back_populates="bot",
        cascade="all, delete-orphan",
    )
    conversations = relationship(
        "BotConversation",
        back_populates="bot",
        cascade="all, delete-orphan",
    )


class BotKnowledgeSource(BaseModel, AuditMixin):
    """Knowledge source attached to a bot."""

    __tablename__ = "bot_knowledge_sources"

    bot_id = Column(Integer, ForeignKey("ai_bots.id", ondelete="CASCADE"), nullable=False, index=True)
    source_type = Column(String(50), nullable=False)  # faq, pdf, website, text
    title = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=True)
    website_url = Column(String(500), nullable=True)
    raw_text = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="ready")
    embedding_provider = Column(String(100), nullable=True)
    embedding_reference = Column(String(255), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    bot = relationship("AIBot", back_populates="knowledge_sources")
    chunks = relationship(
        "BotKnowledgeChunk",
        back_populates="source",
        cascade="all, delete-orphan",
    )


class BotKnowledgeChunk(BaseModel, AuditMixin):
    """Chunked knowledge used for retrieval."""

    __tablename__ = "bot_knowledge_chunks"

    bot_id = Column(Integer, ForeignKey("ai_bots.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(Integer, ForeignKey("bot_knowledge_sources.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(JSON, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)

    source = relationship("BotKnowledgeSource", back_populates="chunks")


class BotConversation(BaseModel, AuditMixin):
    """Conversation session for a bot."""

    __tablename__ = "bot_conversations"

    bot_id = Column(Integer, ForeignKey("ai_bots.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    visitor_name = Column(String(150), nullable=True)
    visitor_email = Column(String(255), nullable=True)
    channel = Column(String(50), nullable=False, default="web")
    language = Column(String(20), nullable=False, default="en")
    mood = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True)
    last_message_at = Column(DateTime, nullable=True)

    bot = relationship("AIBot", back_populates="conversations")
    messages = relationship(
        "BotMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )


class BotMessage(BaseModel, AuditMixin):
    """Message within a conversation."""

    __tablename__ = "bot_messages"

    conversation_id = Column(Integer, ForeignKey("bot_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user / assistant / system
    content = Column(Text, nullable=False)
    detected_mood = Column(String(50), nullable=True)
    message_metadata = Column(JSON, nullable=True)
    token_count = Column(Integer, nullable=True)

    conversation = relationship("BotConversation", back_populates="messages")
