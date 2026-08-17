# Requisitos Não-Funcionais

## Segurança e privacidade de dados

**RNF01.** Senhas de usuários do painel de gestão devem ser armazenadas
com hash (nunca em texto plano).

**RNF02.** Dados pessoais de alunos (histórico escolar) não devem ser
versionados no repositório de código em nenhuma hipótese — ver
`.gitignore` e `data/sample/` no README.

**RNF03.** O sistema deve manter um limite de tentativas de login ou
mecanismo equivalente contra força bruta na autenticação.

**RNF04.** Sessões de usuário devem expirar após 30 minutos de inatividade.

**RNF05.** O sistema deve registrar (log) acessos ao painel de gestão para
fins de auditoria — sem expor esse log a usuários sem permissão.

## Desempenho

**RNF06.** O cálculo dos Grupos A, B e C para uma disciplina candidata deve
retornar em menos de 5 segundos, para uso interativo no painel.

## Confiabilidade e qualidade de dados

**RNF07.** O processo de importação (ETL) não deve falhar silenciosamente:
linhas inconsistentes devem ser reportadas, não descartadas sem registro
(ver RF05).

## Usabilidade

**RNF08.** O painel de gestão deve ser utilizável por um perfil não
técnico (coordenação acadêmica), sem necessidade de conhecimento de SQL ou
de conceitos de banco de dados para interpretar o relatório.

## Manutenibilidade

**RNF09.** Decisões de modelagem e de regras de negócio devem ser
registradas como ADRs (`docs/04-arquitetura/decisoes/`), não apenas
discutidas informalmente — critério essencial dado que a equipe do projeto
muda ao longo do tempo (rotatividade de bolsistas).

## Portabilidade / escopo de dados

**RNF10.** O modelo de dados deve suportar múltiplos cursos e disciplinas
compartilhadas entre cursos com regras de pré-requisito distintas (ver
RN01 em Regras de Negócio) — não deve assumir 1 disciplina = 1 conjunto de
pré-requisitos.

**RNF11.** O modelo de dados deve tolerar disciplinas cujo código muda
entre versões de PPC, sem depender da versão de PPC do aluno para saber
qual código foi usado (ver RN06, RN06.1 em Regras de Negócio — confirmado
com dados reais que a `versão PPC` do aluno não prevê de forma confiável o
código usado).
