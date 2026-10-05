import { useEffect, useState } from "react";
import logoImg from "../assets/logo.png";
import { API_BASE } from "../apiConfig";

interface AlunoComProbabilidade {
  matricula: string;
  probabilidade: number;
  probabilidade_reprovacao?: number;
  probabilidade_aprovacao?: number;
}

interface DetalheDemanda {
  conceito_id: string;
  disciplina_codigo?: string;
  disciplina_nome: string;
  curso_codigo: string;
  curso_nome: string;
  periodo_sugerido: number | null;
  periodicidade_oferta: string | null;
  demanda_estimada: number;
  total_alunos: number;
  grupo_a: (string | AlunoComProbabilidade)[];
  grupo_b: string[];
  grupo_c: (string | AlunoComProbabilidade)[];
}

interface DetalheProps {
  token: string;
  cursoCodigo: string;
  conceitoId: string;
  periodo: string;
  onBack: () => void;
}

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
  const p = item.probabilidade ?? item.probabilidade_reprovacao ?? item.probabilidade_aprovacao ?? item.prob;
  return typeof p === "number" && !isNaN(p) ? p : 0.5;
}

export default function Detalhe({ token, cursoCodigo, conceitoId, periodo, onBack }: DetalheProps) {
  const [detalhe, setDetalhe] = useState<DetalheDemanda | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"A" | "B" | "C">("A");

  // Estados para modal de remoção de matrícula
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [matriculaToDelete, setMatriculaToDelete] = useState<string | null>(null);
  const [justificativa, setJustificativa] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

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

  useEffect(() => {
    fetchDetalhe();
  }, [cursoCodigo, conceitoId, periodo, token]);

  useEffect(() => {
    if (detalhe) {
      const aCount = Array.isArray(detalhe.grupo_a) ? detalhe.grupo_a.length : 0;
      const bCount = Array.isArray(detalhe.grupo_b) ? detalhe.grupo_b.length : 0;
      if (aCount === 0 && bCount > 0) {
        setActiveTab("B");
      }
    }
  }, [detalhe]);

  const handleOpenDeleteModal = (matricula: string) => {
    setMatriculaToDelete(matricula);
    setJustificativa("");
    setDeleteError(null);
    setShowDeleteModal(true);
  };

  const handleConfirmDelete = async () => {
    if (!matriculaToDelete) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      const response = await fetch(`${API_BASE}/demanda/remover-matricula`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          matricula: matriculaToDelete,
          curso_codigo: cursoCodigo,
          conceito_id: conceitoId,
          periodo_atual: periodo,
          justificativa: justificativa.trim(),
        }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Erro ao remover matrícula.");
      }

      const matRemovida = matriculaToDelete;
      setShowDeleteModal(false);
      setMatriculaToDelete(null);
      setJustificativa("");
      setToastMessage(`Matrícula ${matRemovida} removida com sucesso!`);
      setTimeout(() => setToastMessage(null), 4000);

      // Atualiza a visualização com os dados recalculados
      await fetchDetalhe();
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "Erro ao remover matrícula.");
    } finally {
      setIsDeleting(false);
    }
  };

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
                <span className="concept-id-badge">{detalhe.disciplina_codigo || detalhe.conceito_id}</span>
                <span className="course-badge">{detalhe.curso_nome} ({detalhe.curso_codigo})</span>
                {detalhe.periodo_sugerido ? (
                  <span className="semester-badge">{detalhe.periodo_sugerido}º Semestre (Grade Ideal)</span>
                ) : (
                  <span className="semester-badge" style={{ backgroundColor: "#f3e8ff", color: "#7e22ce", borderColor: "#d8b4fe" }}>Componente Optativo / Eletivo</span>
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
                {activeTab === "A" && "Grupo A — Alunos Cursando a Disciplina"}
                {activeTab === "B" && "Grupo B — Alunos Aptos não Matriculados"}
                {activeTab === "C" && "Grupo C — Alunos em Carga de Pré-requisitos"}
              </h3>
              <p>
                {activeTab === "A" && "Estudantes cursando a disciplina no período letivo analisado, ponderados pela probabilidade histórica de reprovação (quem reprovar demandará a matéria novamente)."}
                {activeTab === "B" && "Estudantes ativos que completaram os pré-requisitos e não cursaram a matéria ainda."}
                {activeTab === "C" && "Estudantes cursando pré-requisitos no momento, ponderados pela probabilidade histórica de aprovação."}
              </p>
            </div>

            <div key={`content-${activeTab}`} className="list-content">
              {activeTab === "A" && (
                listA.length === 0 ? (
                  <p key="no-students-a" className="no-students">Nenhum aluno matriculado cursando esta disciplina no período de referência (comum em optativas ou semestres alternados).</p>
                ) : (
                  <ul key="list-students-a" className="student-list">
                    {listA.map((item, idx) => {
                      const mat = getMatricula(item);
                      const prob = getProbabilidade(item);
                      return (
                        <li key={`student-a-${mat}-${idx}`} className="student-item">
                          <div className="student-item-main">
                            <span className="student-icon">👤</span>
                            <span className="student-matricula">Matrícula: <strong>{mat}</strong></span>
                            <span className="student-probability">
                              Probabilidade de reprovação: <strong>{(prob * 100).toFixed(1)}%</strong>
                            </span>
                          </div>
                          <button
                            type="button"
                            className="btn-delete-student"
                            title={`Remover matrícula ${mat} (desistência / trancamento)`}
                            onClick={() => handleOpenDeleteModal(mat)}
                          >
                            🗑️
                          </button>
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
                          <div className="student-item-main">
                            <span className="student-icon">👤</span>
                            <span className="student-matricula">Matrícula: <strong>{mat}</strong></span>
                            <span className="student-status eligible">Apto a cursar (Peso 1.0)</span>
                          </div>
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
                          <div className="student-item-main">
                            <span className="student-icon">👤</span>
                            <span className="student-matricula">Matrícula: <strong>{mat}</strong></span>
                            <span className="student-probability">
                              Probabilidade de aprovação: <strong>{(prob * 100).toFixed(1)}%</strong>
                            </span>
                          </div>
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

      {/* Toast de notificação de sucesso */}
      {toastMessage && (
        <div className="toast-notification">
          <span>✓</span>
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Modal Popup de Confirmação de Remoção de Matrícula */}
      {showDeleteModal && (
        <div className="modal-overlay" onClick={() => !isDeleting && setShowDeleteModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>🗑️ Remover Matrícula do Grupo A</h3>
              <p className="modal-subtitle">
                Esta ação registrará a desistência ou trancamento do aluno no período analisado, recalculando a demanda da disciplina.
              </p>
            </div>

            <div className="modal-body">
              <div className="modal-info-box">
                <div className="modal-info-row"><strong>Matrícula:</strong> {matriculaToDelete}</div>
                <div className="modal-info-row">
                  <strong>Disciplina:</strong> {detalhe?.disciplina_nome} ({detalhe?.disciplina_codigo || detalhe?.conceito_id})
                </div>
                <div className="modal-info-row">
                  <strong>Curso:</strong> {detalhe?.curso_nome} ({detalhe?.curso_codigo})
                </div>
                <div className="modal-info-row"><strong>Período Letivo:</strong> {periodo}</div>
              </div>

              <label htmlFor="modal-justificativa" className="modal-label">
                Justificativa da Coordenação (opcional):
              </label>
              <textarea
                id="modal-justificativa"
                className="modal-textarea"
                placeholder="Ex.: Aluno informou desistência da disciplina ou trancamento de matrícula à coordenação..."
                value={justificativa}
                onChange={(e) => setJustificativa(e.target.value)}
                disabled={isDeleting}
              />

              {deleteError && (
                <div className="modal-error-box">{deleteError}</div>
              )}
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setShowDeleteModal(false)}
                disabled={isDeleting}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? "Salvando..." : "Salvar / Confirmar Remoção"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
