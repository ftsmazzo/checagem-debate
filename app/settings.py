import os


def _int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return int(raw)


class Settings:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    app_password = os.environ.get("APP_PASSWORD", "").strip()
    youtube_default = os.environ.get(
        "STREAM_URL",
        os.environ.get(
            "YOUTUBE_URL",
            "https://playerservices.streamtheworld.com/api/livestream-redirect/BANDNEWSFM_SPAAC.m3u8?dist=bandsite",
        ),
    ).strip()
    stt_model = os.environ.get("OPENROUTER_STT_MODEL", "openai/whisper-large-v3").strip()
    extract_model = os.environ.get(
        "OPENROUTER_EXTRACT_MODEL", "google/gemini-2.5-flash"
    ).strip()
    fact_model = os.environ.get(
        "OPENROUTER_FACT_MODEL", "google/gemini-2.5-flash:online"
    ).strip()
    chunk_seconds = _int("CHUNK_SECONDS", 12)
    youtube_cookies = os.environ.get("YOUTUBE_COOKIES", "").strip()
    cookies_path = os.environ.get("YOUTUBE_COOKIES_PATH", "/tmp/youtube-cookies.txt").strip()
    referer = os.environ.get(
        "OPENROUTER_HTTP_REFERER", "https://checagem-debate-app.kxryyk.easypanel.host"
    ).strip()


settings = Settings()
