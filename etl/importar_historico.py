"""
ETL de importação dos CSVs de histórico escolar, um arquivo por curso
(RF02). Ver Seção 5.2 do system-design.md para o contrato de dados.

Passos (mesma lógica de importar_curriculo.py):

1. ler_historico(caminho)
   → aceita tanto .csv (separador ';', encoding 'latin-1') quanto .xlsx
     (confirmado: Engenharia Civil manda em xlsx, mesmas colunas — Seção
     5.2). Detectar pela extensão do arquivo.

2. normalizar_situacao(df)
   → RF03, RN04: mapeia a coluna `situação na disciplina` para o estado
     canônico (aprovado / reprovado / cursando / trancado / indefinido),
     usando a tabela de RN04. NUNCA perder o texto original — guardar em
     paralelo se for útil para auditoria/depuração.

3. excluir_evadidos(df)
   → RN05: remove (das análises de Grupo B/C — não do banco!) alunos com
     `situação da matrícula` em {Abandono, Cancelamento, Desligamento,
     Falecimento, Cancelamento Sisu e Guri}. `Aluno Regular` sempre fica.
     `Formado`, `Transferência voluntária`, `Reopção de Curso` — decidir
     caso a caso conforme a consulta (deixar parametrizável, não fixo).

4. inferir_periodicidade(df_historico)
   → RN03, Seção 3 do system-design: por (curso, conceito), olha em quais
     valores de `período` (1. Semestre / 2. Semestre) o conceito teve
     matrícula ao longo dos anos observados → 'impar' / 'par' / 'ambos'.
     Períodos de verão/inverno não entram nessa conta. Atualiza
     VINCULO_CURRICULAR.periodicidade_oferta.

5. gravar_historico(df, conceitos)
   → grava uma linha em HISTORICO por linha do CSV, com o
     `disciplina_codigo` BRUTO preservado (nunca resolvido para conceito
     aqui — RN06.1). Se o código não for resolvível a nenhum conceito
     conhecido, ainda assim GRAVA a linha (não descarta o histórico do
     aluno) e reporta a exceção separadamente (RF05).

Assim como no ETL de currículo: confirme os nomes reais de coluna abrindo
o CSV antes de implementar qualquer função abaixo.
"""
import pandas as pd


def ler_historico(caminho: str) -> pd.DataFrame:
    raise NotImplementedError("Implementar após confirmar colunas reais do CSV/XLSX.")


def normalizar_situacao(df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("Ver RF03, RN04.")


def excluir_evadidos(df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("Ver RN05.")


def inferir_periodicidade(df_historico: pd.DataFrame):
    raise NotImplementedError("Ver RN03, Seção 3 do system-design.md.")


def gravar_historico(df: pd.DataFrame, conceitos):
    raise NotImplementedError("Ver RN06.1 — nunca descartar/reescrever o código bruto.")
