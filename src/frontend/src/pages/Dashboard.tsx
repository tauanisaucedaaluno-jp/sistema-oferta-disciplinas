import React, { useEffect, useState } from "react";
import logoImg from "../assets/logo.png";

interface DemandaPorCurso {
  curso_codigo: string;
  grupo_a_qtd: number;
  grupo_b_qtd: number;
  grupo_c_qtd: number;
  grupo_c_prob: number;
  demanda_estimada: number;
  total_alunos: number;
}

interface DisciplinaDemand {
  conceito_id: string;
  disciplina_nome: string;
  periodo_sugerido: number | null;
  periodicidade_oferta: string | null;
  grupo_a_qtd: number;
  grupo_b_qtd: number;
  grupo_c_qtd: number;
  demanda_estimada: number;
  total_alunos: number;
  demanda_por_curso: DemandaPorCurso[];
}

interface CursoInfo {
  codigo: string;
  nome: string;
}

interface DashboardProps {
  token: string;
  userEmail: string;
  curso: string;
  setCurso: (curso: string) => void;
  periodo: string;
  setPeriodo: (periodo: string) => void;
  modo: string;
  setModo: (modo: string) => void;
  onLogout: () => void;
  onSelectDisciplina: (conceitoId: string, cursoCodigo: string, periodo: string) => void;
}

const API_BASE = "http://localhost:8000";

export default function Dashboard({
  token,
  userEmail,
  curso,
  setCurso,
  periodo,
  setPeriodo,
  modo,
  setModo,
  onLogout,
  onSelectDisciplina,
}: DashboardProps) {
  const [demandas, setDemandas] = useState<DisciplinaDemand[]>([]);
  const [cursos, setCursos] = useState<CursoInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Controla quais linhas têm a quebra por curso expandida
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set());

  // Busca a lista de cursos ao montar
  useEffect(() => {
    const fetchCursos = async () => {
      try {
        const response = await fetch(`${API_BASE}/demanda/cursos`, {
          headers: { "Authorization": `Bearer ${token}` },
        });
        if (response.ok) {
          const data = await response.json();
          setCursos(data);
        }
      } catch {
        // Fallback silencioso — o select ainda mostra "Todos os Cursos"
      }
    };
    fetchCursos();
  }, [token]);

  const fetchDemandas = async () => {
    setLoading(true);
    setError(null);
    setExpandidos(new Set());
    try {
      const response = await fetch(`${API_BASE}/demanda?curso_codigo=${curso}&periodo_atual=${periodo}&modo=${modo}`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          onLogout();
          return;
        }
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Erro ao carregar os dados de demanda.");
      }

      const data = await response.json();
      setDemandas(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao se conectar com o servidor.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDemandas();
  }, [curso, periodo, modo]);

  const handleExport = async () => {
    try {
      const response = await fetch(`${API_BASE}/demanda/exportar?curso_codigo=${curso}&periodo_atual=${periodo}&modo=${modo}`, {
        method: "GET",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Erro ao exportar arquivo CSV.");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `demandas_${curso}_${periodo.replace("/", "-")}_${modo}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro desconhecido ao exportar.");
    }
  };

  const toggleExpandido = (conceitoId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpandidos(prev => {
      const next = new Set(prev);
      if (next.has(conceitoId)) {
        next.delete(conceitoId);
      } else {
        next.add(conceitoId);
      }
      return next;
    });
  };

  // Quando curso = TODOS e a disciplina tem múltiplos cursos, o clique no detalhe
  // usa o curso_codigo do primeiro item de demanda_por_curso
  const handleRowClick = (item: DisciplinaDemand) => {
    const cursoCodigo = curso === "TODOS"
      ? (item.demanda_por_curso?.[0]?.curso_codigo ?? "CC")
      : curso;
    onSelectDisciplina(item.conceito_id, cursoCodigo, periodo);
  };

  // Monta o nome do curso a partir da lista carregada
  const nomeCurso = (codigo: string) => {
    const c = cursos.find(c => c.codigo === codigo);
    return c ? c.nome : codigo;
  };

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div
          className="header-logo-group clickable-logo"
          onClick={() => {
            setCurso("TODOS");
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
          title="Voltar para a tela principal (Todos os Cursos)"
        >
          <img src={logoImg} alt="OfertaPampa Logo" className="dashboard-logo" />
          <div className="header-titles">
            <h1>OfertaPampa</h1>
            <span className="badge-unipampa">UNIPAMPA</span>
          </div>
        </div>
        <div className="header-actions">
          <span className="user-email">{userEmail}</span>
          <button onClick={onLogout} className="btn btn-outline-danger btn-sm">
            Sair
          </button>
        </div>
      </header>

      <main className="dashboard-content">
        <div className="filter-card">
          <div className="filter-title">
            <h3>Filtros de Análise</h3>
            <p>Selecione as opções abaixo para recarregar as estimativas</p>
          </div>
          <div className="filters-row">
            <div className="form-group flex-1">
              <label htmlFor="select-curso">Curso de Graduação</label>
              <select
                id="select-curso"
                value={curso}
                onChange={(e) => setCurso(e.target.value)}
              >
                <option value="TODOS">Todos os Cursos</option>
                {cursos.map(c => (
                  <option key={c.codigo} value={c.codigo}>{c.nome} ({c.codigo})</option>
                ))}
                {/* Fallback caso a API de cursos falhe */}
                {cursos.length === 0 && (
                  <>
                    <option value="ALES">Engenharia de Software (ALES)</option>
                    <option value="ALEC">Engenharia Civil (ALEC)</option>
                    <option value="ALEE">Engenharia Elétrica (ALEE)</option>
                    <option value="ALEM">Engenharia Mecânica (ALEM)</option>
                    <option value="ALEA">Engenharia Agrícola (ALEA)</option>
                    <option value="ALET">Engenharia de Telecomunicações (ALET)</option>
                  </>
                )}
              </select>
            </div>

            <div className="form-group flex-1">
              <label htmlFor="select-periodo">Período Letivo Alvo</label>
              <select
                id="select-periodo"
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
              >
                <option value="2026/1">2026/1 (Ímpar - Atual)</option>
                <option value="2026/2">2026/2 (Par - Próximo)</option>
              </select>
            </div>

            <div className="form-group flex-1">
              <label htmlFor="select-modo">Modo de Análise</label>
              <select
                id="select-modo"
                value={modo}
                onChange={(e) => setModo(e.target.value)}
              >
                <option value="regular">Demanda no Semestre Regular</option>
                <option value="extraordinaria">Oferta Extraordinária</option>
              </select>
            </div>

            <div className="filter-actions flex-align-end">
              <button onClick={handleExport} className="btn btn-success" disabled={demandas.length === 0}>
                Exportar CSV
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="dashboard-error-box">
            <strong>Ocorreu um erro:</strong> {error}
          </div>
        )}

        <div className="table-card">
          <div className="table-header-group">
            <h3>Estimativas de Demanda</h3>
            <span className="results-count">{demandas.length} disciplinas mapeadas</span>
          </div>

          {loading ? (
            <div className="table-loading">Carregando estimativas de demanda...</div>
          ) : demandas.length === 0 ? (
            <div className="table-empty">Nenhum dado encontrado para os filtros selecionados.</div>
          ) : (
            <div className="table-responsive">
              <table className="custom-table">
                <thead>
                  <tr>
                    {curso !== "TODOS" && <th>Código</th>}
                    <th>Disciplina</th>
                    {curso !== "TODOS" && <th className="text-center">Semestre</th>}
                    <th className="text-center">A (Cursando)</th>
                    <th className="text-center">B (Aptos)</th>
                    <th className="text-center">C (Potencial)</th>
                    <th className="text-center">Total Alunos</th>
                    <th className="text-right">Demanda Est.</th>
                    {curso === "TODOS" && <th className="text-center">Cursos</th>}
                  </tr>
                </thead>
                <tbody>
                  {demandas.map((item) => {
                    const isCompartilhada = item.demanda_por_curso && item.demanda_por_curso.length > 1;
                    const isExpandida = expandidos.has(item.conceito_id);

                    return (
                      <React.Fragment key={item.conceito_id}>
                        <tr
                          onClick={(e) => {
                            if (curso === "TODOS" && isCompartilhada) {
                              toggleExpandido(item.conceito_id, e);
                            } else {
                              handleRowClick(item);
                            }
                          }}
                          className="clickable-row"
                          title={
                            curso === "TODOS" && isCompartilhada
                              ? "Clique para expandir/recolher os cursos desta disciplina"
                              : "Clique para auditar as matrículas desta disciplina"
                          }
                        >
                          {curso !== "TODOS" && <td><strong>{item.conceito_id}</strong></td>}
                          <td><strong>{item.disciplina_nome}</strong></td>
                          {curso !== "TODOS" && (
                            <td className="text-center">{item.periodo_sugerido ? `${item.periodo_sugerido}º` : "-"}</td>
                          )}
                          <td className="text-center"><span className="badge badge-a">{item.grupo_a_qtd}</span></td>
                          <td className="text-center"><span className="badge badge-b">{item.grupo_b_qtd}</span></td>
                          <td className="text-center"><span className="badge badge-c">{item.grupo_c_qtd}</span></td>
                          <td className="text-center"><span className="badge badge-total">{item.total_alunos}</span></td>
                          <td className="text-right highlight-demand"><strong>{item.demanda_estimada}</strong></td>
                          {curso === "TODOS" && (
                            <td className="text-center">
                              {isCompartilhada ? (
                                <button
                                  className="btn-expand-curso"
                                  onClick={(e) => toggleExpandido(item.conceito_id, e)}
                                  title={isExpandida ? "Recolher quebra por curso" : "Ver quebra por curso"}
                                >
                                  {item.demanda_por_curso.length} cursos {isExpandida ? "▲" : "▼"}
                                </button>
                              ) : (
                                <span className="curso-unico-label">
                                  {item.demanda_por_curso?.[0]?.curso_codigo ?? "-"}
                                </span>
                              )}
                            </td>
                          )}
                        </tr>

                        {/* Sub-linhas de quebra por curso (RF12) */}
                        {curso === "TODOS" && isCompartilhada && isExpandida && item.demanda_por_curso.map((dpc) => (
                          <tr
                            key={`${item.conceito_id}-${dpc.curso_codigo}`}
                            className="curso-breakdown-row clickable-row"
                            onClick={() => onSelectDisciplina(item.conceito_id, dpc.curso_codigo, periodo)}
                            title={`Clique para auditar detalhes dos alunos de ${nomeCurso(dpc.curso_codigo)}`}
                          >
                            <td className="curso-breakdown-indent">
                              <span className="curso-breakdown-nome">↳ {nomeCurso(dpc.curso_codigo)}</span>
                              <span className="curso-breakdown-codigo">{dpc.curso_codigo}</span>
                            </td>
                            <td className="text-center"><span className="badge badge-a badge-sm">{dpc.grupo_a_qtd}</span></td>
                            <td className="text-center"><span className="badge badge-b badge-sm">{dpc.grupo_b_qtd}</span></td>
                            <td className="text-center"><span className="badge badge-c badge-sm">{dpc.grupo_c_qtd}</span></td>
                            <td className="text-center"><span className="badge badge-total badge-sm">{dpc.total_alunos}</span></td>
                            <td className="text-right highlight-demand-sm">{dpc.demanda_estimada}</td>
                            <td className="text-center">
                              <span className="curso-audit-link">Ver detalhes &rarr;</span>
                            </td>
                          </tr>
                        ))}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      <footer className="dashboard-footer">
        <p>© 2026 OfertaPampa — Universidade Federal do Pampa (UNIPAMPA)</p>
      </footer>
    </div>
  );
}
