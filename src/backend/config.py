"""
Configuração central do backend.

Lê o arquivo .env (ver .env.example) e expõe as variáveis como um objeto
tipado. Qualquer outro módulo que precisar de uma variável de ambiente
importa `settings` daqui — em vez de chamar os.environ espalhado pelo
código.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 30
    historico_ano_corte: int = 2016

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
