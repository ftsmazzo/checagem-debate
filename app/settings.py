import os


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return int(raw)


def _secret(name: str) -> str:
    raw = os.environ.get(name, "") or ""
    cleaned = raw.strip().strip('"').strip("'").replace("\r", "").replace("\n", "")
    if cleaned.lower().startswith("bearer "):
        cleaned = cleaned[7:].strip()
    return cleaned


class Settings:
    @property
    def database_url(self) -> str:
        return os.environ.get("DATABASE_URL", "").strip()

    @property
    def openrouter_key(self) -> str:
        return _secret("OPENROUTER_API_KEY")

    @property
    def app_password(self) -> str:
        return os.environ.get("APP_PASSWORD", "").strip()

    @property
    def youtube_default(self) -> str:
        return os.environ.get(
            "STREAM_URL",
            os.environ.get(
                "YOUTUBE_URL",
                "https://playerservices.streamtheworld.com/api/livestream-redirect/BANDNEWSFM_SPAAC.m3u8?dist=bandsite",
            ),
        ).strip()

    @property
    def stt_model(self) -> str:
        return os.environ.get("OPENROUTER_STT_MODEL", "openai/whisper-large-v3").strip()

    @property
    def extract_model(self) -> str:
        return os.environ.get(
            "OPENROUTER_EXTRACT_MODEL", "anthropic/claude-haiku-4.5"
        ).strip()

    @property
    def fact_model(self) -> str:
        return os.environ.get(
            "OPENROUTER_FACT_MODEL", "perplexity/sonar"
        ).strip()

    @property
    def chunk_seconds(self) -> int:
        return _int("CHUNK_SECONDS", 12)

    @property
    def youtube_cookies(self) -> str:
        return os.environ.get("YOUTUBE_COOKIES", "").strip()

    @property
    def cookies_path(self) -> str:
        return os.environ.get("YOUTUBE_COOKIES_PATH", "/tmp/youtube-cookies.txt").strip()

    @property
    def referer(self) -> str:
        return os.environ.get(
            "OPENROUTER_HTTP_REFERER",
            "https://checagem-debate-app.kxryyk.easypanel.host",
        ).strip()


settings = Settings()
