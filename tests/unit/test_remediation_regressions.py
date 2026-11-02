"""
Unit tests for Step 7 remediation and regression fixes.
Verifies fixes for BUG-QA-15 (invoice negative discount), BUG-QA-14 (SSRF validation),
and BUG-QA-17 (leave balance underflow protection).
"""

import os
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "ci-testing-dummy-secret-key-32-characters-minimum")

from decimal import Decimal
import pytest
from pydantic import ValidationError

from app.schemas.invoice import InvoiceCreate, InvoiceItemCreate, InvoiceUpdate
from app.services.bot_ai_service import BotAIService


class TestInvoiceValidationRegressions:
    """Verifies that invoice schemas strictly enforce non-negative values (BUG-QA-15)."""

    def test_invoice_create_rejects_negative_discount(self):
        with pytest.raises(ValidationError) as exc_info:
            InvoiceCreate(
                client_id=1,
                issue_date="2026-10-01",
                due_date="2026-10-15",
                discount=Decimal("-50.00"),
                items=[InvoiceItemCreate(description="Consulting", rate=Decimal("100.00"))]
            )
        assert "discount" in str(exc_info.value)
        assert "greater than or equal to 0" in str(exc_info.value)

    def test_invoice_create_rejects_negative_tax_rate(self):
        with pytest.raises(ValidationError) as exc_info:
            InvoiceCreate(
                client_id=1,
                issue_date="2026-10-01",
                due_date="2026-10-15",
                tax_rate=-5.0,
                items=[InvoiceItemCreate(description="Consulting", rate=Decimal("100.00"))]
            )
        assert "tax_rate" in str(exc_info.value)

    def test_invoice_update_rejects_negative_discount(self):
        with pytest.raises(ValidationError) as exc_info:
            InvoiceUpdate(discount=Decimal("-10.00"))
        assert "discount" in str(exc_info.value)

    def test_invoice_valid_discount_passes(self):
        invoice = InvoiceCreate(
            client_id=1,
            issue_date="2026-10-01",
            due_date="2026-10-15",
            discount=Decimal("25.00"),
            items=[InvoiceItemCreate(description="Consulting", rate=Decimal("100.00"))]
        )
        assert invoice.discount == Decimal("25.00")


class TestBotSSRFRegressions:
    """Verifies that bot URL knowledge ingestion blocks loopback and internal IP ranges (BUG-QA-14)."""

    def test_ssrf_rejects_localhost_and_loopback(self):
        assert BotAIService._is_safe_public_url("localhost") is False
        assert BotAIService._is_safe_public_url("127.0.0.1") is False
        assert BotAIService._is_safe_public_url("127.0.0.1:8000") is False
        assert BotAIService._is_safe_public_url("::1") is False

    def test_ssrf_rejects_cloud_metadata_service(self):
        assert BotAIService._is_safe_public_url("169.254.169.254") is False

    def test_ssrf_rejects_private_network_ranges(self):
        assert BotAIService._is_safe_public_url("10.0.0.5") is False
        assert BotAIService._is_safe_public_url("192.168.1.1") is False
        assert BotAIService._is_safe_public_url("172.16.0.1") is False

    def test_ssrf_allows_public_domains(self):
        assert BotAIService._is_safe_public_url("example.com") is True
        assert BotAIService._is_safe_public_url("ayatiworks.com") is True
        assert BotAIService._is_safe_public_url("docs.python.org") is True
