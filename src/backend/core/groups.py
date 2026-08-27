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


def _aluno_esta_ativo(db: Session, matricula: str) -> bool:
    """RN05 — Retorna False se o aluno estiver evadido (Abandono, Cancelamento, etc.) no seu período mais recente."""
    ultimo_historico = (
        db.query(Historico)
        .filter(Historico.aluno_matricula == matricula)
        .order_by(Historico.periodo_letivo.desc(), Historico.id.desc())
        .first()
    )
    if ultimo_historico and ultimo_historico.situacao_matricula in {
        "Abandono", "Cancelamento", "Desligamento", "Falecimento", "Cancelamento Sisu", "Guri"
    }:
        return False
    return True


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


def _periodo_mesmo(p1: str, p2: str) -> bool:
    """Verifica se dois períodos letivos representam o mesmo semestre (ex.: '2026/1' == '20261' == '2026/01')."""
    if not p1 or not p2:
        return False
    c1 = p1.replace("/", "").replace("-", "").strip()
    c2 = p2.replace("/", "").replace("-", "").strip()
    if len(c1) == 6 and c1[4] == "0":
        c1 = c1[:4] + c1[5]
    if len(c2) == 6 and c2[4] == "0":
        c2 = c2[:4] + c2[5]
    return c1 == c2


def grupo_a(db: Session, curso_codigo: str, conceito_id: str, periodo_atual: str) -> List[str]:
    """RF07 — matrículas dos alunos cursando o conceito agora."""
    alunos_curso = db.query(Aluno.matricula).filter(Aluno.curso_codigo == curso_codigo).all()
    resultado = []
    for (matricula,) in alunos_curso:
        historico = _historico_do_aluno_no_conceito(db, matricula, curso_codigo, conceito_id)
        cursando_agora = any(
            _periodo_mesmo(h.periodo_letivo, periodo_atual) and h.situacao == "cursando" for h in historico
        )
        if cursando_agora:
            resultado.append(matricula)
    return resultado


def grupo_b(db: Session, curso_codigo: str, conceito_id: str) -> List[str]:
    """
    RF08 — aptos e não matriculados: cumpriram TODOS os pré-requisitos
    (suportando cláusulas E/OU via grupo_alternativo) e não estão, atualmente,
    aprovados ou cursando o próprio conceito.
    """
    pre_requisitos = (
        db.query(PreRequisito)
        .filter(
            PreRequisito.curso_codigo == curso_codigo,
            PreRequisito.conceito_id == conceito_id,
        )
        .all()
    )

    req_obrigatorios = [p.conceito_prerequisito_id for p in pre_requisitos if p.grupo_alternativo is None]
    
    req_alternativos = {}
    for p in pre_requisitos:
        if p.grupo_alternativo is not None:
            if p.grupo_alternativo not in req_alternativos:
                req_alternativos[p.grupo_alternativo] = []
            req_alternativos[p.grupo_alternativo].append(p.conceito_prerequisito_id)

    alunos_curso = db.query(Aluno.matricula).filter(Aluno.curso_codigo == curso_codigo).all()
    resultado = []
    for (matricula,) in alunos_curso:
        if not _aluno_esta_ativo(db, matricula):
            continue
        # Verifica se já passou ou está cursando a disciplina alvo
        historico_alvo = _historico_do_aluno_no_conceito(db, matricula, curso_codigo, conceito_id)
        ja_aprovado_ou_cursando = any(
            h.situacao in ESTADOS_APROVADO or h.situacao == "cursando" for h in historico_alvo
        )
        if ja_aprovado_ou_cursando:
            continue

        # 1. Verifica se cumpriu todos os obrigatórios (E)
        cumpriu_obrigatorios = all(
            any(
                h.situacao in ESTADOS_APROVADO
                for h in _historico_do_aluno_no_conceito(db, matricula, curso_codigo, pre_id)
            )
            for pre_id in req_obrigatorios
        )
        if not cumpriu_obrigatorios:
            continue

        # 2. Verifica se cumpriu pelo menos um de cada grupo alternativo (OU)
        cumpriu_alternativos = True
        for grupo, pre_ids in req_alternativos.items():
            passou_em_algum = any(
                any(
                    h.situacao in ESTADOS_APROVADO
                    for h in _historico_do_aluno_no_conceito(db, matricula, curso_codigo, pre_id)
                )
                for pre_id in pre_ids
            )
            if not passou_em_algum:
                cumpriu_alternativos = False
                break
        
        if cumpriu_alternativos:
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
        db.query(PreRequisito)
        .filter(
            PreRequisito.curso_codigo == curso_codigo,
            PreRequisito.conceito_id == conceito_id,
        )
        .all()
    )

    if not pre_requisitos:
        return []

    req_obrigatorios = [p.conceito_prerequisito_id for p in pre_requisitos if p.grupo_alternativo is None]
    
    req_alternativos = {}
    for p in pre_requisitos:
        if p.grupo_alternativo is not None:
            if p.grupo_alternativo not in req_alternativos:
                req_alternativos[p.grupo_alternativo] = []
            req_alternativos[p.grupo_alternativo].append(p.conceito_prerequisito_id)

    alunos_curso = db.query(Aluno.matricula).filter(Aluno.curso_codigo == curso_codigo).all()
    resultado = []
    for (matricula,) in alunos_curso:
        if not _aluno_esta_ativo(db, matricula):
            continue
        # Primeiro, verifica se já passou ou está cursando a disciplina alvo
        historico_alvo = _historico_do_aluno_no_conceito(db, matricula, curso_codigo, conceito_id)
        ja_aprovado_ou_cursando = any(
            h.situacao in ESTADOS_APROVADO or h.situacao == "cursando" for h in historico_alvo
        )
        if ja_aprovado_ou_cursando:
            continue

        caminho_viavel = True
        prereqs_cursando_agora = []
        
        # 1. Checa obrigatórios (E)
        for pre_id in req_obrigatorios:
            hist_pre = _historico_do_aluno_no_conceito(db, matricula, curso_codigo, pre_id)
            passou = any(h.situacao in ESTADOS_APROVADO for h in hist_pre)
            cursando = any(_periodo_mesmo(h.periodo_letivo, periodo_atual) and h.situacao == "cursando" for h in hist_pre)
            
            if not (passou or cursando):
                caminho_viavel = False
                break
            if cursando:
                prereqs_cursando_agora.append(pre_id)
                
        if not caminho_viavel:
            continue
            
        # 2. Checa alternativos (OU)
        for grupo, pre_ids in req_alternativos.items():
            passou_em_algum = False
            cursando_algum = None
            
            for pre_id in pre_ids:
                hist_pre = _historico_do_aluno_no_conceito(db, matricula, curso_codigo, pre_id)
                if any(h.situacao in ESTADOS_APROVADO for h in hist_pre):
                    passou_em_algum = True
                    break
                if any(_periodo_mesmo(h.periodo_letivo, periodo_atual) and h.situacao == "cursando" for h in hist_pre):
                    cursando_algum = pre_id
            
            if not (passou_em_algum or cursando_algum is not None):
                caminho_viavel = False
                break
                
            if not passou_em_algum and cursando_algum is not None:
                prereqs_cursando_agora.append(cursando_algum)
                
        if not caminho_viavel:
            continue
            
        # Para ser Grupo C, o aluno precisa estar cursando PELO MENOS UM pré-requisito agora
        if prereqs_cursando_agora:
            probabilidade = 1.0
            for pre_id in prereqs_cursando_agora:
                probabilidade *= probabilidade_aprovacao_nivel1(db, pre_id)
                
            resultado.append(
                AlunoGrupoC(
                    matricula=matricula,
                    probabilidade_aprovacao=round(probabilidade, 4),
                )
            )
    return resultado


def demanda_estimada(db: Session, curso_codigo: str, conceito_id: str, periodo_atual: str) -> float:
    """RN08 — |Grupo A| + |Grupo B| + soma das probabilidades do Grupo C."""
    a = grupo_a(db, curso_codigo, conceito_id, periodo_atual)
    b = grupo_b(db, curso_codigo, conceito_id)
    c = grupo_c(db, curso_codigo, conceito_id, periodo_atual)
    return len(a) + len(b) + sum(aluno.probabilidade_aprovacao for aluno in c)
