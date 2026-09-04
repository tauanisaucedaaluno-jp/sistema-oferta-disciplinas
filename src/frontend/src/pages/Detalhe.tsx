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

function getMatricula(item: any): string {
  if (item === null || item === undefined) return "Desconhecido";
  if (typeof item === "string" || typeof item === "number") return String(item);
  if (typeof item === "object") {
    return item.matricula || item.aluno_matricula || item.id || String(item);
  }
  return String(item);
}

function getProbabilidade(item: any): number {
  if (!item || typeof item !== "object") return 0.5;
  const p = item.probabilidade ?? item.probabilidade_aprovacao ?? item.prob;
  return typeof p === "number" && !isNaN(p) ? p : 0.5;
}

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

  const listA = Array.isArray(detalhe?.grupo_a) ? detalhe!.grupo_a : [];
  const listB = Array.isArray(detalhe?.grupo_b) ? detalhe!.grupo_b : [];
  const listC = Array.isArray(detalhe?.grupo_c) ? detalhe!.grupo_c : [];

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
              <span className="summary-number">{listA.length}</span>
              <p>Cursando agora</p>
            </div>
            <div className={`summary-card card-b ${activeTab === "B" ? "active" : ""}`} onClick={() => setActiveTab("B")}>
              <h4>Grupo B</h4>
              <span className="summary-number">{listB.length}</span>
              <p>Aptos (pré-req. OK)</p>
            </div>
            <div className={`summary-card card-c ${activeTab === "C" ? "active" : ""}`} onClick={() => setActiveTab("C")}>
              <h4>Grupo C</h4>
              <span className="summary-number">{listC.length}</span>
              <p>Potenciais (cursando pré-req.)</p>
            </div>
          </div>

          <div key={activeTab} className="audit-list-card">
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

            <div key={`content-${activeTab}`} className="list-content">
              {activeTab === "A" && (
                listA.length === 0 ? (
                  <p key="no-students-a" className="no-students">Nenhum aluno matriculado neste período.</p>
                ) : (
                  <ul key="list-students-a" className="student-list">
                    {listA.map((item, idx) => {
                      const mat = getMatricula(item);
                      return (
                        <li key={`student-a-${mat}-${idx}`} className="student-item">
                          <span className="student-icon">👤</span>
                          <span className="student-matricula">Matrícula: <strong>{mat}</strong></span>
                          <span className="student-status active">Matriculado (Peso 1.0)</span>
                        </li>
                      );
                    })}
                  </ul>
                )
              )}

              {activeTab === "B" && (
                listB.length === 0 ? (
                  <p key="no-students-b" className="no-students">Nenhum aluno apto encontrado.</p>
                ) : (
                  <ul key="list-students-b" className="student-list">
                    {listB.map((item, idx) => {
                      const mat = getMatricula(item);
                      return (
                        <li key={`student-b-${mat}-${idx}`} className="student-item">
                          <span className="student-icon">👤</span>
                          <span className="student-matricula">Matrícula: <strong>{mat}</strong></span>
                          <span className="student-status eligible">Apto a cursar (Peso 1.0)</span>
                        </li>
                      );
                    })}
                  </ul>
                )
              )}

              {activeTab === "C" && (
                listC.length === 0 ? (
                  <p key="no-students-c" className="no-students">Nenhum aluno cursando pré-requisitos atualmente.</p>
                ) : (
                  <ul key="list-students-c" className="student-list">
                    {listC.map((item, idx) => {
                      const mat = getMatricula(item);
                      const prob = getProbabilidade(item);
                      return (
                        <li key={`student-c-${mat}-${idx}`} className="student-item">
                          <span className="student-icon">👤</span>
                          <span className="student-matricula">Matrícula: <strong>{mat}</strong></span>
                          <span className="student-probability">
                            Probabilidade de aprovação: <strong>{(prob * 100).toFixed(1)}%</strong>
                          </span>
                        </li>
                      );
                    })}
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
