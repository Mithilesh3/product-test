from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ==========================
    # APP
    # ==========================
    APP_NAME: str = "Life Signify Ank(अंक) AI SaaS"
    ENGINE_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG_LOGGING: bool = False
    ENABLE_MOCK_PAYMENTS: bool = False
    AI_FALLBACK_LOG_THRESHOLD: int = 1
    AI_REPORT_SKIP_AZURE_FOR_BASIC: bool = False
    AI_REPORT_AZURE_REQUEST_TIMEOUT_SECONDS: float = 90.0
    AI_REPORT_AZURE_MAX_RETRIES: int = 1
    AI_REPORT_AZURE_ENABLE_TARGETED_REWRITE: bool = True
    AI_REPORT_FORCE_LLM_NARRATIVE: bool = False
    AI_REPORT_DISABLE_LLM: bool = True
    AI_BASIC_UNIQUENESS_GATE_ENABLED: bool = True
    AI_BASIC_UNIQUENESS_GATE_THRESHOLD: float = 0.80
    AI_BASIC_UNIQUENESS_GATE_MAX_PASSES: int = 2
    AI_REPORT_HINDI_POLISH_PASS: bool = True

    # ==========================
    # DATABASE
    # ==========================
    DATABASE_URL: str

    # ==========================
    # JWT
    # ==========================
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ==========================
    # AZURE OPENAI
    # ==========================
    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_API_VERSION: str = "2024-02-15-preview"
    AZURE_OPENAI_DEPLOYMENT: str
    AZURE_OPENAI_AUDIO_DEPLOYMENT: str | None = None

    # ==========================
    # KNOWLEDGE STUDIO
    # ==========================
    KNOWLEDGE_ASSET_STORAGE_PATH: str = "storage/admin_knowledge"

    # ==========================
    # PAYMENTS
    # ==========================
    PAYMENT_PROVIDER: str = "razorpay"
    RAZORPAY_KEY_ID: str | None = None
    RAZORPAY_KEY_SECRET: str | None = None
    PHONEPE_CLIENT_ID: str | None = None
    PHONEPE_CLIENT_SECRET: str | None = None
    PHONEPE_CLIENT_VERSION: int = 1
    PHONEPE_AUTH_URL: str = "https://api-preprod.phonepe.com/apis/pg-sandbox/v1/oauth/token"
    PHONEPE_PAY_URL: str = "https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/pay"
    PHONEPE_STATUS_URL_TEMPLATE: str = "https://api-preprod.phonepe.com/apis/pg-sandbox/checkout/v2/order/{order_id}/status"
    PHONEPE_PAYMENT_RETURN_URL: str = "http://localhost:5173/billing"
    PHONEPE_KYC_RETURN_URL: str = "http://localhost:5173/register"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
