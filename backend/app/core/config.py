from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from connectors.rss.models import DEFAULT_USER_AGENT

# backend/app/core/config.py -> backend/ and the repository root above it.
BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
# Local runtime files (git-ignored): the SQLite database, logs, caches, backups.
DATA_DIR = BACKEND_DIR / ".data"

# Zero-setup local database, used only when DATABASE_URL is not set.
# PostgreSQL/PostGIS is the target database (see docker-compose.yml).
LOCAL_SQLITE_URL = f"sqlite:///{(DATA_DIR / 'rei.db').as_posix()}"


class Settings(BaseSettings):
    """API configuration, read from environment variables or the root .env file."""

    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = LOCAL_SQLITE_URL
    # Apply database migrations on startup. Turn off where migrations are run
    # as a separate deployment step.
    auto_migrate: bool = True
    # Comma-separated origins allowed to call the API from a browser.
    cors_origins: str = "http://localhost:3000"

    # Local reviewer authentication. The bootstrap account is created only if
    # both seed values are present, and an existing account is never reset.
    seed_admin_email: str | None = None
    seed_admin_password: str | None = None
    # The one read-only User account (decision 0032), created the same way: only
    # if both are set, once, and never reset. Its email must differ from the admin's.
    seed_user_email: str | None = None
    seed_user_password: str | None = None
    auth_cookie_name: str = "rei_session"
    auth_cookie_secure: bool = False
    auth_session_hours: int = 12

    # Poll active sources in the background, at each source's own frequency.
    ingestion_scheduler_enabled: bool = True
    ingestion_scheduler_tick_seconds: int = 60
    # How REI identifies itself to the sources it reads.
    http_user_agent: str = DEFAULT_USER_AGENT
    # Optional replacement for services/extraction/config/traffic_keywords.json.
    traffic_keywords_path: str | None = None
    # Serper.dev key for the Google News search source; the source stays
    # unconnected without it.
    serper_api_key: str | None = None
    # Google News RSS discovery feeds, one source per configured city. Off:
    # each feed says it is for personal, non-commercial use only. Switch on only
    # with written permission (docs/data-sources/google-news-rss.md).
    google_news_rss_enabled: bool = False
    # GDELT news searches, one per city with a place list (decision 0033). Off
    # by default: on 16 October 2026 its API refused most requests. Off, the
    # searches are listed but never run; true switches them on.
    gdelt_search_enabled: bool = False
    # Connected government feeds (including TfL, Toronto, NYC and France).
    # Run by hand by default; set true to poll all connected official feeds on
    # their source-specific schedules.
    official_feeds_scheduled: bool = False
    # Comma-separated official feeds to poll on their schedules while
    # OFFICIAL_FEEDS_SCHEDULED is off, e.g. "tfl-road-disruptions,
    # toronto-road-restrictions". Names that are not official feeds are ignored.
    official_feeds_scheduled_sources: str = ""
    # Records one run of an official feed may keep at most (in effect now or
    # upcoming, most recent first); 0 keeps every record. 30 during the first
    # four-city test (6 October 2026); since 21 October 2026 every record is
    # kept by default, as every other official feed already did.
    official_feed_max_records: int = 0
    # Optional TfL app key: raises TfL's limit from 50 to 500 requests a minute.
    tfl_app_key: str | None = None
    # After each ingestion run, compare the new events with the city's open
    # events: merge clear duplicates, record possible matches for review.
    event_matching_after_ingestion: bool = True
    # Storage: days the full text of an article that is not a road event is
    # kept; afterwards a small stub remains so it is not stored again
    # (app/services/retention_service.py). 0 keeps the text for ever.
    unrelated_article_text_days: int = 14
    # The PostGIS database holding the OSM road network for GIS resolution
    # (postgresql+psycopg://…/rei_gis). Without it, GIS resolution is unavailable;
    # everything else works as before.
    gis_database_url: str | None = None

    # --- AI reading of articles (app/services/ai_reading_service.py) -------------
    # OpenRouter key. Without it (or without AI_MODEL) no article is sent to a model.
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # The OpenRouter model id, e.g. google/gemma-4-26b-a4b-it:free. Required.
    ai_model: str | None = None
    # Comma-separated models OpenRouter tries in turn when the first is busy.
    ai_fallback_models: str = ""
    # Ask the model to reason before it answers (slower, usually more careful).
    ai_reasoning: bool = True
    # Switch the background reading off while keeping the key configured.
    ai_reading_enabled: bool = True
    # Requests this API sends to OpenRouter per day (UTC). A free key allows 50;
    # the rest is left for trying things by hand.
    ai_daily_request_limit: int = 40
    # Only articles stored within this many days are read automatically
    # (backend/cli/ai_read.py --days reads older ones).
    ai_lookback_days: int = 2
    # How often the background reader looks for unread articles, in seconds.
    ai_tick_seconds: int = 300
    # Sources whose articles are never sent to a model (their terms forbid it).
    # Articles on a restricted publisher's site (connectors/restricted.py) are
    # never sent either, whichever source stored them.
    ai_excluded_sources: str = "siasat,siasat-mumbai"
    # Optional replacement for services/ai_reading/config/ai_reading.json.
    ai_reading_config_path: str | None = None

    # --- Placing events (services/geo_resolution/placement.py) ---------------------
    # Ask Google Maps (through Serper.dev, SERPER_API_KEY) for names the
    # OpenStreetMap place list cannot place. Off, or without the key: OSM only.
    place_lookup_google: bool = True
    # Serper credits a day for place lookups (a /places query costs 1, a /maps 3);
    # 0 sets no daily limit (since 21 October 2026; 60 before). Every answer is
    # cached, so a name is never asked twice.
    place_lookup_daily_credits: int = 0
    place_lookup_cache_path: str = str(DATA_DIR / "google_places_cache.json")

    # --- Email, registration and reset links (decision 0045) ----------------------
    # Self-registration (decision 0046: off). Accounts are created by an
    # administrator in User management. True, with email configured and
    # ALLOWED_EMAIL_DOMAINS set, opens the Register form and its API again.
    registration_enabled: bool = False
    # The transactional email service: "resend" (resend.com, an HTTP API: Railway
    # may block outgoing SMTP). Empty, or any value incomplete below: no email is
    # ever sent, and registration and reset links are unavailable (the console
    # says so). Nothing pretends an email was sent.
    email_provider: str = ""
    # The sender, on a domain verified with the provider: "JSAN REI <rei@mail.example.com>".
    email_from: str | None = None
    # The provider's API key. Only in .env or Railway variables, never in code.
    email_api_key: str | None = None
    # The console's public address, for the links in emails: https://jsan-rei.up.railway.app
    app_base_url: str | None = None
    # Comma-separated company email domains that may register: "jsanconsulting.com".
    # Empty: registration is closed. Never guessed: set it explicitly.
    allowed_email_domains: str = ""
    # How long a link stays valid.
    email_verification_minutes: int = 24 * 60
    password_reset_minutes: int = 30

    @property
    def email_configured(self) -> bool:
        """Whether emails can be sent: a known provider with its key, a sender and the console's address."""
        return (
            self.email_provider.strip().lower() == "resend"
            and bool(self.email_api_key and self.email_from and self.app_base_url)
        )

    @property
    def allowed_email_domain_set(self) -> frozenset[str]:
        return frozenset(
            domain.strip().lower().lstrip("@") for domain in self.allowed_email_domains.split(",") if domain.strip()
        )

    @property
    def registration_open(self) -> bool:
        """Registration needs both: ownership is proved by an emailed link, and only company domains may register."""
        return self.registration_enabled and self.email_configured and bool(self.allowed_email_domain_set)

    @property
    def ai_configured(self) -> bool:
        return bool(self.openrouter_api_key and self.ai_model)

    @property
    def ai_fallback_model_list(self) -> list[str]:
        return [model.strip() for model in self.ai_fallback_models.split(",") if model.strip()]

    @property
    def ai_excluded_source_ids(self) -> set[str]:
        return {source.strip() for source in self.ai_excluded_sources.split(",") if source.strip()}

    @property
    def official_feeds_scheduled_source_ids(self) -> frozenset[str]:
        return frozenset(
            source.strip()
            for source in self.official_feeds_scheduled_sources.split(",")
            if source.strip()
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
