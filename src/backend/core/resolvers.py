"""
resolver_conceito() é a função mais importante do sistema: é ela que
resolve "este código bruto de disciplina, neste curso, corresponde a qual
CONCEITO_DISCIPLINA?" (ver ADR 0003, RN06, RN06.1).

Todo cálculo de Grupo A, B ou C passa por aqui antes de comparar
disciplinas entre si. Nunca compare `disciplina_codigo` diretamente —
sempre resolva para conceito primeiro.

Este arquivo já é código real e funcional (não pseudo-código) — depende só
do banco estar populado (ETL) para ter dado pra resolver.
"""
from typing import Optional

from sqlalchemy.orm import Session

from db.models import CodigoDisciplina


def resolver_conceito(db: Session, curso_codigo: str, disciplina_codigo: str) -> Optional[str]:
    """
    Dado um código bruto de disciplina (do jeito que apareceu no CSV) e o
    curso, retorna o id do CONCEITO_DISCIPLINA correspondente.

    Retorna None se o código não foi reconhecido pelo ETL (isso não deveria
    acontecer silenciosamente em produção — códigos não resolvidos são
    reportados como exceção pelo ETL, RF05. Se aparecer None aqui em tempo
    de consulta, é sinal de dado inconsistente que passou despercebido.)
    """
    registro = (
        db.query(CodigoDisciplina)
        .filter(
            CodigoDisciplina.curso_codigo == curso_codigo,
            CodigoDisciplina.codigo == disciplina_codigo,
        )
        .first()
    )
    return registro.conceito_id if registro else None
