"""
Configuração central do backend.

Lê o arquivo .env (ver .env.example) e expõe as variáveis como um objeto
tipado. Qualquer outro módulo que precisar de uma variável de ambiente
importa `settings` daqui — em vez de chamar os.environ espalhado pelo
código.
"""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 30
    historico_ano_corte: int = 2016
    frontend_url: str = "http://localhost:5173"

    # Configurações de SMTP para envio real de e-mails
    smtp_server: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_use_tls: bool = True

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
