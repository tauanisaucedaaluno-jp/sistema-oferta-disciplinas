from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from db.database import get_db
from db.models import Usuario

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login-form")

class Token(BaseModel):
    access_token: str
    token_type: str

class LoginRequest(BaseModel):
    email: str
    senha: str

def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    return bcrypt.checkpw(senha_plana.encode("utf-8"), senha_hash.encode("utf-8"))

def criar_token_acesso(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm="HS256")
    return encoded_jwt


# ---------------------------------------------------------------------------
# RNF03 – Limitação de tentativas de login (bloqueio temporário por 15 min)
# ---------------------------------------------------------------------------
# Estrutura: { email: {"tentativas": int, "bloqueado_ate": datetime | None} }
_tentativas_falha: dict = {}
_MAX_TENTATIVAS = 5
_BLOQUEIO_MINUTOS = 15


def _verificar_bloqueio(email: str):
    """Levanta 403 se o e-mail ainda está no período de bloqueio."""
    estado = _tentativas_falha.get(email)
    if estado and estado["bloqueado_ate"] and datetime.now(timezone.utc) < estado["bloqueado_ate"]:
        restante = int((estado["bloqueado_ate"] - datetime.now(timezone.utc)).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Conta temporariamente bloqueada devido a múltiplas tentativas falhas. Tente novamente em {restante} minuto(s).",
        )


def _registrar_falha(email: str):
    """Incrementa o contador de tentativas falhas e bloqueia após _MAX_TENTATIVAS."""
    estado = _tentativas_falha.setdefault(email, {"tentativas": 0, "bloqueado_ate": None})
    estado["tentativas"] += 1
    if estado["tentativas"] >= _MAX_TENTATIVAS:
        estado["bloqueado_ate"] = datetime.now(timezone.utc) + timedelta(minutes=_BLOQUEIO_MINUTOS)
        estado["tentativas"] = 0  # reseta para próximo ciclo após bloqueio


def _limpar_falhas(email: str):
    """Limpa o contador de falhas após login bem-sucedido."""
    _tentativas_falha.pop(email, None)


@router.post("/login", response_model=Token)
def login_json(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Endpoint de login aceitando JSON (e-mail e senha)."""
    from api.deps import registrar_acesso
    _verificar_bloqueio(credentials.email)
    usuario = db.query(Usuario).filter(Usuario.email == credentials.email).first()
    if not usuario or not verificar_senha(credentials.senha, usuario.senha_hash):
        _registrar_falha(credentials.email)
        registrar_acesso(db, "login_falha", f"Email: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not usuario.ativo:
        registrar_acesso(db, "login_falha", f"Usuário inativo: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo",
        )
    _limpar_falhas(credentials.email)
    registrar_acesso(db, "login_sucesso", f"Email: {credentials.email}", usuario.id)
    access_token = criar_token_acesso(data={"sub": usuario.email, "role": usuario.papel})
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login-form", response_model=Token)
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Endpoint de login padrão OAuth2 (para testes interativos no Swagger)."""
    from api.deps import registrar_acesso
    _verificar_bloqueio(form_data.username)
    usuario = db.query(Usuario).filter(Usuario.email == form_data.username).first()
    if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
        _registrar_falha(form_data.username)
        registrar_acesso(db, "login_falha", f"Email: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not usuario.ativo:
        registrar_acesso(db, "login_falha", f"Usuário inativo: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário inativo",
        )
    _limpar_falhas(form_data.username)
    registrar_acesso(db, "login_sucesso", f"Email: {form_data.username}", usuario.id)
    access_token = criar_token_acesso(data={"sub": usuario.email, "role": usuario.papel})
    return {"access_token": access_token, "token_type": "bearer"}

def obter_usuario_atual(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Usuario:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if usuario is None:
        raise credentials_exception
    if not usuario.ativo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inativo")
    return usuario
