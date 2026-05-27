from tests.integration.helpers import get_auth_headers


def test_bot_module_crud_and_chat_flow(client, db, test_user):
    headers = get_auth_headers(
        client,
        db,
        test_user,
        [
            "bot.view",
            "bot.create",
            "bot.edit",
            "bot.delete",
        ],
    )

    create_response = client.post(
        "/api/v1/bots",
        headers=headers,
        json={
            "name": "Ananda Assistant",
            "slug": "ananda-assistant",
            "industry": "wellness",
            "description": "Calm wellness bot",
            "tone": "spiritual",
            "personality": "calm",
            "system_prompt": "You are a calm wellness assistant who guides users gently.",
            "welcome_message": "Welcome to your wellness companion.",
            "primary_color": "#0F766E",
            "enabled_plugins": ["booking", "email_automation"],
            "supported_languages": ["en", "ta"],
            "is_published": True,
        },
    )
    assert create_response.status_code == 201, create_response.text
    bot = create_response.json()
    bot_id = bot["id"]
    assert bot["slug"] == "ananda-assistant"
    assert bot["is_published"] is True

    list_response = client.get("/api/v1/bots", headers=headers)
    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] >= 1

    knowledge_response = client.post(
        f"/api/v1/bots/{bot_id}/knowledge",
        headers=headers,
        json={
            "source_type": "faq",
            "title": "Meditation FAQ",
            "raw_text": "Offer breathing exercises, beginner meditation guidance, and short stress relief routines.",
            "status": "ready",
        },
    )
    assert knowledge_response.status_code == 201, knowledge_response.text
    assert knowledge_response.json()["bot_id"] == bot_id
    assert knowledge_response.json()["status"] == "indexed"

    update_response = client.put(
        f"/api/v1/bots/{bot_id}",
        headers=headers,
        json={
            "tone": "professional",
            "personality": "expert",
            "industry": "wellbeing",
        },
    )
    assert update_response.status_code == 200, update_response.text
    updated = update_response.json()
    assert updated["tone"] == "professional"
    assert updated["industry"] == "wellbeing"

    conversation_response = client.post(
        f"/api/v1/bots/{bot_id}/conversations",
        headers=headers,
        json={
            "visitor_name": "Ruban",
            "channel": "web",
            "language": "en",
            "mood": "curious",
        },
    )
    assert conversation_response.status_code == 201, conversation_response.text
    conversation_id = conversation_response.json()["id"]

    chat_response = client.post(
        f"/api/v1/bots/conversations/{conversation_id}/messages",
        headers=headers,
        json={
            "content": "Suggest a meditation course for stress relief",
            "detected_mood": "stress",
        },
    )
    assert chat_response.status_code == 200, chat_response.text
    payload = chat_response.json()
    assert payload["user_message"]["role"] == "user"
    assert payload["assistant_message"]["role"] == "assistant"
    assert "knowledge" in payload["assistant_message"]["content"].lower()
    assert payload["assistant_message"]["message_metadata"]["retrieved_chunks"]

    analytics_response = client.get("/api/v1/bots/analytics/summary", headers=headers)
    assert analytics_response.status_code == 200, analytics_response.text
    assert analytics_response.json()["total_bots"] >= 1

    delete_response = client.delete(f"/api/v1/bots/{bot_id}", headers=headers)
    assert delete_response.status_code == 200, delete_response.text


def test_bot_create_generates_default_prompt_when_missing(client, db, test_user):
    headers = get_auth_headers(
        client,
        db,
        test_user,
        [
            "bot.view",
            "bot.create",
        ],
    )

    response = client.post(
        "/api/v1/bots",
        headers=headers,
        json={
            "name": "FlowBot",
            "slug": "flowbot",
            "industry": "finance",
            "tone": "professional",
            "personality": "expert",
            "enabled_plugins": ["booking"],
            "supported_languages": ["en"],
            "is_published": False,
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["system_prompt"]
    assert "FlowBot" in payload["system_prompt"]


def test_public_published_bot_chat_flow(client, db, test_user):
    headers = get_auth_headers(
        client,
        db,
        test_user,
        [
            "bot.view",
            "bot.create",
            "bot.edit",
        ],
    )

    create_response = client.post(
        "/api/v1/bots",
        headers=headers,
        json={
            "name": "Ayatiworks",
            "slug": "ayatiworks-bot",
            "industry": "digital marketing",
            "tone": "friendly",
            "personality": "helpful",
            "system_prompt": "You are a helpful digital marketing assistant for Ayatiworks.",
            "welcome_message": "Welcome to Ayatiworks bot.",
            "is_published": True,
        },
    )
    assert create_response.status_code == 201, create_response.text
    bot_id = create_response.json()["id"]

    knowledge_response = client.post(
        f"/api/v1/bots/{bot_id}/knowledge",
        headers=headers,
        json={
            "source_type": "faq",
            "title": "Marketing Services",
            "raw_text": "Ayatiworks offers SEO, Meta Ads management, lead generation, and campaign optimization.",
            "status": "ready",
        },
    )
    assert knowledge_response.status_code == 201, knowledge_response.text

    public_bot_response = client.get("/api/v1/public/bots/ayatiworks-bot")
    assert public_bot_response.status_code == 200, public_bot_response.text
    assert public_bot_response.json()["slug"] == "ayatiworks-bot"

    public_conversation_response = client.post(
        "/api/v1/public/bots/ayatiworks-bot/conversations",
        json={"visitor_name": "Guest", "language": "en"},
    )
    assert public_conversation_response.status_code == 201, public_conversation_response.text
    conversation_id = public_conversation_response.json()["id"]

    public_message_response = client.post(
        f"/api/v1/public/bots/ayatiworks-bot/conversations/{conversation_id}/messages",
        json={"content": "What services do you offer?"},
    )
    assert public_message_response.status_code == 200, public_message_response.text
    payload = public_message_response.json()
    assert payload["assistant_message"]["role"] == "assistant"
    assert payload["assistant_message"]["message_metadata"]["public"] is True


def test_website_knowledge_source_is_fetched_and_indexed(client, db, test_user, monkeypatch):
    async def fake_fetch(self, url):
        assert url in {"https://www.ayatiworks.com", "www.ayatiworks.com"}
        return (
            "Ayatiworks Digital Marketing",
            "Ayatiworks is a digital marketing agency offering SEO, Meta Ads, web design, "
            "lead generation, and conversion-focused campaign strategy.",
        )

    monkeypatch.setattr(
        "app.services.bot_ai_service.BotAIService._fetch_website_content",
        fake_fetch,
    )

    headers = get_auth_headers(
        client,
        db,
        test_user,
        [
            "bot.view",
            "bot.create",
            "bot.edit",
        ],
    )

    create_response = client.post(
        "/api/v1/bots",
        headers=headers,
        json={
            "name": "Ayatiworks",
            "slug": "ayatiworks-site-bot",
            "industry": "digital marketing",
            "tone": "friendly",
            "personality": "helpful",
            "system_prompt": "You are a helpful digital marketing assistant for Ayatiworks.",
            "is_published": True,
        },
    )
    assert create_response.status_code == 201, create_response.text
    bot_id = create_response.json()["id"]

    knowledge_response = client.post(
        f"/api/v1/bots/{bot_id}/knowledge",
        headers=headers,
        json={
            "source_type": "website",
            "title": "Ayatiworks Website",
            "website_url": "https://www.ayatiworks.com",
            "status": "ready",
        },
    )
    assert knowledge_response.status_code == 201, knowledge_response.text
    knowledge = knowledge_response.json()
    assert knowledge["status"] == "indexed"
    assert knowledge["raw_text"]
    assert knowledge["metadata_json"]["source_url"] == "https://www.ayatiworks.com"

    public_conversation_response = client.post(
        "/api/v1/public/bots/ayatiworks-site-bot/conversations",
        json={"visitor_name": "Guest", "language": "en"},
    )
    assert public_conversation_response.status_code == 201, public_conversation_response.text
    conversation_id = public_conversation_response.json()["id"]

    public_message_response = client.post(
        f"/api/v1/public/bots/ayatiworks-site-bot/conversations/{conversation_id}/messages",
        json={"content": "What does Ayatiworks do?"},
    )
    assert public_message_response.status_code == 200, public_message_response.text
    payload = public_message_response.json()
    assert payload["assistant_message"]["message_metadata"]["retrieved_chunks"]
