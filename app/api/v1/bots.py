"""
Bot-as-a-Service API endpoints.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import PermissionChecker, get_current_active_user
from app.database import get_db
from app.models.ai_bot import AIBot, BotConversation, BotKnowledgeSource, BotMessage
from app.models.auth import User
from app.schemas.ai_bot import (
    BotAnalyticsResponse,
    BotChatResponse,
    BotConversationCreate,
    BotConversationResponse,
    BotCreate,
    BotKnowledgeCreate,
    BotKnowledgeResponse,
    BotKnowledgeUpdate,
    BotListResponse,
    BotMessageCreate,
    BotMessageResponse,
    BotResponse,
    BotUpdate,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services.bot_ai_service import BotAIService

router = APIRouter(prefix="/bots", tags=["Bots"])


def _build_system_prompt(
    name: str,
    tone: str | None,
    personality: str | None,
    industry: str | None,
) -> str:
    tone_value = tone or "friendly"
    personality_value = personality or "helpful"
    industry_value = industry or "general"
    return (
        f"You are {name}, a {tone_value} {personality_value} assistant for the {industry_value} industry. "
        "Answer clearly, stay on-brand, and guide users toward the most helpful next step."
    )


def _serialize_bot(bot: AIBot, db: Session) -> BotResponse:
    knowledge_count = db.query(BotKnowledgeSource).filter(
        BotKnowledgeSource.bot_id == bot.id,
        BotKnowledgeSource.is_deleted == False,
    ).count()
    conversation_count = db.query(BotConversation).filter(
        BotConversation.bot_id == bot.id,
        BotConversation.is_deleted == False,
    ).count()

    response = BotResponse.model_validate(bot)
    response.knowledge_source_count = knowledge_count
    response.conversation_count = conversation_count
    return response


def _serialize_bot_list(bot: AIBot, db: Session) -> BotListResponse:
    response = BotListResponse.model_validate(bot)
    response.knowledge_source_count = db.query(BotKnowledgeSource).filter(
        BotKnowledgeSource.bot_id == bot.id,
        BotKnowledgeSource.is_deleted == False,
    ).count()
    response.conversation_count = db.query(BotConversation).filter(
        BotConversation.bot_id == bot.id,
        BotConversation.is_deleted == False,
    ).count()
    return response


def _build_assistant_reply(bot: AIBot, user_message: str, mood: str | None) -> str:
    tone = (bot.tone or "friendly").lower()
    personality = bot.personality or "helpful"
    mood_hint = f" I noticed a {mood} mood and adjusted the tone accordingly." if mood else ""

    if tone == "spiritual":
        prefix = "Let's take this one calm step at a time."
    elif tone == "professional":
        prefix = "Here is a clear, structured response."
    elif tone == "expert":
        prefix = "Based on the configured knowledge and workflow,"
    else:
        prefix = "Happy to help."

    return (
        f"{prefix} I'm acting as {bot.name} with a {personality} personality.{mood_hint} "
        f"You asked: \"{user_message}\". This MVP module stores the conversation and is ready "
        f"for your real LLM + RAG integration to replace this generated placeholder."
    )


@router.get("", response_model=PaginatedResponse[BotListResponse])
def list_bots(
    search: str | None = None,
    industry: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(PermissionChecker("bot.view")),
    db: Session = Depends(get_db),
):
    """List configurable bots."""
    query = db.query(AIBot).filter(AIBot.is_deleted == False)

    if industry:
        query = query.filter(AIBot.industry == industry)
    if search:
        like = f"%{search}%"
        query = query.filter(
            (AIBot.name.ilike(like)) |
            (AIBot.slug.ilike(like)) |
            (AIBot.industry.ilike(like))
        )

    total = query.count()
    bots = query.order_by(AIBot.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [_serialize_bot_list(bot, db) for bot in bots]
    return PaginatedResponse.create(items, total, page, page_size)


@router.get("/analytics/summary", response_model=BotAnalyticsResponse)
def get_bot_analytics(
    current_user: User = Depends(PermissionChecker("bot.view")),
    db: Session = Depends(get_db),
):
    """Get lightweight bot analytics."""
    total_bots = db.query(AIBot).filter(AIBot.is_deleted == False).count()
    published_bots = db.query(AIBot).filter(
        AIBot.is_deleted == False,
        AIBot.is_published == True,
    ).count()
    total_conversations = db.query(BotConversation).filter(BotConversation.is_deleted == False).count()
    total_messages = db.query(BotMessage).filter(BotMessage.is_deleted == False).count()
    industries = db.query(
        AIBot.industry,
        func.count(AIBot.id).label("count"),
    ).filter(
        AIBot.is_deleted == False,
        AIBot.industry.isnot(None),
    ).group_by(AIBot.industry).order_by(func.count(AIBot.id).desc()).limit(5).all()

    return BotAnalyticsResponse(
        total_bots=total_bots,
        published_bots=published_bots,
        total_conversations=total_conversations,
        total_messages=total_messages,
        top_industries=[
            {"industry": industry, "count": count}
            for industry, count in industries
        ],
    )


@router.get("/{bot_id}", response_model=BotResponse)
def get_bot(
    bot_id: int,
    current_user: User = Depends(PermissionChecker("bot.view")),
    db: Session = Depends(get_db),
):
    """Get bot details."""
    bot = db.query(AIBot).filter(AIBot.id == bot_id, AIBot.is_deleted == False).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    return _serialize_bot(bot, db)


@router.post("", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
def create_bot(
    payload: BotCreate,
    current_user: User = Depends(PermissionChecker("bot.create")),
    db: Session = Depends(get_db),
):
    """Create a new bot."""
    existing = db.query(AIBot).filter(AIBot.slug == payload.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bot slug already exists")

    system_prompt = payload.system_prompt
    if not system_prompt or len(system_prompt.strip()) < 10:
        system_prompt = _build_system_prompt(
            payload.name,
            payload.tone,
            payload.personality,
            payload.industry,
        )

    bot = AIBot(
        **payload.model_dump(exclude={"system_prompt"}),
        system_prompt=system_prompt,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return _serialize_bot(bot, db)


@router.put("/{bot_id}", response_model=BotResponse)
def update_bot(
    bot_id: int,
    payload: BotUpdate,
    current_user: User = Depends(PermissionChecker("bot.edit")),
    db: Session = Depends(get_db),
):
    """Update an existing bot."""
    bot = db.query(AIBot).filter(AIBot.id == bot_id, AIBot.is_deleted == False).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    update_data = payload.model_dump(exclude_unset=True)
    if "slug" in update_data:
        slug_owner = db.query(AIBot).filter(
            AIBot.slug == update_data["slug"],
            AIBot.id != bot_id,
        ).first()
        if slug_owner:
            raise HTTPException(status_code=400, detail="Bot slug already exists")

    if "system_prompt" in update_data and (
        not update_data["system_prompt"] or len(update_data["system_prompt"].strip()) < 10
    ):
        update_data["system_prompt"] = _build_system_prompt(
            update_data.get("name", bot.name),
            update_data.get("tone", bot.tone),
            update_data.get("personality", bot.personality),
            update_data.get("industry", bot.industry),
        )

    for field, value in update_data.items():
        setattr(bot, field, value)
    bot.updated_by = current_user.id

    db.add(bot)
    db.commit()
    db.refresh(bot)
    return _serialize_bot(bot, db)


@router.delete("/{bot_id}", response_model=MessageResponse)
def delete_bot(
    bot_id: int,
    current_user: User = Depends(PermissionChecker("bot.delete")),
    db: Session = Depends(get_db),
):
    """Soft delete a bot."""
    bot = db.query(AIBot).filter(AIBot.id == bot_id, AIBot.is_deleted == False).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    bot.soft_delete(current_user.id)
    bot.updated_by = current_user.id
    db.add(bot)
    db.commit()
    return MessageResponse(message="Bot deleted successfully")


@router.get("/{bot_id}/knowledge", response_model=list[BotKnowledgeResponse])
def list_bot_knowledge(
    bot_id: int,
    current_user: User = Depends(PermissionChecker("bot.view")),
    db: Session = Depends(get_db),
):
    """List knowledge sources for a bot."""
    return db.query(BotKnowledgeSource).filter(
        BotKnowledgeSource.bot_id == bot_id,
        BotKnowledgeSource.is_deleted == False,
    ).order_by(BotKnowledgeSource.created_at.desc()).all()


@router.post("/{bot_id}/knowledge", response_model=BotKnowledgeResponse, status_code=status.HTTP_201_CREATED)
def create_bot_knowledge(
    bot_id: int,
    payload: BotKnowledgeCreate,
    current_user: User = Depends(PermissionChecker("bot.edit")),
    db: Session = Depends(get_db),
):
    """Add a knowledge source to a bot."""
    bot = db.query(AIBot).filter(AIBot.id == bot_id, AIBot.is_deleted == False).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    knowledge = BotKnowledgeSource(
        bot_id=bot_id,
        **payload.model_dump(),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(knowledge)
    db.commit()
    db.refresh(knowledge)
    service = BotAIService(db)
    import asyncio
    asyncio.run(service.sync_knowledge_source(knowledge, current_user.id))
    db.refresh(knowledge)
    return knowledge


@router.put("/{bot_id}/knowledge/{knowledge_id}", response_model=BotKnowledgeResponse)
def update_bot_knowledge(
    bot_id: int,
    knowledge_id: int,
    payload: BotKnowledgeUpdate,
    current_user: User = Depends(PermissionChecker("bot.edit")),
    db: Session = Depends(get_db),
):
    """Update a knowledge source."""
    knowledge = db.query(BotKnowledgeSource).filter(
        BotKnowledgeSource.id == knowledge_id,
        BotKnowledgeSource.bot_id == bot_id,
        BotKnowledgeSource.is_deleted == False,
    ).first()
    if not knowledge:
        raise HTTPException(status_code=404, detail="Knowledge source not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(knowledge, field, value)
    knowledge.updated_by = current_user.id
    db.add(knowledge)
    db.commit()
    service = BotAIService(db)
    import asyncio
    asyncio.run(service.sync_knowledge_source(knowledge, current_user.id))
    db.refresh(knowledge)
    return knowledge


@router.get("/{bot_id}/conversations", response_model=list[BotConversationResponse])
def list_bot_conversations(
    bot_id: int,
    current_user: User = Depends(PermissionChecker("bot.view")),
    db: Session = Depends(get_db),
):
    """List conversations for a bot."""
    conversations = db.query(BotConversation).filter(
        BotConversation.bot_id == bot_id,
        BotConversation.is_deleted == False,
    ).order_by(BotConversation.created_at.desc()).all()

    items: list[BotConversationResponse] = []
    for conversation in conversations:
        item = BotConversationResponse.model_validate(conversation)
        item.message_count = db.query(BotMessage).filter(
            BotMessage.conversation_id == conversation.id,
            BotMessage.is_deleted == False,
        ).count()
        items.append(item)
    return items


@router.post("/{bot_id}/conversations", response_model=BotConversationResponse, status_code=status.HTTP_201_CREATED)
def create_bot_conversation(
    bot_id: int,
    payload: BotConversationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a bot conversation."""
    bot = db.query(AIBot).filter(AIBot.id == bot_id, AIBot.is_deleted == False).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    conversation = BotConversation(
        bot_id=bot_id,
        user_id=current_user.id,
        **payload.model_dump(),
        last_message_at=datetime.utcnow(),
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    response = BotConversationResponse.model_validate(conversation)
    response.message_count = 0
    return response


@router.get("/conversations/{conversation_id}/messages", response_model=list[BotMessageResponse])
def list_conversation_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List messages for a conversation."""
    conversation = db.query(BotConversation).filter(
        BotConversation.id == conversation_id,
        BotConversation.is_deleted == False,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return db.query(BotMessage).filter(
        BotMessage.conversation_id == conversation_id,
        BotMessage.is_deleted == False,
    ).order_by(BotMessage.created_at.asc()).all()


@router.post("/conversations/{conversation_id}/messages", response_model=BotChatResponse)
def send_conversation_message(
    conversation_id: int,
    payload: BotMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Store a chat message and generate an MVP assistant reply."""
    conversation = db.query(BotConversation).filter(
        BotConversation.id == conversation_id,
        BotConversation.is_deleted == False,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    bot = db.query(AIBot).filter(AIBot.id == conversation.bot_id, AIBot.is_deleted == False).first()
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")

    user_message = BotMessage(
        conversation_id=conversation_id,
        role="user",
        content=payload.content,
        detected_mood=payload.detected_mood,
        message_metadata=payload.message_metadata,
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(user_message)
    db.flush()

    service = BotAIService(db)
    import asyncio
    assistant_content, assistant_metadata = asyncio.run(
        service.generate_response(bot, conversation, payload.content, payload.detected_mood)
    )
    assistant_message = BotMessage(
        conversation_id=conversation_id,
        role="assistant",
        content=assistant_content,
        detected_mood=payload.detected_mood,
        message_metadata={
            "bot_slug": bot.slug,
            **assistant_metadata,
        },
        created_by=current_user.id,
        updated_by=current_user.id,
    )
    db.add(assistant_message)

    conversation.last_message_at = datetime.utcnow()
    conversation.mood = payload.detected_mood or conversation.mood
    conversation.updated_by = current_user.id
    db.add(conversation)
    db.commit()
    db.refresh(user_message)
    db.refresh(assistant_message)

    return BotChatResponse(
        user_message=BotMessageResponse.model_validate(user_message),
        assistant_message=BotMessageResponse.model_validate(assistant_message),
    )
