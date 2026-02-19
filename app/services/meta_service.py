"""
Meta Graph API Service.

Implements the real Meta Platforms Graph API flow:
  Step A: Exchange short-lived token → long-lived token
  Step B: Fetch campaigns from Ad Account
  Step C: Fetch ads under each campaign
  Step D: Get lead form IDs from ads
  Step E: Fetch leads from each lead form
"""

import logging
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v19.0"


class MetaGraphService:
    """Service to interact with the Meta Graph API."""

    def __init__(self, access_token: str, ad_account_id: str,
                 app_id: str | None = None, app_secret: str | None = None):
        self.access_token = access_token
        self.ad_account_id = ad_account_id.lstrip("act_")  # normalize
        self.app_id = app_id
        self.app_secret = app_secret
        self.client = httpx.Client(timeout=30.0)

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ------------------------------------------------------------------
    # Step A: Exchange short-lived → long-lived token
    # ------------------------------------------------------------------
    def exchange_token(self, short_lived_token: str) -> dict:
        """
        Exchange a short-lived token for a long-lived token.
        Requires app_id and app_secret.

        Returns: {"access_token": "...", "token_type": "bearer", "expires_in": 5183944}
        """
        if not self.app_id or not self.app_secret:
            raise ValueError("app_id and app_secret are required for token exchange")

        url = f"{GRAPH_API_BASE}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": short_lived_token,
        }
        resp = self.client.get(url, params=params)
        data = resp.json()

        if "error" in data:
            error_msg = data["error"].get("message", "Unknown Meta API error")
            logger.error(f"Token exchange failed: {error_msg}")
            raise Exception(f"Meta API: {error_msg}")

        logger.info("Token exchange successful")
        return data

    # ------------------------------------------------------------------
    # Step B: Fetch campaigns from Ad Account
    # ------------------------------------------------------------------
    def fetch_campaigns(self) -> list[dict]:
        """
        GET /act_{AD_ACCOUNT_ID}/campaigns
        Returns list of campaign dicts with id, name, status, objective, etc.
        """
        url = f"{GRAPH_API_BASE}/act_{self.ad_account_id}/campaigns"
        params = {
            "fields": "id,name,status,objective,daily_budget,lifetime_budget,start_time,stop_time,created_time",
            "access_token": self.access_token,
            "limit": 100,
        }

        all_campaigns = []
        while url:
            resp = self.client.get(url, params=params)
            data = resp.json()

            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                logger.error(f"Fetch campaigns failed: {error_msg}")
                raise Exception(f"Meta API: {error_msg}")

            all_campaigns.extend(data.get("data", []))

            # Pagination
            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}  # next URL has params built in

        logger.info(f"Fetched {len(all_campaigns)} campaigns")
        return all_campaigns

    # ------------------------------------------------------------------
    # Step C: Fetch ads under a campaign
    # ------------------------------------------------------------------
    def fetch_ads(self, campaign_id: str) -> list[dict]:
        """
        GET /{CAMPAIGN_ID}/ads
        Returns list of ad dicts.
        """
        url = f"{GRAPH_API_BASE}/{campaign_id}/ads"
        params = {
            "fields": "id,name,status",
            "access_token": self.access_token,
            "limit": 100,
        }

        all_ads = []
        while url:
            resp = self.client.get(url, params=params)
            data = resp.json()

            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                logger.warning(f"Fetch ads for campaign {campaign_id}: {error_msg}")
                break

            all_ads.extend(data.get("data", []))
            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}

        return all_ads

    # ------------------------------------------------------------------
    # Step D: Get lead form ID from an ad
    # ------------------------------------------------------------------
    def fetch_lead_forms(self, ad_id: str) -> list[dict]:
        """
        GET /{AD_ID}?fields=leadgen_forms
        Returns list of lead form dicts (id, name).
        """
        url = f"{GRAPH_API_BASE}/{ad_id}"
        params = {
            "fields": "leadgen_forms{id,name,status}",
            "access_token": self.access_token,
        }

        resp = self.client.get(url, params=params)
        data = resp.json()

        if "error" in data:
            error_msg = data["error"].get("message", "Unknown error")
            logger.warning(f"Fetch lead forms for ad {ad_id}: {error_msg}")
            return []

        forms_data = data.get("leadgen_forms", {}).get("data", [])
        return forms_data

    # ------------------------------------------------------------------
    # Step E: Fetch leads from a lead form
    # ------------------------------------------------------------------
    def fetch_leads(self, form_id: str) -> list[dict]:
        """
        GET /{FORM_ID}/leads
        Returns list of lead dicts with field_data.
        """
        url = f"{GRAPH_API_BASE}/{form_id}/leads"
        params = {
            "access_token": self.access_token,
            "limit": 100,
        }

        all_leads = []
        while url:
            resp = self.client.get(url, params=params)
            data = resp.json()

            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                logger.warning(f"Fetch leads for form {form_id}: {error_msg}")
                break

            all_leads.extend(data.get("data", []))
            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}

        return all_leads

    # ------------------------------------------------------------------
    # Full Sync: Orchestrate all steps
    # ------------------------------------------------------------------
    def full_sync(self, db, client_id: int) -> dict:
        """
        Perform a full sync: Campaigns → Ads → Forms → Leads.
        Stores everything in the database.

        Returns summary dict: {campaigns_synced, leads_synced}
        """
        from app.models.meta import MetaCampaign, MetaLead

        stats = {"campaigns_synced": 0, "leads_synced": 0, "errors": []}

        # ----- STEP B: Campaigns -----
        try:
            campaigns_data = self.fetch_campaigns()
        except Exception as e:
            stats["errors"].append(f"Campaign fetch: {str(e)}")
            return stats

        campaign_map = {}  # meta_campaign_id → db MetaCampaign object

        for c in campaigns_data:
            meta_id = c["id"]

            # Upsert campaign
            db_camp = db.query(MetaCampaign).filter(
                MetaCampaign.client_id == client_id,
                MetaCampaign.campaign_id == meta_id,
            ).first()

            # Parse budget (Meta returns in cents)
            daily_budget = None
            if c.get("daily_budget"):
                try:
                    daily_budget = float(c["daily_budget"]) / 100
                except (ValueError, TypeError):
                    pass

            lifetime_budget = None
            if c.get("lifetime_budget"):
                try:
                    lifetime_budget = float(c["lifetime_budget"]) / 100
                except (ValueError, TypeError):
                    pass

            start_time = _parse_meta_datetime(c.get("start_time"))
            stop_time = _parse_meta_datetime(c.get("stop_time"))

            if db_camp:
                db_camp.name = c.get("name", db_camp.name)
                db_camp.status = c.get("status", db_camp.status)
                db_camp.objective = c.get("objective")
                db_camp.daily_budget = daily_budget
                db_camp.lifetime_budget = lifetime_budget
                db_camp.start_time = start_time
                db_camp.stop_time = stop_time
            else:
                db_camp = MetaCampaign(
                    client_id=client_id,
                    campaign_id=meta_id,
                    name=c.get("name", "Unnamed"),
                    status=c.get("status"),
                    objective=c.get("objective"),
                    daily_budget=daily_budget,
                    lifetime_budget=lifetime_budget,
                    start_time=start_time,
                    stop_time=stop_time,
                )
                db.add(db_camp)

            db.flush()
            campaign_map[meta_id] = db_camp
            stats["campaigns_synced"] += 1

        # ----- STEP C → D → E: Ads → Forms → Leads per campaign -----
        for meta_camp_id, db_camp in campaign_map.items():
            try:
                ads = self.fetch_ads(meta_camp_id)
            except Exception as e:
                stats["errors"].append(f"Ads for {meta_camp_id}: {str(e)}")
                continue

            for ad in ads:
                ad_id = ad["id"]

                # Step D: Get lead forms from ad
                try:
                    forms = self.fetch_lead_forms(ad_id)
                except Exception as e:
                    stats["errors"].append(f"Forms for ad {ad_id}: {str(e)}")
                    continue

                for form in forms:
                    form_id = form["id"]

                    # Step E: Get leads from form
                    try:
                        leads = self.fetch_leads(form_id)
                    except Exception as e:
                        stats["errors"].append(f"Leads for form {form_id}: {str(e)}")
                        continue

                    for lead in leads:
                        lead_meta_id = lead.get("id")
                        if not lead_meta_id:
                            continue

                        # Check duplicate
                        existing = db.query(MetaLead).filter(
                            MetaLead.lead_id == lead_meta_id
                        ).first()
                        if existing:
                            continue

                        # Parse field_data
                        field_data = lead.get("field_data", [])
                        parsed = _parse_lead_fields(field_data)

                        created_time = _parse_meta_datetime(lead.get("created_time"))

                        new_lead = MetaLead(
                            client_id=client_id,
                            campaign_id=db_camp.id,
                            lead_id=lead_meta_id,
                            form_id=form_id,
                            created_time=created_time,
                            full_name=parsed.get("full_name"),
                            email=parsed.get("email"),
                            phone_number=parsed.get("phone_number"),
                            status="new",
                            raw_data=lead,  # Store full Meta response
                        )
                        db.add(new_lead)
                        stats["leads_synced"] += 1

        db.commit()
        logger.info(f"Sync complete: {stats['campaigns_synced']} campaigns, {stats['leads_synced']} leads")
        return stats


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_meta_datetime(value: str | None) -> datetime | None:
    """Parse ISO datetime from Meta API (e.g. '2025-10-01T10:00:00+0000')."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("+0000", "+00:00"))
    except (ValueError, TypeError):
        return None


def _parse_lead_fields(field_data: list[dict]) -> dict[str, str]:
    """
    Parse Meta lead field_data array into a flat dict.
    Example field_data:
        [{"name": "full_name", "values": ["Ravi Kumar"]},
         {"name": "phone_number", "values": ["9876543210"]}]
    """
    result = {}
    for field in field_data:
        name = field.get("name", "").lower()
        values = field.get("values", [])
        value = values[0] if values else None

        if name in ("full_name", "name"):
            result["full_name"] = value
        elif name in ("email", "email_address"):
            result["email"] = value
        elif name in ("phone_number", "phone", "mobile"):
            result["phone_number"] = value
        else:
            # Store any extra fields
            result[name] = value

    return result
