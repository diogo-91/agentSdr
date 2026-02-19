"""
Configurações centrais da aplicação via variáveis de ambiente.
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Grok AI / OpenRouter
    grok_api_key: str = Field(..., env="GROK_API_KEY")
    grok_model: str = Field(default="grok-2-latest", env="GROK_MODEL")
    openrouter_base_url: str | None = Field(default=None, env="OPENROUTER_BASE_URL")

    # Supabase
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_service_key: str = Field(..., env="SUPABASE_SERVICE_KEY")

    # Google Sheets
    google_sheets_id: str = Field(..., env="GOOGLE_SHEETS_ID")
    google_credentials_path: str = Field(
        default="credentials.json", env="GOOGLE_CREDENTIALS_PATH"
    )
    google_credentials_json: str | None = Field(
        default=None, env="GOOGLE_CREDENTIALS_JSON"
    )

    # Evolution API
    evolution_api_url: str = Field(..., env="EVOLUTION_API_URL")
    evolution_api_key: str = Field(..., env="EVOLUTION_API_KEY")
    evolution_instance: str = Field(..., env="EVOLUTION_INSTANCE")

    # Gestor de Vendas
    manager_phone: str = Field(..., env="MANAGER_PHONE")

    # Empresa / Agente
    agent_name: str = Field(default="Ana Laura", env="AGENT_NAME")
    company_name: str = Field(default="Empresa", env="COMPANY_NAME")
    company_tagline: str = Field(default="", env="COMPANY_TAGLINE")
    company_phone: str = Field(default="", env="COMPANY_PHONE")
    company_email: str = Field(default="", env="COMPANY_EMAIL")
    company_logo_url: str = Field(default="", env="COMPANY_LOGO_URL")

    # Configurações do Agente
    webhook_secret: str = Field(default="", env="WEBHOOK_SECRET")
    max_history_messages: int = Field(default=20, env="MAX_HISTORY_MESSAGES")
    quote_validity_days: int = Field(default=7, env="QUOTE_VALIDITY_DAYS")
    port: int = Field(default=8000, env="PORT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()
