"""
Modelos do banco de dados.

Este arquivo é a tradução literal do diagrama ER da Seção 6 de
`arquitetura/system-design.md` para tabelas reais. Se você não entendeu
o "porquê" de alguma tabela, leia a Seção 6 (e o ADR 0003) antes de mexer
aqui — cada campo abaixo existe por causa de um caso real de dados
observado nos CSVs (documentado nas Regras de Negócio, RN06 em diante).

Resumo do porquê o schema não é "óbvio":

- O código de uma disciplina MUDA ao longo do tempo (ex.: Cálculo I foi
  AL0001, depois AL0363, depois DAL2002). Por isso existe
  CONCEITO_DISCIPLINA: é a identidade estável, e CODIGO_DISCIPLINA guarda
  todo código bruto já visto, apontando para o conceito correspondente.
- Pré-requisito é por (curso, disciplina), nunca por disciplina isolada
  (ADR 0001) — porque a mesma disciplina pode ter pré-requisitos
  diferentes em cursos diferentes.
- HISTORICO nunca reescreve o código bruto do CSV. A "tradução" de código
  para conceito acontece em tempo de consulta (join com CODIGO_DISCIPLINA),
  não na importação (RN06.1) — assim nenhum dado é perdido.
"""
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    DateTime,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db.database import Base


class Curso(Base):
    """Um curso de graduação (ex.: Ciência da Computação, Engenharia Civil)."""

    __tablename__ = "curso"

    codigo = Column(String, primary_key=True)  # ex.: "ALCC"
    nome = Column(String, nullable=False)


class ConceitoDisciplina(Base):
    """
    A identidade ESTÁVEL de uma disciplina dentro de um curso, independente
    de qual código de PPC foi usado ao longo do tempo (ver ADR 0003).

    Ex.: o conceito "Cálculo I" em Ciência da Computação agrupa os códigos
    brutos AL0001, AL0363 e DAL2002 — todos com significado "a mesma
    disciplina", vistos em versões diferentes do PPC.

    Construído pelo ETL (não digitado manualmente) agrupando por
    (curso, nome_disciplina normalizado) — ver RN06 e o issue de ETL
    correspondente.
    """

    __tablename__ = "conceito_disciplina"

    id = Column(String, primary_key=True)  # gerado pelo ETL, ex.: hash ou slug
    curso_codigo = Column(String, ForeignKey("curso.codigo"), nullable=False)
    nome_normalizado = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("curso_codigo", "nome_normalizado", name="uq_conceito_curso_nome"),
    )


class CodigoDisciplina(Base):
    """
    Cada código BRUTO já visto nos CSVs (currículo ou histórico), por curso,
    apontando para o conceito ao qual pertence.

    Esta é a tabela "nova" introduzida pelo ADR 0003 para resolver o
    problema de código não ser identidade estável. Toda consulta de
    histórico de aluno passa por aqui (join) para saber "este código antigo
    corresponde a qual conceito hoje".
    """

    __tablename__ = "codigo_disciplina"

    codigo = Column(String, primary_key=True)
    curso_codigo = Column(String, ForeignKey("curso.codigo"), primary_key=True)
    conceito_id = Column(String, ForeignKey("conceito_disciplina.id"), nullable=False)
    versao_ppc_origem = Column(Integer, nullable=True)
    # Valores reais do currículo: 'ATIVO' / 'CORRENTE' / 'INATIVO' (ADR 0003)
    situacao_curriculo = Column(String, nullable=True)


class VinculoCurricular(Base):
    """
    A "definição vigente" de uma disciplina dentro de um curso: em que
    semestre ela normalmente é ofertada e em que período da grade ela
    sugere estar.

    IMPORTANTE (ADR 0003): para o MVP, esta linha reflete a versão de PPC
    marcada como CORRENTE. Alunos vinculados a versões ATIVO mais antigas
    podem, na prática, ter regras levemente diferentes — limitação
    conhecida e documentada, não um bug a "consertar" sem entender o
    contexto primeiro.
    """

    __tablename__ = "vinculo_curricular"

    curso_codigo = Column(String, ForeignKey("curso.codigo"), primary_key=True)
    conceito_id = Column(String, ForeignKey("conceito_disciplina.id"), primary_key=True)
    # 'impar' | 'par' | 'ambos' | None (sem histórico suficiente para inferir) — RN03
    periodicidade_oferta = Column(String, nullable=True)
    periodo_sugerido = Column(Integer, nullable=True)


class PreRequisito(Base):
    """
    Uma exigência de pré-requisito: para cursar `conceito_id` no
    `curso_codigo`, é preciso ter sido aprovado em
    `conceito_prerequisito_id` (ou em algum equivalente direto dele — RN07).

    Uma disciplina pode ter várias linhas aqui (vários pré-requisitos) —
    por isso é tabela separada de VINCULO_CURRICULAR, não uma coluna nela.
    """

    __tablename__ = "pre_requisito"

    id = Column(Integer, primary_key=True, autoincrement=True)
    curso_codigo = Column(String, nullable=False)
    conceito_id = Column(String, nullable=False)
    conceito_prerequisito_id = Column(String, ForeignKey("conceito_disciplina.id"), nullable=False)
    grupo_alternativo = Column(Integer, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["curso_codigo", "conceito_id"],
            ["vinculo_curricular.curso_codigo", "vinculo_curricular.conceito_id"],
        ),
    )


class Aluno(Base):
    """Um estudante. `matricula` é o identificador único vindo do sistema acadêmico."""

    __tablename__ = "aluno"

    matricula = Column(String, primary_key=True)
    curso_codigo = Column(String, ForeignKey("curso.codigo"), nullable=False)
    semestre_ingresso = Column(String, nullable=True)


class Historico(Base):
    """
    Uma linha do histórico escolar: um aluno cursou uma disciplina (código
    BRUTO, do jeito que veio no CSV) em um período letivo, com um resultado.

    `disciplina_codigo` NUNCA é sobrescrito nem "corrigido" para o conceito
    — o dado bruto é preservado tal como veio do CSV (RN06.1). Quando o
    motor de regras precisa saber "isso é o conceito X?", ele faz um JOIN
    com CodigoDisciplina em tempo de consulta — é a função
    `resolver_conceito()` em core/resolvers.py.
    """

    __tablename__ = "historico"

    id = Column(Integer, primary_key=True, autoincrement=True)
    aluno_matricula = Column(String, ForeignKey("aluno.matricula"), nullable=False)
    curso_codigo = Column(String, ForeignKey("curso.codigo"), nullable=False)
    disciplina_codigo = Column(String, nullable=False)
    periodo_letivo = Column(String, nullable=False)  # ex.: "2026/1"
    # Estado CANÔNICO já normalizado pelo ETL (RN04): aprovado / reprovado /
    # cursando / trancado / indefinido — nunca o texto bruto do CSV.
    situacao = Column(String, nullable=False)
    situacao_matricula = Column(String, nullable=True)  # RN05 — Aluno Regular, Abandono etc.


class Usuario(Base):
    """
    Login do painel de gestão (RF13). Esta tabela NÃO está no diagrama ER
    original do system-design.md — foi adicionada aqui porque autenticação
    é requisito funcional (RF13) e o schema documentado ainda não a cobria.

    Ação recomendada: registrar isso como atualização da Seção 6 do
    system-design.md (ou um ADR próprio), conforme RNF09 pede — ver
    Issue "Documentar tabela de usuários" na divisão de issues.
    """

    __tablename__ = "usuario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    # Hash da senha (passlib/bcrypt) — nunca texto plano (RNF01)
    senha_hash = Column(String, nullable=False)
    papel = Column(String, nullable=False, default="coordenador")  # RBAC simples
    ativo = Column(Boolean, default=True, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())


class LogAcesso(Base):
    """Auditoria de acesso ao painel (RNF05)."""

    __tablename__ = "log_acesso"

    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    acao = Column(String, nullable=False)  # ex.: "login", "login_falho", "consulta_demanda"
    detalhe = Column(String, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())


class PeriodoLetivo(Base):
    """
    Registro explícito de períodos letivos gerenciados pela coordenação (ex.: 2026/1, 2026/2).
    Permite criar novos semestres e gerenciar o ciclo de planejamento e exclusão.
    """

    __tablename__ = "periodo_letivo"

    codigo = Column(String, primary_key=True)  # ex.: "2026/1"
    ano = Column(Integer, nullable=False)
    semestre = Column(Integer, nullable=False)  # 1 ou 2
    descricao = Column(String, nullable=True)
    is_atual = Column(Boolean, default=False, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())

