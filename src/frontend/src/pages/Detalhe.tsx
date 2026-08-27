import { useEffect, useState } from "react";
import logoImg from "../assets/logo.png";

interface AlunoGrupoC {
  matricula: string;
  probabilidade: number;
}

interface DetalheDemanda {
  conceito_id: string;
  disciplina_nome: string;
  curso_codigo: string;
  curso_nome: string;
  periodo_sugerido: number | null;
  periodicidade_oferta: string | null;
  demanda_estimada: number;
  total_alunos: number;
  grupo_a: string[];
  grupo_b: string[];
  grupo_c: AlunoGrupoC[];
}

interface DetalheProps {
  token: string;
  cursoCodigo: string;
  conceitoId: string;
  periodo: string;
  onBack: () => void;
}

const API_BASE = "http://localhost:8000";

export default function Detalhe({ token, cursoCodigo, conceitoId, periodo, onBack }: DetalheProps) {
  const [detalhe, setDetalhe] = useState<DetalheDemanda | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"A" | "B" | "C">("A");

  useEffect(() => {
    const fetchDetalhe = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `${API_BASE}/demanda/detalhe?curso_codigo=${cursoCodigo}&conceito_id=${conceitoId}&periodo_atual=${periodo}`,
          {
            method: "GET",
            headers: {
              "Authorization": `Bearer ${token}`,
            },
          }
        );

        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || "Erro ao carregar o detalhamento da disciplina.");
        }

        const data = await response.json();
        setDetalhe(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erro de conexão com o servidor.");
      } finally {
        setLoading(false);
      }
    };

    fetchDetalhe();
  }, [cursoCodigo, conceitoId, periodo, token]);

  return (
    <div className="detalhe-container">
      <header className="dashboard-header">
        <div
          className="header-logo-group clickable-logo"
          onClick={onBack}
          title="Voltar para a tela principal"
        >
          <img src={logoImg} alt="OfertaPampa Logo" className="dashboard-logo" />
          <div className="header-titles">
            <h1>OfertaPampa</h1>
            <span className="badge-unipampa">UNIPAMPA</span>
          </div>
        </div>
        <div className="header-actions">
          <span className="period-label" style={{ marginRight: "0.5rem" }}>
            Período: {periodo}
          </span>
          <button onClick={onBack} className="btn btn-outline-danger btn-sm">
            &larr; Voltar ao Dashboard
          </button>
        </div>
      </header>

      {loading ? (
        <div className="detail-loading">Carregando detalhes da disciplina...</div>
      ) : error ? (
        <div className="detail-error">
          <strong>Erro:</strong> {error}
          <button onClick={onBack} className="btn btn-outline" style={{ marginTop: "1rem" }}>
            Voltar ao Dashboard
          </button>
        </div>
      ) : !detalhe ? (
        <div className="detail-empty">Nenhum dado retornado.</div>
      ) : (
        <main className="detalhe-content">
          <div className="detail-hero-card">
            <div className="detail-info">
              <div className="detail-badges-row">
                <span className="concept-id-badge">{detalhe.conceito_id}</span>
                <span className="course-badge">{detalhe.curso_nome} ({detalhe.curso_codigo})</span>
                {detalhe.periodo_sugerido && (
                  <span className="semester-badge">{detalhe.periodo_sugerido}º Semestre (Grade Ideal)</span>
                )}
                {detalhe.periodicidade_oferta && (
                  <span className="periodicity-badge">
                    Oferta: {detalhe.periodicidade_oferta === "ambos" ? "Semestral (Ambos)" : detalhe.periodicidade_oferta === "impar" ? "Semestres Ímpares" : "Semestres Pares"}
                  </span>
                )}
              </div>
              <h2>{detalhe.disciplina_nome}</h2>
              <p>Mapeamento detalhado de alunos elegíveis e estimativa matemática para o curso de {detalhe.curso_nome}</p>
            </div>
            <div className="detail-score">
              <span className="score-value">{detalhe.demanda_estimada}</span>
              <span className="score-label">Demanda Estimada</span>
              <span className="score-sublabel">{detalhe.total_alunos} alunos no total</span>
            </div>
          </div>

          <div className="summary-cards-row">
            <div className={`summary-card card-a ${activeTab === "A" ? "active" : ""}`} onClick={() => setActiveTab("A")}>
              <h4>Grupo A</h4>
              <span className="summary-number">{detalhe.grupo_a.length}</span>
              <p>Cursando agora</p>
            </div>
            <div className={`summary-card card-b ${activeTab === "B" ? "active" : ""}`} onClick={() => setActiveTab("B")}>
              <h4>Grupo B</h4>
              <span className="summary-number">{detalhe.grupo_b.length}</span>
              <p>Aptos (pré-req. OK)</p>
            </div>
            <div className={`summary-card card-c ${activeTab === "C" ? "active" : ""}`} onClick={() => setActiveTab("C")}>
              <h4>Grupo C</h4>
              <span className="summary-number">{detalhe.grupo_c.length}</span>
              <p>Potenciais (cursando pré-req.)</p>
            </div>
          </div>

          <div className="audit-list-card">
            <div className="card-header">
              <h3>
                {activeTab === "A" && "Grupo A — Alunos Atualmente Matriculados"}
                {activeTab === "B" && "Grupo B — Alunos Aptos não Matriculados"}
                {activeTab === "C" && "Grupo C — Alunos em Carga de Pré-requisitos"}
              </h3>
              <p>
                {activeTab === "A" && "Estudantes cursando a disciplina no período letivo analisado."}
                {activeTab === "B" && "Estudantes ativos que completaram os pré-requisitos e não cursaram a matéria ainda."}
                {activeTab === "C" && "Estudantes cursando pré-requisitos no momento, multiplicados pela probabilidade de aprovação."}
              </p>
            </div>

            <div className="list-content">
              {activeTab === "A" && (
                detalhe.grupo_a.length === 0 ? (
                  <p className="no-students">Nenhum aluno matriculado neste período.</p>
                ) : (
                  <ul className="student-list">
                    {detalhe.grupo_a.map((matricula) => (
                      <li key={matricula} className="student-item">
                        <span className="student-icon">👤</span>
                        <span className="student-matricula">Matrícula: <strong>{matricula}</strong></span>
                        <span className="student-status active">Matriculado (Peso 1.0)</span>
                      </li>
                    ))}
                  </ul>
                )
              )}

              {activeTab === "B" && (
                detalhe.grupo_b.length === 0 ? (
                  <p className="no-students">Nenhum aluno apto encontrado.</p>
                ) : (
                  <ul className="student-list">
                    {detalhe.grupo_b.map((matricula) => (
                      <li key={matricula} className="student-item">
                        <span className="student-icon">👤</span>
                        <span className="student-matricula">Matrícula: <strong>{matricula}</strong></span>
                        <span className="student-status eligible">Apto a cursar (Peso 1.0)</span>
                      </li>
                    ))}
                  </ul>
                )
              )}

              {activeTab === "C" && (
                detalhe.grupo_c.length === 0 ? (
                  <p className="no-students">Nenhum aluno cursando pré-requisitos atualmente.</p>
                ) : (
                  <ul className="student-list">
                    {detalhe.grupo_c.map((aluno) => (
                      <li key={aluno.matricula} className="student-item">
                        <span className="student-icon">👤</span>
                        <span className="student-matricula">Matrícula: <strong>{aluno.matricula}</strong></span>
                        <span className="student-probability">
                          Probabilidade de aprovação: <strong>{(aluno.probabilidade * 100).toFixed(1)}%</strong>
                        </span>
                      </li>
                    ))}
                  </ul>
                )
              )}
            </div>
          </div>
        </main>
      )}
    </div>
  );
}
