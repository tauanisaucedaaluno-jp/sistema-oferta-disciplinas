"""
Motor de regras: implementa RF07–RF11 e a Seção 7 do system-design.md.

Os três grupos, em uma frase cada:

- Grupo A: quem JÁ está cursando a disciplina agora.
- Grupo B: quem PODERIA se matricular agora (já cumpriu tudo, ainda não
  cursou) mas não está matriculado.
- Grupo C: quem provavelmente PODERÁ se matricular no futuro, porque está
  cursando algum pré-requisito agora.

Cada função aqui recebe `curso_codigo` + `conceito_id` (nunca disciplina
isolada — ADR 0001) e devolve a lista de matrículas de alunos que caem
naquele grupo. `demanda_estimada()` soma tudo, seguindo a fórmula de RN08.

NOTA IMPORTANTE (gap conhecido, deixado explícito de propósito):
RN07 define que pré-requisitos na mesma lista podem ser "E" (todos
obrigatórios) ou "OU" (alternativos, via campo `equivalencias`), mas o
schema atual de PRE_REQUISITO (Seção 6 do system-design.md) não tem uma
coluna para marcar quais linhas formam um grupo "OU". A implementação
abaixo assume que TODOS os pré-requisitos de um conceito são exigidos (E)
— o caso mais comum. Tratar RN07 corretamente é a Issue "Grupo B/C:
suportar pré-requisitos alternativos (RN07)" na divisão de issues — não
pule essa decisão silenciosamente.
"""
from typing import List
from dataclasses import dataclass

from sqlalchemy.orm import Session

from db.models import Historico, Aluno, PreRequisito
from core.resolvers import resolver_conceito

ESTADOS_APROVADO = {"aprovado"}  # ver RN04 — já normalizado pelo ETL


def _historico_do_aluno_no_conceito(
    db: Session, matricula: str, curso_codigo: str, conceito_id: str
) -> List[Historico]:
    """Todas as linhas de histórico do aluno cujo código resolve para este conceito."""
    linhas = (
        db.query(Historico)
        .filter(
            Historico.aluno_matricula == matricula,
            Historico.curso_codigo == curso_codigo,
        )
        .all()
    )
    return [
        h
        for h in linhas
        if resolver_conceito(db, curso_codigo, h.disciplina_codigo) == conceito_id
    ]


def grupo_a(db: Session, curso_codigo: str, conceito_id: str, periodo_atual: str) -> List[str]:
    """RF07 — matrículas dos alunos cursando o conceito agora."""
    alunos_curso = db.query(Aluno.matricula).filter(Aluno.curso_codigo == curso_codigo).all()
    resultado = []
    for (matricula,) in alunos_curso:
        historico = _historico_do_aluno_no_conceito(db, matricula, curso_codigo, conceito_id)
        cursando_agora = any(
            h.periodo_letivo == periodo_atual and h.situacao == "cursando" for h in historico
        )
        if cursando_agora:
            resultado.append(matricula)
    return resultado


def grupo_b(db: Session, curso_codigo: str, conceito_id: str) -> List[str]:
    """
    RF08 — aptos e não matriculados: cumpriram TODOS os pré-requisitos
    (ver nota sobre RN07 no topo do arquivo) e não estão, atualmente,
    aprovados ou cursando o próprio conceito.
    """
    pre_requisitos = (
        db.query(PreRequisito.conceito_prerequisito_id)
        .filter(
            PreRequisito.curso_codigo == curso_codigo,
            PreRequisito.conceito_id == conceito_id,
        )
        .all()
    )
    pre_requisito_ids = [p[0] for p in pre_requisitos]

    alunos_curso = db.query(Aluno.matricula).filter(Aluno.curso_codigo == curso_codigo).all()
    resultado = []
    for (matricula,) in alunos_curso:
        cumpriu_todos = all(
            any(
                h.situacao in ESTADOS_APROVADO
                for h in _historico_do_aluno_no_conceito(db, matricula, curso_codigo, pre_id)
            )
            for pre_id in pre_requisito_ids
        )
        if not cumpriu_todos:
            continue

        historico_alvo = _historico_do_aluno_no_conceito(db, matricula, curso_codigo, conceito_id)
        ja_aprovado_ou_cursando = any(
            h.situacao in ESTADOS_APROVADO or h.situacao == "cursando" for h in historico_alvo
        )
        if not ja_aprovado_ou_cursando:
            resultado.append(matricula)
    return resultado


@dataclass
class AlunoGrupoC:
    matricula: str
    probabilidade_aprovacao: float


def probabilidade_aprovacao_nivel1(db: Session, conceito_id: str) -> float:
    """
    RN09 — Nível 1 (MVP): taxa histórica agregada de aprovação do conceito,
    somando todos os códigos históricos que resolvem para ele.

    aprovados / (aprovados + reprovados) — situações 'cursando', 'trancado'
    e 'indefinido' não entram no denominador porque não representam um
    resultado final ainda (ou, no caso de indefinido, já foi decidido em
    RN04.1 tratar como não-aprovado só para checagem de pré-requisito, não
    para esta taxa histórica).
    """
    from sqlalchemy import func
    from db.models import CodigoDisciplina

    query = (
        db.query(Historico.situacao, func.count(Historico.id))
        .join(
            CodigoDisciplina,
            (Historico.curso_codigo == CodigoDisciplina.curso_codigo) &
            (Historico.disciplina_codigo == CodigoDisciplina.codigo)
        )
        .filter(CodigoDisciplina.conceito_id == conceito_id)
        .filter(Historico.situacao.in_(["aprovado", "reprovado"]))
        .group_by(Historico.situacao)
        .all()
    )

    aprovados = 0
    reprovados = 0
    for situacao, count in query:
        if situacao == "aprovado":
            aprovados += count
        elif situacao == "reprovado":
            reprovados += count

    total = aprovados + reprovados
    if total == 0:
        return 0.0
    return aprovados / total


def grupo_c(db: Session, curso_codigo: str, conceito_id: str, periodo_atual: str) -> List[AlunoGrupoC]:
    """RF09 — cursando algum pré-requisito agora, com probabilidade estimada."""
    pre_requisitos = (
        db.query(PreRequisito.conceito_prerequisito_id)
        .filter(
            PreRequisito.curso_codigo == curso_codigo,
            PreRequisito.conceito_id == conceito_id,
        )
        .all()
    )
    pre_requisito_ids = [p[0] for p in pre_requisitos]

    alunos_curso = db.query(Aluno.matricula).filter(Aluno.curso_codigo == curso_codigo).all()
    resultado = []
    for (matricula,) in alunos_curso:
        for pre_id in pre_requisito_ids:
            historico = _historico_do_aluno_no_conceito(db, matricula, curso_codigo, pre_id)
            cursando = any(
                h.periodo_letivo == periodo_atual and h.situacao == "cursando" for h in historico
            )
            if cursando:
                resultado.append(
                    AlunoGrupoC(
                        matricula=matricula,
                        probabilidade_aprovacao=probabilidade_aprovacao_nivel1(db, pre_id),
                    )
                )
                break  # RF09: um aluno entra uma vez no grupo por conceito-alvo
    return resultado


def demanda_estimada(db: Session, curso_codigo: str, conceito_id: str, periodo_atual: str) -> float:
    """RN08 — |Grupo A| + |Grupo B| + soma das probabilidades do Grupo C."""
    a = grupo_a(db, curso_codigo, conceito_id, periodo_atual)
    b = grupo_b(db, curso_codigo, conceito_id)
    c = grupo_c(db, curso_codigo, conceito_id, periodo_atual)
    return len(a) + len(b) + sum(aluno.probabilidade_aprovacao for aluno in c)
