from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smiger_bot"
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM (chat completions)
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://www.sophnet.com/api/open-apis/v1"
    LLM_MODEL: str = "DeepSeek-V3.2"

    # Embedding (sophnet custom API)
    EMBEDDING_URL: str = "https://www.sophnet.com/api/open-apis/projects/2BBzpkOwzr6ylj8CUoKPnJ/easyllms/embeddings"
    EMBEDDING_EASYLLM_ID: str = "1mpWbqbmXnBRBdecJQPcFw"
    EMBEDDING_DIMENSIONS: int = 1024

    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    RETRIEVAL_TOP_K: int = 5
    SIMILARITY_THRESHOLD: float = 0.3
    LEAD_TRIGGER_TURN: int = 3
    MAX_HISTORY_TURNS: int = 10
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "smiger2026"
    SECRET_KEY: str = "smiger-bot-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # WhatsApp Business Cloud API
    WHATSAPP_ENABLED: bool = False
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_ADMIN_PHONE: str = ""
    WHATSAPP_TEMPLATE_NAME: str = ""

    # Telegram Bot API
    TELEGRAM_ENABLED: bool = False
    TELEGRAM_MODE: str = "polling"
    TELEGRAM_BOT_TOKEN: str = "8590443955:AAG19dqUHXidjxNCcexEmVg62h5dOQxLJoU"
    TELEGRAM_ADMIN_CHAT_ID: str = "8432959658"
    TELEGRAM_WEBHOOK_SECRET: str = ""
    TELEGRAM_WEBHOOK_BASE_URL: str = ""
    TELEGRAM_BOT_ACCOUNTS: str = ""
    TELEGRAM_ACTIVE_ACCOUNT: str = ""

    # Google Chat (Workspace)
    GCHAT_ENABLED: bool = False
    GCHAT_WEBHOOK_URL: str = ""
    GCHAT_VERIFY_TOKEN: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
