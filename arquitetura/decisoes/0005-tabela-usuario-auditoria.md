# ADR 0005 — Inclusão de tabelas de Usuário e Logs de Auditoria

**Status:** Aceito
**Data:** 26/08/2026
**Relacionado a:** RF13 (Autenticação) e RNF05 (Auditoria de Acesso)

## Contexto

A especificação inicial e o diagrama de entidade-relacionamento (ER) do projeto cobriam as tabelas acadêmicas básicas (cursos, alunos, currículo, pré-requisitos, conceitos e histórico), mas não previam as tabelas necessárias para suportar a autenticação de usuários administradores (coordenadores) nem o registro de logs de auditoria administrativa.

Como o sistema lida com dados acadêmicos sensíveis dos alunos (como matrícula, curso e histórico), a conformidade com a LGPD e os requisitos não-funcionais de segurança e auditoria (RNF01, RNF03, RNF04 e RNF05) exigem que o painel seja protegido por credenciais e que todas as operações sejam devidamente auditadas.

## Decisão

Foram adicionadas duas novas entidades ao modelo físico do banco de dados e ao mapeamento SQLAlchemy:

1. **`USUARIO`**: Armazena as credenciais de acesso dos coordenadores acadêmicos e equipe técnica. A senha é armazenada utilizando hash criptográfico seguro (bcrypt via `passlib`), impedindo a exposição de senhas em texto plano. Possui controle de acesso baseado em papéis simples (RBAC).
2. **`LOG_ACESSO`**: Armazena logs de auditoria para fins de conformidade e segurança, registrando quem acessou o painel, a ação realizada (ex: "login", "consulta_demanda") e detalhes adicionais relevantes, com carimbo de data/hora gerado automaticamente pelo banco de dados.

Ambas as tabelas foram incluídas no esquema inicial de banco de dados (`src/backend/db/models.py`) e na migração inicial gerenciada pelo Alembic.

## Consequências

**Positivas:**
- Conformidade total com a LGPD e com os requisitos do projeto que exigem segurança no acesso (RF13, RNF01, RNF03, RNF04).
- Capacidade de auditoria retrospectiva e rastreamento de acessos administrativos caso ocorram incidentes de segurança (RNF05).
- Proteção de dados acadêmicos confidenciais contra acessos não autorizados.

**Negativas / custos:**
- Maior complexidade no setup de banco de dados e migrações iniciais.
- Necessidade de implementar rotinas e dependências de autenticação (JWT) e rotinas para inserção de registros de log nas rotas administrativas da API.
