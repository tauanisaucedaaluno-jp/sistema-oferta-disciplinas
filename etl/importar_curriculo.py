"""
ETL de importação do CSV de currículo/matriz curricular (RF01).

Este arquivo é um ESQUELETO — as funções abaixo ainda não têm corpo porque
implementá-las corretamente exige olhar os CSVs reais primeiro (nomes
exatos de coluna, encoding, casos de borda). Ver `arquitetura/system-design.md`
Seção 5.1 para o contrato de dados hipotetizado, e a divisão de issues do
Epic 2 no guia de implementação para a ordem recomendada.

Pipeline completo (cada função = um passo, na ordem em que devem ser
chamadas por um `importar_tudo()` que vocês vão escrever):

1. ler_csv_curriculo(caminho)
   → abre o CSV com separador ';' e encoding 'latin-1' (confirmado na
     Seção 5.1), devolve um DataFrame do pandas.

2. deduplicar_versoes(df)
   → RN06/Seção 5.1: o CSV tem linhas repetidas por versão de PPC. Regra
     proposta (validar com a coordenadora antes de travar): manter
     `situacao = 'ATIVA'` e a versão mais recente por (cod_curso,
     cod_disciplina). CUIDADO: o ADR 0003 descobriu que a coluna relevante
     de status pode ser 'ATIVO'/'CORRENTE'/'INATIVO' na versão, não
     'situacao' — confirme contra o CSV real antes de implementar, os dois
     documentos do projeto não usam exatamente os mesmos nomes.

3. construir_conceitos(df_curriculo, df_historico)
   → RF04, RN06, ADR 0003: agrupa por (curso, nome_disciplina normalizado)
     + vínculos diretos no campo `equivalencias` (um salto só, sem
     transitividade — é o ponto central do ADR 0003). Cria uma linha em
     CONCEITO_DISCIPLINA para cada grupo e uma linha em CODIGO_DISCIPLINA
     para cada código bruto visto, apontando pro conceito.
   → Códigos que não conseguirem ser agrupados a nenhum conceito
     (nome_disciplina não reconhecido) NÃO são descartados: entram no
     relatório de exceções (RF05).

4. montar_vinculos_curriculares(df, conceitos)
   → cria VINCULO_CURRICULAR (periodo_sugerido) por (curso, conceito) —
     periodicidade_oferta é preenchida depois, pelo ETL de histórico
     (Seção 3 do system-design), porque não vem no PPC.

5. montar_pre_requisitos(df, conceitos)
   → RF01, ADR 0001: já vem pronto no CSV como "código-nome" por linha —
     não precisa reconstrução (confirmado na Seção 5.1). Resolve cada
     código citado para seu conceito_id; se não resolver, reporta exceção
     (pré-requisito referenciando disciplina inexistente — RF05).

6. relatorio_excecoes()
   → RF05, RNF07: junta tudo que caiu nos "casos não resolvidos" acima e
     devolve/imprime um relatório — nunca falhar silenciosamente.

Antes de escrever o corpo de qualquer função acima: abra o CSV real com
`pandas.read_csv(caminho, sep=';', encoding='latin-1')` e rode
`df.columns.tolist()` e `df.head()` para confirmar os nomes de coluna. A
Seção 5.1 do system-design avisa explicitamente que os nomes ali são
hipóteses a confirmar, não certeza.
"""
import pandas as pd


def ler_csv_curriculo(caminho: str) -> pd.DataFrame:
    raise NotImplementedError("Implementar após confirmar colunas reais do CSV.")


def deduplicar_versoes(df: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("Ver RN06 / ADR 0003 — validar regra de dedup com a coordenadora.")


def construir_conceitos(df_curriculo: pd.DataFrame, df_historico: pd.DataFrame):
    raise NotImplementedError("Ver RF04, RN06, ADR 0003.")


def montar_vinculos_curriculares(df: pd.DataFrame, conceitos):
    raise NotImplementedError("Ver Seção 6 do system-design.md.")


def montar_pre_requisitos(df: pd.DataFrame, conceitos):
    raise NotImplementedError("Ver ADR 0001, RN07 (equivalências — ver nota em core/groups.py).")
