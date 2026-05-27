"""
Bot AI service with lightweight RAG and optional OpenAI integration.
"""

from __future__ import annotations

import hashlib
import html
import math
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.models.ai_bot import AIBot, BotConversation, BotKnowledgeChunk, BotKnowledgeSource, BotMessage


class _WebsiteTextExtractor(HTMLParser):
    """Extract readable text from simple HTML pages."""

    def __init__(self) -> None:
        super().__init__()
        self._skip_depth = 0
        self._in_title = False
        self._title_parts: list[str] = []
        self._text_parts: list[str] = []
        self._links: list[str] = []

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        normalized = re.sub(r"\s+", " ", data or "").strip()
        if not normalized:
            return
        if self._in_title:
            self._title_parts.append(normalized)
        else:
            self._text_parts.append(normalized)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag == "a":
            href = dict(attrs).get("href")
            if href:
                self._links.append(href)

    @property
    def title(self) -> str:
        return " ".join(self._title_parts).strip()

    @property
    def text(self) -> str:
        return "\n".join(self._text_parts).strip()

    @property
    def links(self) -> list[str]:
        return self._links


class BotAIService:
    """Encapsulates retrieval and response generation for bots."""

    def __init__(self, db: Session):
        self.db = db
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL.rstrip("/")

    def has_openai(self) -> bool:
        return bool(self.api_key)

    def _source_text(self, source: BotKnowledgeSource) -> str:
        text_parts = []
        metadata = source.metadata_json or {}
        extracted_title = metadata.get("extracted_title")
        extracted_text = metadata.get("extracted_text")
        website_url = source.website_url or metadata.get("source_url")

        if extracted_title:
            text_parts.append(extracted_title)
        elif source.title:
            text_parts.append(source.title)
        if extracted_text:
            text_parts.append(extracted_text)
        elif source.raw_text:
            text_parts.append(source.raw_text)
        if website_url:
            text_parts.append(f"Website source: {website_url}")
        return "\n\n".join(part.strip() for part in text_parts if part and part.strip())

    def _normalize_website_url(self, url: str) -> str:
        normalized = (url or "").strip()
        if not normalized:
            return ""
        if not normalized.startswith(("http://", "https://")):
            normalized = f"https://{normalized}"
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return ""
        return normalized

    def _is_same_site_url(self, candidate: str, base_host: str) -> bool:
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return False
        host = parsed.netloc.lower()
        base_host = base_host.lower()
        return host == base_host or host == f"www.{base_host}" or base_host == f"www.{host}"

    def _filter_crawl_links(self, base_url: str, links: list[str]) -> list[str]:
        parsed_base = urlparse(base_url)
        base_host = parsed_base.netloc
        selected: list[str] = []
        seen: set[str] = set()
        excluded_prefixes = ("mailto:", "tel:", "javascript:", "#")
        excluded_extensions = (
            ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".pdf",
            ".zip", ".mp4", ".mp3", ".avi", ".mov", ".doc", ".docx",
            ".xls", ".xlsx", ".ppt", ".pptx",
        )

        for raw_link in links:
            if not raw_link or raw_link.startswith(excluded_prefixes):
                continue
            candidate = self._normalize_website_url(urljoin(base_url, raw_link))
            if not candidate:
                continue
            if not self._is_same_site_url(candidate, base_host):
                continue
            if urlparse(candidate).path.lower().endswith(excluded_extensions):
                continue
            normalized = candidate.rstrip("/")
            if normalized in seen:
                continue
            seen.add(normalized)
            selected.append(candidate)
            if len(selected) >= max(settings.BOT_WEBSITE_MAX_PAGES - 1, 0):
                break

        return selected

    async def _fetch_single_page(
        self,
        client: httpx.AsyncClient,
        url: str,
    ) -> tuple[str, str, list[str]]:
        response = await client.get(
            url,
            headers={
                "User-Agent": "AyatiworksBotIndexer/1.0 (+https://www.ayatiworks.com)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "").lower()
        if "html" not in content_type:
            return "", "", []

        parser = _WebsiteTextExtractor()
        parser.feed(response.text)
        title = html.unescape(parser.title).strip()
        text = html.unescape(parser.text).strip()
        return title, text, parser.links

    async def _fetch_website_content(self, url: str) -> tuple[str, str]:
        normalized_url = self._normalize_website_url(url)
        if not normalized_url:
            return "", ""

        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            main_title, main_text, main_links = await self._fetch_single_page(client, normalized_url)
            aggregated_sections: list[str] = []
            total_chars = 0

            def append_section(page_url: str, page_title: str, page_text: str) -> None:
                nonlocal total_chars
                if not page_text:
                    return
                section = f"{page_title or page_url}\n{page_text}".strip()
                remaining = settings.BOT_WEBSITE_MAX_CHARACTERS - total_chars
                if remaining <= 0:
                    return
                if len(section) > remaining:
                    section = section[:remaining].rstrip()
                if section:
                    aggregated_sections.append(section)
                    total_chars += len(section)

            append_section(normalized_url, main_title or "Home", main_text)

            crawl_links = self._filter_crawl_links(normalized_url, main_links)
            for link in crawl_links:
                if total_chars >= settings.BOT_WEBSITE_MAX_CHARACTERS:
                    break
                try:
                    page_title, page_text, _ = await self._fetch_single_page(client, link)
                except Exception:
                    continue
                append_section(link, page_title or link, page_text)

            return main_title, "\n\n".join(aggregated_sections).strip()

    def _chunk_text(self, text: str) -> list[str]:
        normalized = re.sub(r"\s+", " ", text or "").strip()
        if not normalized:
            return []

        size = settings.BOT_RAG_CHUNK_SIZE
        overlap = settings.BOT_RAG_CHUNK_OVERLAP
        chunks: list[str] = []
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + size)
            chunks.append(normalized[start:end].strip())
            if end >= len(normalized):
                break
            start = max(end - overlap, start + 1)
        return [chunk for chunk in chunks if chunk]

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _tokenize(self, text: str) -> set[str]:
        return {token for token in re.findall(r"[a-z0-9]+", (text or "").lower()) if len(token) > 1}

    def _keyword_score(self, query: str, text: str) -> float:
        query_tokens = self._tokenize(query)
        text_tokens = self._tokenize(text)
        if not query_tokens or not text_tokens:
            return 0.0
        overlap = len(query_tokens & text_tokens)
        return overlap / max(len(query_tokens), 1)

    def _cosine_similarity(self, vector_a: list[float], vector_b: list[float]) -> float:
        if not vector_a or not vector_b or len(vector_a) != len(vector_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vector_a, vector_b))
        mag_a = math.sqrt(sum(a * a for a in vector_a))
        mag_b = math.sqrt(sum(b * b for b in vector_b))
        if not mag_a or not mag_b:
            return 0.0
        return dot / (mag_a * mag_b)

    async def _post_openai(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def embed_texts(self, texts: list[str]) -> list[list[float] | None]:
        if not texts:
            return []
        if not self.has_openai():
            return [None for _ in texts]

        try:
            payload = {
                "model": settings.OPENAI_EMBEDDING_MODEL,
                "input": texts,
            }
            data = await self._post_openai("/embeddings", payload)
            return [item.get("embedding") for item in data.get("data", [])]
        except Exception:
            return [None for _ in texts]

    async def sync_knowledge_source(self, source: BotKnowledgeSource, actor_id: int | None = None) -> int:
        metadata = dict(source.metadata_json or {})
        if source.website_url:
            metadata["source_url"] = self._normalize_website_url(source.website_url) or source.website_url
            try:
                fetched_title, fetched_text = await self._fetch_website_content(source.website_url)
                if fetched_title:
                    metadata["extracted_title"] = fetched_title
                    if not source.title or source.title == source.website_url:
                        source.title = fetched_title[:255]
                if fetched_text:
                    metadata["extracted_text"] = fetched_text
                    metadata["extracted_characters"] = len(fetched_text)
                    source.raw_text = fetched_text
                    source.status = "ready"
                elif not source.raw_text:
                    source.status = "empty"
            except Exception as exc:
                metadata["fetch_error"] = str(exc)
                if not source.raw_text:
                    source.status = "fetch_failed"

        source.metadata_json = metadata or None
        text = self._source_text(source)
        chunks = self._chunk_text(text)

        self.db.query(BotKnowledgeChunk).filter(
            BotKnowledgeChunk.source_id == source.id
        ).delete()
        self.db.flush()

        embeddings = await self.embed_texts(chunks)
        created = 0
        for index, chunk in enumerate(chunks):
            embedding = embeddings[index] if index < len(embeddings) else None
            record = BotKnowledgeChunk(
                bot_id=source.bot_id,
                source_id=source.id,
                chunk_index=index,
                content=chunk,
                embedding_json=embedding,
                content_hash=self._hash_text(chunk),
                created_by=actor_id,
                updated_by=actor_id,
            )
            self.db.add(record)
            created += 1

        if created:
            source.status = "indexed"
        elif source.status not in {"fetch_failed", "empty"}:
            source.status = "empty"
        source.embedding_provider = "openai" if self.has_openai() else "local"
        source.embedding_reference = settings.OPENAI_EMBEDDING_MODEL if self.has_openai() else "keyword"
        source.updated_by = actor_id
        self.db.add(source)
        self.db.commit()
        return created

    async def retrieve_context(self, bot_id: int, query: str) -> list[BotKnowledgeChunk]:
        chunks = self.db.query(BotKnowledgeChunk).filter(
            BotKnowledgeChunk.bot_id == bot_id,
            BotKnowledgeChunk.is_deleted == False,
        ).all()
        if not chunks:
            return []

        query_embedding = None
        if self.has_openai():
            query_embeddings = await self.embed_texts([query])
            if query_embeddings:
                query_embedding = query_embeddings[0]

        ranked: list[tuple[float, BotKnowledgeChunk]] = []
        for chunk in chunks:
            score = self._keyword_score(query, chunk.content)
            if query_embedding and chunk.embedding_json:
                score = max(score, self._cosine_similarity(query_embedding, chunk.embedding_json))
            if score > 0:
                ranked.append((score, chunk))

        ranked.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in ranked[:settings.BOT_RAG_TOP_K]]

    def _history_messages(self, conversation_id: int) -> list[BotMessage]:
        return self.db.query(BotMessage).filter(
            BotMessage.conversation_id == conversation_id,
            BotMessage.is_deleted == False,
        ).order_by(BotMessage.created_at.desc()).limit(6).all()[::-1]

    def _fallback_response(
        self,
        bot: AIBot,
        user_message: str,
        mood: str | None,
        retrieved_chunks: list[BotKnowledgeChunk],
    ) -> str:
        tone = (bot.tone or "friendly").lower()
        intro = {
            "spiritual": "Let's approach this calmly and clearly.",
            "professional": "Here is a structured answer based on the bot knowledge base.",
            "expert": "Based on the indexed knowledge available,",
        }.get(tone, "Here is a helpful response based on the indexed bot knowledge.")
        context_text = "\n".join(f"- {chunk.content[:220]}" for chunk in retrieved_chunks[:3])
        mood_text = f" User mood detected: {mood}." if mood else ""
        if context_text:
            return f"{intro}{mood_text}\n\nRelevant knowledge:\n{context_text}\n\nUser asked: {user_message}"
        return f"{intro}{mood_text}\n\nI could not find matching indexed knowledge yet, so please add or refine the bot knowledge base."

    async def generate_response(
        self,
        bot: AIBot,
        conversation: BotConversation,
        user_message: str,
        detected_mood: str | None = None,
    ) -> tuple[str, dict[str, Any]]:
        retrieved_chunks = await self.retrieve_context(bot.id, user_message)
        history = self._history_messages(conversation.id)
        context_text = "\n\n".join(chunk.content for chunk in retrieved_chunks)

        if not self.has_openai():
            return self._fallback_response(bot, user_message, detected_mood, retrieved_chunks), {
                "source": "fallback-rag",
                "retrieved_chunks": [chunk.id for chunk in retrieved_chunks],
            }

        history_lines = "\n".join(f"{msg.role}: {msg.content}" for msg in history[-6:])
        prompt = (
            f"{bot.system_prompt}\n\n"
            f"Bot tone: {bot.tone}\n"
            f"Bot personality: {bot.personality}\n"
            f"Detected mood: {detected_mood or 'unknown'}\n\n"
            f"Retrieved knowledge:\n{context_text or 'No indexed knowledge retrieved.'}\n\n"
            f"Recent conversation:\n{history_lines or 'No previous messages.'}\n\n"
            f"Answer the latest user message accurately and stay within the retrieved knowledge when possible."
        )

        try:
            payload = {
                "model": settings.OPENAI_RESPONSE_MODEL,
                "instructions": prompt,
                "input": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": user_message,
                            }
                        ],
                    }
                ],
            }
            data = await self._post_openai("/responses", payload)
            response_text = data.get("output_text")
            if not response_text:
                for item in data.get("output", []):
                    if item.get("type") == "message":
                        for content in item.get("content", []):
                            if content.get("type") == "output_text" and content.get("text"):
                                response_text = content["text"]
                                break
                    if response_text:
                        break

            if response_text:
                return response_text, {
                    "source": "openai-rag",
                    "model": settings.OPENAI_RESPONSE_MODEL,
                    "retrieved_chunks": [chunk.id for chunk in retrieved_chunks],
                }
        except Exception:
            pass

        return self._fallback_response(bot, user_message, detected_mood, retrieved_chunks), {
            "source": "fallback-rag",
            "retrieved_chunks": [chunk.id for chunk in retrieved_chunks],
        }
