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
from typing import List, Set
from dataclasses import dataclass
from collections import defaultdict
from functools import lru_cache

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
from typing import List, Set
from dataclasses import dataclass
from collections import defaultdict
from functools import lru_cache

from sqlalchemy.orm import Session
from sqlalchemy import func

from db.models import Historico, Aluno, PreRequisito, ConceitoDisciplina, CodigoDisciplina
from core.resolvers import resolver_conceito

ESTADOS_APROVADO = {"aprovado"}  # ver RN04 — já normalizado pelo ETL


def _obter_alunos_ativos_curso(db: Session, curso_codigo: str, context_cache: dict = None) -> Set[str]:
    """RN05 — Retorna conjunto de matrículas dos alunos ativos do curso (exclui evadidos)."""
    if context_cache is not None:
        if "ativos" not in context_cache:
            context_cache["ativos"] = {}
        if curso_codigo in context_cache["ativos"]:
            return context_cache["ativos"][curso_codigo]

    todos_alunos = set(r[0] for r in db.query(Aluno.matricula).filter(Aluno.curso_codigo == curso_codigo).all())
    evadidos = set(r[0] for r in db.query(Historico.aluno_matricula).filter(
        Historico.curso_codigo == curso_codigo,
        Historico.situacao_matricula.in_(["Abandono", "Cancelamento", "Desligamento", "Falecimento", "Cancelamento Sisu", "Guri"])
    ).distinct().all())
    res = todos_alunos - evadidos
    if context_cache is not None:
        context_cache["ativos"][curso_codigo] = res
    return res


def _aluno_esta_ativo(db: Session, matricula: str) -> bool:
    """RN05 — Retorna False se o aluno estiver evadido no seu período mais recente."""
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


def _formatos_periodo(periodo_atual: str) -> List[str]:
    """Gera variações aceitáveis do período letivo (ex.: '2026/1', '20261', '2026.1')."""
    p_clean = periodo_atual.replace("-", "").strip()
    sem_tipo = "1" if p_clean.endswith("1") or p_clean.endswith("01") else "2"
    ano = p_clean[:4]
    return [periodo_atual, f"{ano}/{sem_tipo}", f"{ano}.{sem_tipo}", f"{ano}{sem_tipo}"]


def _obter_nome_normalizado(db: Session, conceito_id: str, context_cache: dict = None) -> str:
    if context_cache is not None:
        if "conceitos" not in context_cache:
            context_cache["conceitos"] = {}
        if conceito_id in context_cache["conceitos"]:
            return context_cache["conceitos"][conceito_id]
    nome_alvo = db.query(ConceitoDisciplina.nome_normalizado).filter(ConceitoDisciplina.id == conceito_id).scalar()
    if context_cache is not None:
        context_cache["conceitos"][conceito_id] = nome_alvo
    return nome_alvo


def _obter_codigos_disciplina(db: Session, curso_codigo: str, nome_alvo: str, context_cache: dict = None) -> List[str]:
    if context_cache is not None:
        if "mapa_codigos" not in context_cache:
            cods = (
                db.query(CodigoDisciplina.curso_codigo, ConceitoDisciplina.nome_normalizado, CodigoDisciplina.codigo)
                .join(ConceitoDisciplina, CodigoDisciplina.conceito_id == ConceitoDisciplina.id)
                .all()
            )
            mapa = defaultdict(list)
            for c_cod, n_norm, d_cod in cods:
                mapa[(c_cod, n_norm)].append(d_cod)
            context_cache["mapa_codigos"] = mapa
        return context_cache["mapa_codigos"].get((curso_codigo, nome_alvo), [])
    else:
        query = (
            db.query(CodigoDisciplina.codigo)
            .join(ConceitoDisciplina, CodigoDisciplina.conceito_id == ConceitoDisciplina.id)
            .filter(CodigoDisciplina.curso_codigo == curso_codigo, ConceitoDisciplina.nome_normalizado == nome_alvo)
            .all()
        )
        return [r[0] for r in query]


def _obter_passaram_disciplina(db: Session, curso_codigo: str, pre_nome: str, context_cache: dict = None) -> Set[str]:
    key = (curso_codigo, pre_nome)
    if context_cache is not None:
        if "passaram" not in context_cache:
            context_cache["passaram"] = {}
        if key in context_cache["passaram"]:
            return context_cache["passaram"][key]

    cods = _obter_codigos_disciplina(db, curso_codigo, pre_nome, context_cache)
    if not cods:
        passaram = set()
    else:
        passaram = set(r[0] for r in db.query(Historico.aluno_matricula)
            .filter(
                Historico.curso_codigo == curso_codigo,
                Historico.disciplina_codigo.in_(cods),
                Historico.situacao == "aprovado"
            ).distinct().all())

    if context_cache is not None:
        context_cache["passaram"][key] = passaram
    return passaram


def _obter_inaptos_disciplina(db: Session, curso_codigo: str, nome_alvo: str, context_cache: dict = None) -> Set[str]:
    key = (curso_codigo, nome_alvo)
    if context_cache is not None:
        if "inaptos" not in context_cache:
            context_cache["inaptos"] = {}
        if key in context_cache["inaptos"]:
            return context_cache["inaptos"][key]

    cods = _obter_codigos_disciplina(db, curso_codigo, nome_alvo, context_cache)
    if not cods:
        inaptos = set()
    else:
        inaptos = set(r[0] for r in db.query(Historico.aluno_matricula)
            .filter(
                Historico.curso_codigo == curso_codigo,
                Historico.disciplina_codigo.in_(cods),
                Historico.situacao.in_(["aprovado", "cursando"])
            ).distinct().all())

    if context_cache is not None:
        context_cache["inaptos"][key] = inaptos
    return inaptos


_CACHE_PROB = {}

def probabilidade_aprovacao_nivel1(db: Session, conceito_id: str, context_cache: dict = None) -> float:
    """
    RN09 — Nível 1 (MVP): taxa histórica agregada de aprovação do conceito.
    Agrega por nome_normalizado com cache em memória.
    """
    nome_alvo = _obter_nome_normalizado(db, conceito_id, context_cache)
    if not nome_alvo:
        return 0.5

    if context_cache is not None:
        if "prob_aprov" not in context_cache:
            context_cache["prob_aprov"] = {}
        if nome_alvo in context_cache["prob_aprov"]:
            return context_cache["prob_aprov"][nome_alvo]
    elif nome_alvo in _CACHE_PROB:
        return _CACHE_PROB[nome_alvo]

    query = (
        db.query(Historico.situacao, func.count(Historico.id))
        .join(
            CodigoDisciplina,
            (Historico.curso_codigo == CodigoDisciplina.curso_codigo) &
            (Historico.disciplina_codigo == CodigoDisciplina.codigo)
        )
        .join(
            ConceitoDisciplina,
            CodigoDisciplina.conceito_id == ConceitoDisciplina.id
        )
        .filter(ConceitoDisciplina.nome_normalizado == nome_alvo)
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
    taxa = round(aprovados / total, 4) if total > 0 else 0.5
    if context_cache is not None:
        context_cache["prob_aprov"][nome_alvo] = taxa
    else:
        _CACHE_PROB[nome_alvo] = taxa
    return taxa


def probabilidade_reprovacao_nivel1(db: Session, conceito_id: str, context_cache: dict = None) -> float:
    """RN10 — Nível 1 (MVP): taxa histórica agregada de reprovação do conceito (1 - taxa_aprovacao)."""
    taxa_aprov = probabilidade_aprovacao_nivel1(db, conceito_id, context_cache)
    return round(1.0 - taxa_aprov, 4)


@dataclass
class AlunoGrupoA:
    matricula: str
    probabilidade_reprovacao: float


def grupo_a(db: Session, curso_codigo: str, conceito_id: str, periodo_atual: str, context_cache: dict = None) -> List[AlunoGrupoA]:
    """RF07 / RN10 — alunos cursando o conceito agora com probabilidade de reprovação estimada."""
    nome_alvo = _obter_nome_normalizado(db, conceito_id, context_cache)
    if not nome_alvo:
        return []

    formatos = _formatos_periodo(periodo_atual)
    alunos_ativos = _obter_alunos_ativos_curso(db, curso_codigo, context_cache)
    prob_rep = probabilidade_reprovacao_nivel1(db, conceito_id, context_cache)

    key = (curso_codigo, nome_alvo, tuple(formatos))
    if context_cache is not None:
        if "cursando_alvo" not in context_cache:
            context_cache["cursando_alvo"] = {}
        if key in context_cache["cursando_alvo"]:
            query_res = context_cache["cursando_alvo"][key]
            return [AlunoGrupoA(matricula=mat, probabilidade_reprovacao=prob_rep) for mat in sorted(query_res) if mat in alunos_ativos]

    cods = _obter_codigos_disciplina(db, curso_codigo, nome_alvo, context_cache)
    if not cods:
        res_mats = set()
    else:
        query = (
            db.query(Historico.aluno_matricula)
            .filter(
                Historico.curso_codigo == curso_codigo,
                Historico.disciplina_codigo.in_(cods),
                Historico.situacao == "cursando",
                Historico.periodo_letivo.in_(formatos)
            )
            .distinct()
            .all()
        )
        res_mats = set(r[0] for r in query)

    if context_cache is not None:
        context_cache["cursando_alvo"][key] = res_mats
    return [AlunoGrupoA(matricula=m, probabilidade_reprovacao=prob_rep) for m in sorted(res_mats) if m in alunos_ativos]


def grupo_b(db: Session, curso_codigo: str, conceito_id: str, context_cache: dict = None) -> List[str]:
    """
    RF08 — aptos e não matriculados: cumpriram TODOS os pré-requisitos
    (suportando cláusulas E/OU via grupo_alternativo) e não estão, atualmente,
    aprovados ou cursando o próprio conceito.
    """
    nome_alvo = _obter_nome_normalizado(db, conceito_id, context_cache)
    if not nome_alvo:
        return []

    alunos_ativos = _obter_alunos_ativos_curso(db, curso_codigo, context_cache)
    if not alunos_ativos:
        return []

    # Alunos que já cursaram ou estão cursando esta disciplina alvo (inaptos)
    alunos_inaptos = _obter_inaptos_disciplina(db, curso_codigo, nome_alvo, context_cache)

    candidatos = set(alunos_ativos) - alunos_inaptos
    if not candidatos:
        return []

    if context_cache is not None:
        if "prereqs" not in context_cache:
            context_cache["prereqs"] = {}
        if (curso_codigo, conceito_id) not in context_cache["prereqs"]:
            context_cache["prereqs"][(curso_codigo, conceito_id)] = (
                db.query(PreRequisito)
                .filter(
                    PreRequisito.curso_codigo == curso_codigo,
                    PreRequisito.conceito_id == conceito_id,
                )
                .all()
            )
        pre_requisitos = context_cache["prereqs"][(curso_codigo, conceito_id)]
    else:
        pre_requisitos = (
            db.query(PreRequisito)
            .filter(
                PreRequisito.curso_codigo == curso_codigo,
                PreRequisito.conceito_id == conceito_id,
            )
            .all()
        )

    req_obrigatorios = [p.conceito_prerequisito_id for p in pre_requisitos if p.grupo_alternativo is None]
    req_alternativos = defaultdict(list)
    for p in pre_requisitos:
        if p.grupo_alternativo is not None:
            req_alternativos[p.grupo_alternativo].append(p.conceito_prerequisito_id)

    # 1. Checa obrigatórios (E): aprovado em TODOS
    for pre_id in req_obrigatorios:
        pre_nome = _obter_nome_normalizado(db, pre_id, context_cache)
        if not pre_nome:
            continue
        passaram = _obter_passaram_disciplina(db, curso_codigo, pre_nome, context_cache)
        candidatos &= passaram
        if not candidatos:
            break

    # 2. Checa alternativos (OU): aprovado em pelo menos UM de cada grupo
    for grupo, pre_ids in req_alternativos.items():
        if not candidatos:
            break
        passaram_grupo = set()
        for pre_id in pre_ids:
            pre_nome = _obter_nome_normalizado(db, pre_id, context_cache)
            if not pre_nome:
                continue
            passaram = _obter_passaram_disciplina(db, curso_codigo, pre_nome, context_cache)
            passaram_grupo |= passaram
        candidatos &= passaram_grupo

    return sorted(list(candidatos))


@dataclass
class AlunoGrupoC:
    matricula: str
    probabilidade_aprovacao: float


def _obter_cursando_disciplina(db: Session, curso_codigo: str, pre_nome: str, formatos: List[str], context_cache: dict = None) -> Set[str]:
    key = (curso_codigo, pre_nome, tuple(formatos))
    if context_cache is not None:
        if "cursando_pre" not in context_cache:
            context_cache["cursando_pre"] = {}
        if key in context_cache["cursando_pre"]:
            return context_cache["cursando_pre"][key]

    cods = _obter_codigos_disciplina(db, curso_codigo, pre_nome, context_cache)
    if not cods:
        cursando = set()
    else:
        cursando = set(r[0] for r in db.query(Historico.aluno_matricula)
            .filter(
                Historico.curso_codigo == curso_codigo,
                Historico.disciplina_codigo.in_(cods),
                Historico.situacao == "cursando",
                Historico.periodo_letivo.in_(formatos)
            ).distinct().all())

    if context_cache is not None:
        context_cache["cursando_pre"][key] = cursando
    return cursando


def grupo_c(db: Session, curso_codigo: str, conceito_id: str, periodo_atual: str, context_cache: dict = None) -> List[AlunoGrupoC]:
    """RF09 — cursando algum pré-requisito agora, com probabilidade estimada."""
    nome_alvo = _obter_nome_normalizado(db, conceito_id, context_cache)
    if not nome_alvo:
        return []

    if context_cache is not None:
        if "prereqs" not in context_cache:
            context_cache["prereqs"] = {}
        if (curso_codigo, conceito_id) not in context_cache["prereqs"]:
            context_cache["prereqs"][(curso_codigo, conceito_id)] = (
                db.query(PreRequisito)
                .filter(
                    PreRequisito.curso_codigo == curso_codigo,
                    PreRequisito.conceito_id == conceito_id,
                )
                .all()
            )
        pre_requisitos = context_cache["prereqs"][(curso_codigo, conceito_id)]
    else:
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

    alunos_ativos = _obter_alunos_ativos_curso(db, curso_codigo, context_cache)
    if not alunos_ativos:
        return []

    # Inaptos: já aprovados ou cursando a disciplina alvo
    alunos_inaptos = _obter_inaptos_disciplina(db, curso_codigo, nome_alvo, context_cache)

    candidatos = set(alunos_ativos) - alunos_inaptos
    if not candidatos:
        return []

    formatos = _formatos_periodo(periodo_atual)

    req_obrigatorios = [p.conceito_prerequisito_id for p in pre_requisitos if p.grupo_alternativo is None]
    req_alternativos = defaultdict(list)
    for p in pre_requisitos:
        if p.grupo_alternativo is not None:
            req_alternativos[p.grupo_alternativo].append(p.conceito_prerequisito_id)

    aluno_cursando_pre = defaultdict(list)

    for pre_id in req_obrigatorios:
        pre_nome = _obter_nome_normalizado(db, pre_id, context_cache)
        if not pre_nome:
            continue

        passaram = _obter_passaram_disciplina(db, curso_codigo, pre_nome, context_cache)
        cursando = _obter_cursando_disciplina(db, curso_codigo, pre_nome, formatos, context_cache)

        candidatos &= (passaram | cursando)
        for mat in cursando & candidatos:
            aluno_cursando_pre[mat].append(pre_id)

    for grupo, pre_ids in req_alternativos.items():
        if not candidatos:
            break
        passaram_grupo = set()
        cursando_grupo = set()
        for pre_id in pre_ids:
            pre_nome = _obter_nome_normalizado(db, pre_id, context_cache)
            if not pre_nome:
                continue
            passaram = _obter_passaram_disciplina(db, curso_codigo, pre_nome, context_cache)
            cursando = _obter_cursando_disciplina(db, curso_codigo, pre_nome, formatos, context_cache)
            passaram_grupo |= passaram
            cursando_grupo |= cursando
            for mat in cursando & candidatos:
                aluno_cursando_pre[mat].append(pre_id)

        candidatos &= (passaram_grupo | cursando_grupo)

    resultado = []
    for mat in sorted(candidatos):
        pres = aluno_cursando_pre.get(mat, [])
        if pres:
            prob = 1.0
            for pid in pres:
                prob *= probabilidade_aprovacao_nivel1(db, pid, context_cache)
            resultado.append(AlunoGrupoC(matricula=mat, probabilidade_aprovacao=round(prob, 4)))

    return resultado


def demanda_estimada(db: Session, curso_codigo: str, conceito_id: str, periodo_atual: str, context_cache: dict = None) -> float:
    """RN08 — soma das probabilidades de reprovação do Grupo A + |Grupo B| + soma das probabilidades do Grupo C."""
    a = grupo_a(db, curso_codigo, conceito_id, periodo_atual, context_cache)
    b = grupo_b(db, curso_codigo, conceito_id, context_cache)
    c = grupo_c(db, curso_codigo, conceito_id, periodo_atual, context_cache)
    prob_a = sum(aluno.probabilidade_reprovacao for aluno in a)
    prob_c = sum(aluno.probabilidade_aprovacao for aluno in c)
    return prob_a + len(b) + prob_c
