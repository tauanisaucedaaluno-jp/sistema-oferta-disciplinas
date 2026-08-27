"""
Funções utilitárias e dependências para a API (deps.py).
"""
from sqlalchemy.orm import Session
from db.models import LogAcesso


def registrar_acesso(db: Session, acao: str, detalhe: str = None, usuario_id: int = None):
    """Grava um registro de log de acesso na tabela log_acesso para auditoria (RNF05)."""
    try:
        log = LogAcesso(
            usuario_id=usuario_id,
            acao=acao,
            detalhe=detalhe
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Erro ao salvar log de acesso: {e}")
