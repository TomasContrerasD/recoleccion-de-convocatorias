import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote, urlsplit

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parent
ENV_FILE = BACKEND_DIR / ".env"


class ConfigurationError(ValueError):
    """A setting is missing or invalid; messages must never include secret values."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = field(default="", repr=False)
    openai_model: str = "gpt-6-luna"
    sheets_id: str = field(default="", repr=False)
    sheets_tab_name: str = "Convocatorias"
    google_application_credentials: Path = field(
        default=BACKEND_DIR / "credentials.json", repr=False,
    )
    google_credentials_json: str = field(default="", repr=False)
    gmail_user: str = field(default="", repr=False)
    gmail_app_password: str = field(default="", repr=False)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    notify_email: str = field(default="", repr=False)
    enable_automation: bool = False
    scheduler_secret: str = field(default="", repr=False)
    beo_email: str = field(default="", repr=False)
    beo_password: str = field(default="", repr=False)
    portal_url: str = "http://localhost:3000"
    cors_origins: tuple[str, ...] = (
        "http://localhost:3000", "http://127.0.0.1:3000",
    )

    @property
    def sheets_url(self) -> str:
        """Use the configured destination in emails rather than a second sheet ID."""
        if not self.sheets_id:
            return ""
        return f"https://docs.google.com/spreadsheets/d/{quote(self.sheets_id, safe='')}/edit#gid=0"

    def require_openai_key(self) -> str:
        if not self.openai_api_key:
            raise ConfigurationError("Configura OPENAI_API_KEY en backend/.env.")
        return self.openai_api_key


def _http_url(value: str, setting: str, *, origin: bool = False) -> str:
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme in {"http", "https"}
            and parsed.hostname
            and not parsed.username
            and not parsed.password
        )
        if origin:
            valid = valid and parsed.path in {"", "/"} and not parsed.query and not parsed.fragment
        # Accessing the port also validates malformed or out-of-range port numbers.
        parsed.port
    except ValueError:
        valid = False
    if not valid:
        raise ConfigurationError(f"{setting} debe contener una URL HTTP o HTTPS valida.")
    return value.rstrip("/")


def get_settings() -> Settings:
    """Read a settings snapshot without exposing values or mutating os.environ.

    Restart the server after changing settings: CORS and cached AI clients are
    initialized once, while individual operations read their current settings.
    """
    values = {**dotenv_values(ENV_FILE, encoding="utf-8-sig"), **os.environ}

    def read(name: str, default: str = "", *, strip: bool = True) -> str:
        value = values.get(name)
        if value is None:
            return default
        return str(value).strip() if strip else str(value)

    try:
        smtp_port = int(read("SMTP_PORT", "465"))
    except ValueError:
        raise ConfigurationError("SMTP_PORT debe ser un numero entre 1 y 65535.") from None
    if not 1 <= smtp_port <= 65535:
        raise ConfigurationError("SMTP_PORT debe ser un numero entre 1 y 65535.")

    credentials_path = Path(read("GOOGLE_APPLICATION_CREDENTIALS") or "credentials.json").expanduser()
    if not credentials_path.is_absolute():
        credentials_path = BACKEND_DIR / credentials_path

    origins = read("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
    cors_origins = tuple(dict.fromkeys(
        _http_url(value.strip(), "CORS_ORIGINS", origin=True)
        for value in origins.split(",") if value.strip()
    ))
    portal_url = read("PORTAL_URL", "http://localhost:3000")
    if portal_url:
        portal_url = _http_url(portal_url, "PORTAL_URL")

    automation_value = read("ENABLE_AUTOMATION", "false").lower() or "false"
    if automation_value not in {"true", "false"}:
        raise ConfigurationError("ENABLE_AUTOMATION debe ser true o false.")
    enable_automation = automation_value == "true"
    scheduler_secret = read("SCHEDULER_SECRET", strip=False)
    if enable_automation and not scheduler_secret.strip():
        raise ConfigurationError("Configura SCHEDULER_SECRET antes de activar ENABLE_AUTOMATION.")

    return Settings(
        openai_api_key=read("OPENAI_API_KEY"),
        openai_model=read("OPENAI_MODEL") or "gpt-6-luna",
        sheets_id=read("SHEETS_CONVOCATORIAS_ID"),
        sheets_tab_name=read("SHEETS_TAB_NAME") or "Convocatorias",
        google_application_credentials=credentials_path.resolve(),
        google_credentials_json=read("GOOGLE_CREDENTIALS_JSON"),
        gmail_user=read("GMAIL_USER"),
        gmail_app_password=read("GMAIL_APP_PASSWORD", strip=False),
        smtp_host=read("SMTP_HOST") or "smtp.gmail.com",
        smtp_port=smtp_port,
        notify_email=read("NOTIFY_EMAIL"),
        enable_automation=enable_automation,
        scheduler_secret=scheduler_secret,
        beo_email=read("BEO_EMAIL"),
        beo_password=read("BEO_PASSWORD", strip=False),
        portal_url=portal_url,
        cors_origins=cors_origins,
    )
