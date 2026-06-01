from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    app_env: str = 'dev'
    database_url: str = 'sqlite:///./data/app.db'
    tz: str = 'America/Sao_Paulo'

    telegram_bot_token: str = ''
    telegram_chat_id: str = '148008296'

    llm_base_url: str = ''
    llm_api_key: str = ''
    llm_model: str = 'openai/gpt-5.4-nano'

    smtp_enabled: bool = False
    smtp_host: str = ''
    smtp_port: int = 587
    smtp_user: str = ''
    smtp_password: str = ''
    smtp_to: str = 'evandro.prieto@onnitech.com.br'

settings = Settings()
