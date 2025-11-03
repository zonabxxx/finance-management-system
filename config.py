"""
Konfigurácia pre Finance Tracker aplikáciu
"""
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Hlavná konfigurácia aplikácie"""
    
    # Turso Database
    turso_database_url: str = Field(..., env='TURSO_DATABASE_URL')
    turso_auth_token: str = Field(..., env='TURSO_AUTH_TOKEN')
    
    # OpenAI
    openai_api_key: str = Field(..., env='OPENAI_API_KEY')
    openai_model: str = Field(default='gpt-4-turbo-preview', env='OPENAI_MODEL')
    openai_assistant_id: str = Field(..., env='OPENAI_ASSISTANT_ID')
    
    # Finstat API
    finstat_api_key: str = Field(..., env='FINSTAT_API_KEY')
    finstat_private_key: str = Field(..., env='FINSTAT_PRIVATE_KEY')
    finstat_api_url: str = Field(default='https://www.finstat.sk/api', env='FINSTAT_API_URL')
    finstat_station_id: str = Field(default='FinanceTracker', env='FINSTAT_STATION_ID')
    finstat_station_name: str = Field(default='Finance Tracker App', env='FINSTAT_STATION_NAME')
    
    # Email parsing
    email_parser_endpoint: str = Field(..., env='EMAIL_PARSER_ENDPOINT')
    
    # Azure Storage
    azure_storage_connection_string: str = Field(..., env='AZURE_STORAGE_CONNECTION_STRING')
    
    # Application Insights
    appinsights_instrumentation_key: str = Field(..., env='APPINSIGHTS_INSTRUMENTATION_KEY')
    
    # Categorization
    ai_confidence_threshold: float = Field(default=0.7, env='AI_CONFIDENCE_THRESHOLD')
    use_finstat_for_unknown: bool = Field(default=True, env='USE_FINSTAT_FOR_UNKNOWN')
    enable_web_scraping: bool = Field(default=True, env='ENABLE_WEB_SCRAPING')
    
    # ChatGPT Agent
    agent_name: str = Field(default='Finance Assistant SK', env='AGENT_NAME')
    agent_instructions: str = Field(
        default='Pomáhaš používateľovi analyzovať jeho výdavky a príjmy. Odpovedáš v slovenčine.',
        env='AGENT_INSTRUCTIONS'
    )
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


settings = Settings()

