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


class SolicitarAcessoRequest(BaseModel):
    email: str


class DefinirSenhaRequest(BaseModel):
    token: str
    nova_senha: str


class CadastroRequest(BaseModel):
    email: str
    senha: str


def verificar_senha(senha_plana: str, senha_hash: str) -> bool:
    if not senha_hash:
        return False
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


def _enviar_email_ativacao(destinatario: str, link_ativacao: str) -> bool:
    """
    Envia e-mail real com o link seguro de ativação/definição de senha via SMTP.
    Caso o SMTP não esteja configurado (ambiente local/desenvolvimento), registra
    claramente o link no terminal para testes imediatos sem bloquear o usuário.
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    print(f"\n=================================================================")
    print(f"[AUTH] Link seguro de definição de senha para {destinatario}:")
    print(f"       {link_ativacao}")
    print(f"=================================================================\n")

    if not settings.smtp_server or not settings.smtp_user:
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Sistema de Oferta de Disciplinas - Definição de Senha de Acesso"
        msg["From"] = settings.smtp_from or settings.smtp_user
        msg["To"] = destinatario

        texto = f"""Olá Coordenador(a),

Você solicitou acesso ao Sistema de Planejamento de Oferta de Disciplinas (Unipampa).
Para definir sua senha de acesso e ativar sua conta, acesse o link abaixo (válido por 24 horas):

{link_ativacao}

Caso não tenha solicitado este acesso, favor desconsiderar este e-mail.
"""
        html = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; padding: 20px;">
  <div style="max-width: 580px; margin: 0 auto; background: #ffffff; padding: 32px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    <div style="border-bottom: 2px solid #0f766e; padding-bottom: 16px; margin-bottom: 24px;">
      <h2 style="color: #0f766e; margin: 0; font-size: 20px;">Sistema de Planejamento de Oferta de Disciplinas</h2>
      <p style="color: #64748b; font-size: 13px; margin: 4px 0 0 0;">Universidade Federal do Pampa — Campus Alegrete</p>
    </div>
    <p>Olá,</p>
    <p>Você solicitou seu acesso de coordenador ao <strong>Sistema de Oferta de Disciplinas</strong>.</p>
    <p>Clique no botão abaixo para definir sua senha pessoal e ter acesso ao seu painel individual:</p>
    <div style="text-align: center; margin: 32px 0;">
      <a href="{link_ativacao}" style="background-color: #0f766e; color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px; display: inline-block;">Criar Minha Senha</a>
    </div>
    <p style="font-size: 13px; color: #64748b; margin-top: 24px;">Ou utilize o link direto no seu navegador:<br>
      <a href="{link_ativacao}" style="color: #0f766e; word-break: break-all;">{link_ativacao}</a>
    </p>
    <div style="margin-top: 36px; padding-top: 16px; border-top: 1px solid #f1f5f9; font-size: 12px; color: #94a3b8;">
      <p style="margin: 0;">Este link de segurança é exclusivo e expira em 24 horas.</p>
      <p style="margin: 4px 0 0 0;">Se você não solicitou este acesso, ignore esta mensagem com segurança.</p>
    </div>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(texto, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))

        server = smtplib.SMTP(settings.smtp_server, settings.smtp_port, timeout=10)
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(msg["From"], [destinatario], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[AUTH ERROR] Falha ao enviar e-mail via SMTP ({destinatario}): {e}")
        return False


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


@router.post("/solicitar-acesso")
def solicitar_acesso(req: SolicitarAcessoRequest, db: Session = Depends(get_db)):
    """
    Cadastra o e-mail de um novo coordenador ou gera link de redefinição para existentes.
    Gera um link seguro com token JWT com validade de 24 horas.
    """
    from api.deps import registrar_acesso
    email_limpo = req.email.strip().lower()
    if not email_limpo or "@" not in email_limpo or "." not in email_limpo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe um endereço de e-mail válido.",
        )

    usuario = db.query(Usuario).filter(Usuario.email == email_limpo).first()
    if not usuario:
        usuario = Usuario(
            email=email_limpo,
            senha_hash=None,
            papel="coordenador",
            ativo=False,  # Será ativado após definição da senha
        )
        db.add(usuario)
        db.commit()
        db.refresh(usuario)

    # Token com expiração de 24h
    expiracao = datetime.now(timezone.utc) + timedelta(hours=24)
    token = jwt.encode(
        {"sub": usuario.email, "type": "definir_senha", "exp": expiracao},
        settings.secret_key,
        algorithm="HS256",
    )

    link_ativacao = f"{settings.frontend_url}/definir-senha?token={token}"
    email_enviado = _enviar_email_ativacao(usuario.email, link_ativacao)

    registrar_acesso(
        db,
        "solicitacao_acesso",
        f"Email: {usuario.email}, Enviado via SMTP: {email_enviado}",
        usuario.id,
    )

    return {
        "status": "sucesso",
        "email": usuario.email,
        "email_enviado": email_enviado,
        "link_ativacao": link_ativacao,
        "mensagem": (
            f"Link seguro enviado com sucesso para o e-mail {usuario.email}."
            if email_enviado
            else "Link de ativação gerado com sucesso. Como o servidor SMTP não está ativo no momento, copie o link de teste abaixo."
        ),
    }


@router.post("/definir-senha")
def definir_senha(req: DefinirSenhaRequest, db: Session = Depends(get_db)):
    """
    Recebe o token de ativação e a nova senha, valida a assinatura e expiração,
    e registra a senha (com hash bcrypt), ativando a conta do coordenador.
    Retorna o token de acesso (JWT) para login imediato.
    """
    from api.deps import registrar_acesso

    if not req.nova_senha or len(req.nova_senha) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha deve ter no mínimo 6 caracteres.",
        )

    try:
        payload = jwt.decode(req.token, settings.secret_key, algorithms=["HS256"])
        if payload.get("type") != "definir_senha":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tipo de token inválido para definição de senha.")
        email: str = payload.get("sub")
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido.")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Este link expirou (validade de 24 horas). Solicite um novo link.")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Link ou token de ativação inválido.")

    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado.")

    # Cria o hash bcrypt
    senha_hash = bcrypt.hashpw(req.nova_senha.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    usuario.senha_hash = senha_hash
    usuario.ativo = True
    db.commit()

    _limpar_falhas(usuario.email)
    registrar_acesso(db, "definicao_senha_sucesso", f"Email: {usuario.email}", usuario.id)

    # Gera token de sessão para acesso imediato
    access_token = criar_token_acesso(data={"sub": usuario.email, "role": usuario.papel})
    return {
        "status": "sucesso",
        "mensagem": "Senha definida com sucesso! Acesso concedido.",
        "access_token": access_token,
        "token_type": "bearer",
        "email": usuario.email,
        "role": usuario.papel,
    }


@router.post("/cadastrar")
def cadastrar_usuario(req: CadastroRequest, db: Session = Depends(get_db)):
    """
    Cadastra diretamente um novo coordenador com sua senha na plataforma.
    Não requer envio de e-mail e libera acesso imediato com token JWT.
    """
    from api.deps import registrar_acesso
    email_limpo = req.email.strip().lower()
    if not email_limpo or "@" not in email_limpo or "." not in email_limpo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informe um endereço de e-mail institucional válido.",
        )

    if not req.senha or len(req.senha) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A senha deve conter no mínimo 6 caracteres.",
        )

    existente = db.query(Usuario).filter(Usuario.email == email_limpo).first()
    senha_hash = bcrypt.hashpw(req.senha.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")

    if existente:
        if existente.ativo and existente.senha_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Este e-mail já está cadastrado no sistema. Por favor, faça login com sua senha.",
            )
        # Se usuário já existia mas estava inativo/pendente de senha
        existente.senha_hash = senha_hash
        existente.ativo = True
        usuario = existente
    else:
        usuario = Usuario(
            email=email_limpo,
            senha_hash=senha_hash,
            papel="coordenador",
            ativo=True,
        )
        db.add(usuario)

    db.commit()
    db.refresh(usuario)

    _limpar_falhas(usuario.email)
    registrar_acesso(db, "cadastro_direto_sucesso", f"Email: {usuario.email}", usuario.id)

    access_token = criar_token_acesso(data={"sub": usuario.email, "role": usuario.papel})
    return {
        "status": "sucesso",
        "mensagem": "Cadastro realizado com sucesso! Acesso liberado.",
        "access_token": access_token,
        "token_type": "bearer",
        "email": usuario.email,
        "role": usuario.papel,
    }


