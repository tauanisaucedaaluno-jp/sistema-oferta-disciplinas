-- Script de Seed SQL para o MVP (Dados Falsos)
-- Local: data/sample/seed.sql

-- 1. Limpeza das tabelas (Ordem reversa das dependências)
DELETE FROM log_acesso;
DELETE FROM usuario;
DELETE FROM historico;
DELETE FROM pre_requisito;
DELETE FROM vinculo_curricular;
DELETE FROM codigo_disciplina;
DELETE FROM conceito_disciplina;
DELETE FROM aluno;
DELETE FROM curso;

-- 2. Cursos
INSERT INTO curso (codigo, nome) VALUES 
('ES', 'Engenharia de Software'),
('CC', 'Ciência da Computação');

-- 3. Conceitos de Disciplina
INSERT INTO conceito_disciplina (id, curso_codigo, nome_normalizado) VALUES 
('C-CALC1', 'CC', 'CALCULO 1'),
('C-PROG1', 'CC', 'PROGRAMACAO 1'),
('ES-CALC1', 'ES', 'CALCULO 1');

-- 4. Códigos de Disciplina
INSERT INTO codigo_disciplina (codigo, curso_codigo, conceito_id, versao_ppc_origem, situacao_curriculo) VALUES 
('AL0001', 'CC', 'C-CALC1', 2014, 'INATIVO'),
('AL0363', 'CC', 'C-CALC1', 2020, 'CORRENTE'),
('AL0101', 'CC', 'C-PROG1', 2020, 'CORRENTE'),
('ES0001', 'ES', 'ES-CALC1', 2021, 'CORRENTE');

-- 5. Vínculos Curriculares
INSERT INTO vinculo_curricular (curso_codigo, conceito_id, periodicidade_oferta, periodo_sugerido) VALUES 
('CC', 'C-CALC1', 'impar', 1),
('CC', 'C-PROG1', 'impar', 1),
('ES', 'ES-CALC1', 'impar', 1);

-- 6. Pré-Requisitos
-- (Podemos adicionar dependências no futuro aqui)

-- 7. Alunos
INSERT INTO aluno (matricula, curso_codigo, semestre_ingresso) VALUES 
('2020001', 'CC', '2020/1'),
('2021002', 'CC', '2021/1'),
('2022003', 'ES', '2022/1');
('2022003', 'ES', '2022/1');

-- 8. Histórico Escolar
INSERT INTO historico (aluno_matricula, curso_codigo, disciplina_codigo, periodo_letivo, situacao, situacao_matricula) VALUES 
('2020001', 'CC', 'AL0001', '2020/1', 'reprovado', 'Aluno Regular'),
('2020001', 'CC', 'AL0363', '2021/1', 'aprovado', 'Aluno Regular'),
('2021002', 'CC', 'AL0363', '2026/1', 'cursando', 'Aluno Regular'),
('2022003', 'ES', 'ES0001', '2022/1', 'aprovado', 'Aluno Regular');

-- 9. Usuário (senha: admin123 hash via bcrypt)
INSERT INTO usuario (email, senha_hash, papel, ativo) VALUES 
('coordenador@unipampa.edu.br', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjIQqiRQYq', 'coordenador', true);
