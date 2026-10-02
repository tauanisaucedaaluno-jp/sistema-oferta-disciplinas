import React, { useEffect, useState } from "react";
import logoImg from "../assets/logo.png";

interface DemandaPorCurso {
  curso_codigo: string;
  disciplina_codigo?: string;
  grupo_a_qtd: number;
  grupo_a_prob?: number;
  grupo_b_qtd: number;
  grupo_c_qtd: number;
  grupo_c_prob: number;
  demanda_estimada: number;
  total_alunos: number;
}

interface DisciplinaDemand {
  conceito_id: string;
  disciplina_codigo?: string;
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

interface PeriodoInfo {
  codigo: string;
  ano: number;
  semestre: number;
  tipo: string;
  descricao?: string;
  total_registros: number;
  total_cursando: number;
  is_atual: boolean;
}

interface DashboardProps {
  token: string;
  userEmail: string;
  curso: string;
  setCurso: (curso: string) => void;
  periodo: string;
  setPeriodo: (periodo: string) => void;
  demandas: DisciplinaDemand[];
  setDemandas: React.Dispatch<React.SetStateAction<DisciplinaDemand[]>>;
  periodosList: PeriodoInfo[];
  setPeriodosList: React.Dispatch<React.SetStateAction<PeriodoInfo[]>>;
  cursos: CursoInfo[];
  setCursos: React.Dispatch<React.SetStateAction<CursoInfo[]>>;
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
  demandas,
  setDemandas,
  periodosList,
  setPeriodosList,
  cursos,
  setCursos,
  onLogout,
  onSelectDisciplina,
}: DashboardProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Controla quais linhas têm a quebra por curso expandida
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set());
  // Filtro por tipo de componente curricular (Todas, Obrigatórias, Optativas)
  const [tipoFiltro, setTipoFiltro] = useState<"todas" | "obrigatorias" | "optativas">("todas");
  const [bannerDismissed, setBannerDismissed] = useState(false);

  // Estados do Modal de Upload de Históricos / Currículo
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [selectedHistoricos, setSelectedHistoricos] = useState<FileList | null>(null);
  const [selectedCurriculo, setSelectedCurriculo] = useState<File | null>(null);

  // Estados de Gestão de Semestres (Criar e Excluir)
  const [showNovoSemestreModal, setShowNovoSemestreModal] = useState(false);
  const [showExcluirSemestreModal, setShowExcluirSemestreModal] = useState(false);
  const [novoAno, setNovoAno] = useState<string>("2026");
  const [novoSemestreNum, setNovoSemestreNum] = useState<string>("2");
  const [novoDescricao, setNovoDescricao] = useState<string>("");
  const [novoSemestreError, setNovoSemestreError] = useState<string | null>(null);
  const [novoSemestreLoading, setNovoSemestreLoading] = useState(false);
  const [excluirSemestreLoading, setExcluirSemestreLoading] = useState(false);
  const [excluirSemestreError, setExcluirSemestreError] = useState<string | null>(null);

  // Busca a lista de períodos dinamicamente
  const fetchPeriodos = async () => {
    try {
      const response = await fetch(`${API_BASE}/demanda/periodos`, {
        headers: { "Authorization": `Bearer ${token}` },
      });
      if (response.ok) {
        const data: PeriodoInfo[] = await response.json();
        setPeriodosList(data);
        // Se o período selecionado não existe na lista retornada, escolhe o atual
        if (data.length > 0 && !data.some(p => p.codigo === periodo)) {
          const atual = data.find(p => p.is_atual) || data[0];
          setPeriodo(atual.codigo);
        }
      }
    } catch {
      // Fallback silencioso
    }
  };

  // Busca cursos e períodos ao montar
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
    fetchPeriodos();
  }, [token]);


  const fetchDemandas = async () => {
    if (demandas.length === 0) {
      setLoading(true);
    }
    setError(null);
    setExpandidos(new Set());
    try {
      const response = await fetch(`${API_BASE}/demanda?curso_codigo=${curso}&periodo_atual=${periodo}&modo=regular`, {
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
  }, [curso, periodo]);

  const handleExport = async () => {
    try {
      const response = await fetch(`${API_BASE}/demanda/exportar?curso_codigo=${curso}&periodo_atual=${periodo}&modo=regular`, {
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
      a.download = `demandas_${curso}_${periodo.replace("/", "-")}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Erro desconhecido ao exportar.");
    }
  };

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedHistoricos || selectedHistoricos.length === 0) {
      setUploadError("Selecione pelo menos um arquivo CSV de histórico escolar.");
      return;
    }

    setUploadLoading(true);
    setUploadError(null);
    setUploadSuccess(null);

    const formData = new FormData();
    for (let i = 0; i < selectedHistoricos.length; i++) {
      formData.append("historicos", selectedHistoricos[i]);
    }
    if (selectedCurriculo) {
      formData.append("curriculo", selectedCurriculo);
    }

    try {
      const response = await fetch(`${API_BASE}/importacao/upload`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Erro ao importar dados acadêmicos.");
      }

      const resData = await response.json();
      setUploadSuccess(
        `✓ Sucesso! ${resData.total_linhas_historico.toLocaleString()} linhas e ${resData.total_alunos.toLocaleString()} alunos processados em ${resData.tempo_segundos}s.`
      );

      // Recarrega as estimativas e períodos da tela
      await fetchDemandas();
      await fetchPeriodos();

      setTimeout(() => {
        setShowUploadModal(false);
        setUploadSuccess(null);
        setSelectedHistoricos(null);
        setSelectedCurriculo(null);
      }, 3500);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Erro de conexão durante o upload.");
    } finally {
      setUploadLoading(false);
    }
  };

  const handleCriarSemestre = async (e: React.FormEvent) => {
    e.preventDefault();
    const codigo = `${novoAno}/${novoSemestreNum}`;
    setNovoSemestreLoading(true);
    setNovoSemestreError(null);

    try {
      const res = await fetch(`${API_BASE}/demanda/periodos`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          periodo: codigo,
          descricao: novoDescricao.trim() || `Semestre ${codigo}`,
          is_atual: false,
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Erro ao criar novo semestre.");
      }

      await fetchPeriodos();
      setPeriodo(codigo);
      setShowNovoSemestreModal(false);
      setNovoDescricao("");
    } catch (err) {
      setNovoSemestreError(err instanceof Error ? err.message : "Erro ao criar semestre.");
    } finally {
      setNovoSemestreLoading(false);
    }
  };

  const handleExcluirSemestre = async () => {
    setExcluirSemestreLoading(true);
    setExcluirSemestreError(null);

    try {
      const res = await fetch(`${API_BASE}/demanda/periodos/${periodo}`, {
        method: "DELETE",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Erro ao excluir semestre.");
      }

      await fetchPeriodos();
      setShowExcluirSemestreModal(false);
    } catch (err) {
      setExcluirSemestreError(err instanceof Error ? err.message : "Erro ao excluir semestre.");
    } finally {
      setExcluirSemestreLoading(false);
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

  const obrigatorias = demandas.filter(d => d.periodo_sugerido !== null);
  const optativas = demandas.filter(d => d.periodo_sugerido === null);

  const demandasExibidas = tipoFiltro === "obrigatorias"
    ? obrigatorias
    : tipoFiltro === "optativas"
    ? optativas
    : demandas;

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
          <button
            type="button"
            onClick={() => setShowUploadModal(true)}
            className="btn btn-secondary btn-sm"
            title="Importar novos arquivos de histórico escolar ou matriz curricular"
          >
            📥 Importar Dados
          </button>
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
              <div className="label-with-actions">
                <label htmlFor="select-periodo">Semestre de Análise</label>
                <div className="period-action-buttons">
                  <button
                    type="button"
                    className="btn-period-action btn-add-period"
                    title="Cadastrar Novo Semestre Oficial"
                    onClick={() => setShowNovoSemestreModal(true)}
                  >
                    ➕ Novo
                  </button>
                  <button
                    type="button"
                    className="btn-period-action btn-delete-period"
                    title={`Excluir Semestre ${periodo}`}
                    disabled={periodosList.length <= 1}
                    onClick={() => setShowExcluirSemestreModal(true)}
                  >
                    🗑️ Excluir
                  </button>
                </div>
              </div>
              <select
                id="select-periodo"
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
              >
                {periodosList.map((p) => (
                  <option key={p.codigo} value={p.codigo}>
                    {p.codigo} ({p.tipo === "impar" ? "1º Sem" : "2º Sem"}{p.is_atual ? " - Atual" : ""}{p.total_cursando > 0 ? ` • ${p.total_cursando} cursando` : ""})
                  </option>
                ))}
                {periodosList.length === 0 && (
                  <option value="2026/1">2026/1 (Semestre Regular Atual)</option>
                )}
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

        {/* Banner de carregamento ativo com animação */}
        {loading && (
          <div className="dashboard-loading-banner">
            <div className="loading-spinner-circle"></div>
            <div className="loading-text-group">
              <h4>Calculando estimativas de demanda...</h4>
              <p>Cruzando dados acadêmicos, pré-requisitos e históricos para o período <strong>{periodo}</strong>. Por favor, aguarde.</p>
            </div>
          </div>
        )}

        {/* Alerta explicativo apenas se o sistema inteiro estiver sem dados importados */}
        {(() => {
          if (loading || bannerDismissed) return null;
          const temDadosNoSistema = periodosList.some(p => p.total_registros > 0) || demandas.some(d => d.total_alunos > 0);
          if (temDadosNoSistema) return null;
          return (
            <div className="semester-empty-banner">
              <div className="semester-empty-banner-content">
                <span className="semester-empty-banner-icon">ℹ️</span>
                <div>
                  <strong>Nenhum histórico acadêmico carregado no sistema:</strong>
                  <p>
                    As disciplinas curriculares estão mapeadas com contagens zeradas. Para visualizar os alunos cursando, aptos e estimativas reais, faça o upload dos novos arquivos de histórico escolar (.csv).
                  </p>
                </div>
              </div>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <button
                  type="button"
                  className="btn btn-primary btn-sm semester-empty-banner-btn"
                  onClick={() => setShowUploadModal(true)}
                >
                  📥 Importar Histórico Agora
                </button>
                <button
                  type="button"
                  className="semester-empty-banner-close"
                  onClick={() => setBannerDismissed(true)}
                  title="Fechar aviso"
                >
                  ✕
                </button>
              </div>
            </div>
          );
        })()}

        <div className="table-card">
          <div className="table-header-group">
            <h3>Estimativas de Demanda</h3>
            <span className="results-count">
              {loading ? "Calculando..." : `${demandasExibidas.length} de ${demandas.length} disciplinas`}
            </span>
          </div>

          {/* Abas para filtrar entre Obrigatórias e Optativas */}
          <div className="filter-tabs">
            <button
              type="button"
              className={`filter-tab-btn ${tipoFiltro === "todas" ? "active" : ""}`}
              onClick={() => setTipoFiltro("todas")}
            >
              Todas as Disciplinas <span className="filter-tab-count">{demandas.length}</span>
            </button>
            <button
              type="button"
              className={`filter-tab-btn ${tipoFiltro === "obrigatorias" ? "active" : ""}`}
              onClick={() => setTipoFiltro("obrigatorias")}
            >
              Obrigatórias (Grade Regular) <span className="filter-tab-count">{obrigatorias.length}</span>
            </button>
            <button
              type="button"
              className={`filter-tab-btn ${tipoFiltro === "optativas" ? "active" : ""}`}
              onClick={() => setTipoFiltro("optativas")}
            >
              Optativas / Eletivas <span className="filter-tab-count">{optativas.length}</span>
            </button>
          </div>

          {tipoFiltro === "optativas" && (
            <div className="optativas-info-note">
              <span>💡</span>
              <div>
                <strong>Sobre as disciplinas optativas:</strong> Como não possuem turmas regulares obrigatórias na grade, os Grupos A (cursando) e C (cursando pré-requisito) são normalmente zero. A demanda total reflete os alunos do <strong>Grupo B (aptos)</strong> que já possuem os pré-requisitos necessários para cursá-las.
              </div>
            </div>
          )}

          {loading ? (
            <div className="table-loading-container">
              <div className="loading-spinner-circle"></div>
              <p className="loading-title">Calculando estimativas do período {periodo}...</p>
              <span className="loading-sub">Avaliando alunos nos Grupos A (cursando), B (aptos) e C (potenciais)</span>
            </div>
          ) : demandasExibidas.length === 0 ? (
            <div className="table-empty">Nenhuma disciplina encontrada para esta categoria de filtro.</div>
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
                    <th className="text-center">C (Cursando pré-req)</th>
                    <th className="text-center">Total Alunos</th>
                    <th className="text-right">Demanda Est.</th>
                    {curso === "TODOS" && <th className="text-center">Cursos</th>}
                  </tr>
                </thead>
                <tbody>
                  {demandasExibidas.map((item) => {
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
                          {curso !== "TODOS" && <td><strong>{item.disciplina_codigo || item.conceito_id}</strong></td>}
                          <td><strong>{item.disciplina_nome}</strong></td>
                          {curso !== "TODOS" && (
                            <td className="text-center">
                              {item.periodo_sugerido ? (
                                <span className="badge-semestre">{item.periodo_sugerido}º Sem</span>
                              ) : (
                                <span className="badge-optativa" title="Disciplina Optativa / Eletiva">Optativa</span>
                              )}
                            </td>
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

      {/* Modal de Importação de Dados Acadêmicos (Históricos e Currículo) */}
      {showUploadModal && (
        <div className="modal-overlay" onClick={() => !uploadLoading && setShowUploadModal(false)}>
          <div className="modal-card modal-card-lg" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>📁 Importação de Dados Acadêmicos</h3>
              <p className="modal-subtitle">
                Envie os arquivos de histórico escolar exportados do sistema acadêmico (Guri) para recalcular a oferta e a demanda de disciplinas.
              </p>
            </div>

            <form onSubmit={handleUpload}>
              <div className="modal-body">
                <div className="upload-section">
                  <label className="upload-label" htmlFor="upload-historicos">
                    <strong>1. Arquivos de Histórico Escolar (.csv) *</strong>
                    <span className="upload-hint">
                      Selecione um ou múltiplos arquivos CSV de histórico escolar (ex.: históricos dos cursos de Engenharia).
                    </span>
                  </label>
                  <input
                    id="upload-historicos"
                    type="file"
                    multiple
                    accept=".csv,.xlsx,.xls"
                    className="upload-input"
                    disabled={uploadLoading}
                    onChange={(e) => setSelectedHistoricos(e.target.files)}
                  />
                  {selectedHistoricos && selectedHistoricos.length > 0 && (
                    <div className="upload-file-count">
                      ✓ {selectedHistoricos.length} arquivo(s) selecionado(s) para importação
                    </div>
                  )}
                </div>

                <div className="upload-section mt-3">
                  <label className="upload-label" htmlFor="upload-curriculo">
                    <strong>2. Matriz Curricular / Currículo (.csv) (Opcional)</strong>
                    <span className="upload-hint">
                      Envie apenas se houver uma nova grade curricular (PPC) com alterações de disciplinas ou pré-requisitos. Caso contrário, o currículo padrão vigente será mantido.
                    </span>
                  </label>
                  <input
                    id="upload-curriculo"
                    type="file"
                    accept=".csv"
                    className="upload-input"
                    disabled={uploadLoading}
                    onChange={(e) => setSelectedCurriculo(e.target.files?.[0] || null)}
                  />
                  {selectedCurriculo && (
                    <div className="upload-file-count">
                      ✓ Matriz curricular selecionada: {selectedCurriculo.name}
                    </div>
                  )}
                </div>

                <div className="upload-benchmark-note">
                  <span className="note-icon">⏱️</span>
                  <span>
                    <strong>Desempenho:</strong> O processamento completo de mais de 200.000 registros ocorre em <strong>~45 segundos</strong> (muito abaixo do limite de 4 minutos).
                  </span>
                </div>

                {uploadError && (
                  <div className="modal-error-box mt-3">{uploadError}</div>
                )}

                {uploadSuccess && (
                  <div className="modal-success-box mt-3">{uploadSuccess}</div>
                )}
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setShowUploadModal(false)}
                  disabled={uploadLoading}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={uploadLoading || !selectedHistoricos || selectedHistoricos.length === 0}
                >
                  {uploadLoading ? (
                    <span className="upload-spinner-row">
                      <span className="spinner-inline"></span> Processando dados acadêmicos...
                    </span>
                  ) : (
                    "Iniciar Importação"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Criar Novo Semestre */}
      {showNovoSemestreModal && (
        <div className="modal-overlay" onClick={() => !novoSemestreLoading && setShowNovoSemestreModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>➕ Criar Novo Semestre</h3>
              <p className="modal-subtitle">
                Defina o ano e o período letivo oficial para habilitá-lo no planejamento e receber dados de matrícula.
              </p>
            </div>

            <form onSubmit={handleCriarSemestre}>
              <div className="modal-body">
                <div className="semester-inputs-row">
                  <div className="form-group flex-1">
                    <label htmlFor="input-novo-ano">Ano Letivo</label>
                    <input
                      id="input-novo-ano"
                      type="number"
                      min="2020"
                      max="2035"
                      className="form-control"
                      value={novoAno}
                      onChange={(e) => setNovoAno(e.target.value)}
                      required
                      disabled={novoSemestreLoading}
                    />
                  </div>
                  <div className="form-group flex-1">
                    <label htmlFor="select-novo-semestre">Semestre</label>
                    <select
                      id="select-novo-semestre"
                      className="form-control"
                      value={novoSemestreNum}
                      onChange={(e) => setNovoSemestreNum(e.target.value)}
                      disabled={novoSemestreLoading}
                    >
                      <option value="1">1º Semestre (Ímpar)</option>
                      <option value="2">2º Semestre (Par)</option>
                    </select>
                  </div>
                </div>

                <div className="form-group mt-3">
                  <label htmlFor="input-novo-desc">Descrição / Observação (opcional)</label>
                  <input
                    id="input-novo-desc"
                    type="text"
                    className="form-control"
                    placeholder="Ex.: Semestre Regular 2026/2"
                    value={novoDescricao}
                    onChange={(e) => setNovoDescricao(e.target.value)}
                    disabled={novoSemestreLoading}
                  />
                </div>

                <div className="semester-preview-badge mt-3">
                  Período a ser cadastrado: <strong>{novoAno}/{novoSemestreNum}</strong>
                </div>

                {novoSemestreError && (
                  <div className="modal-error-box mt-3">{novoSemestreError}</div>
                )}
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setShowNovoSemestreModal(false)}
                  disabled={novoSemestreLoading}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={novoSemestreLoading}
                >
                  {novoSemestreLoading ? "Cadastrando..." : "Cadastrar Semestre"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Excluir Semestre */}
      {showExcluirSemestreModal && (
        <div className="modal-overlay" onClick={() => !excluirSemestreLoading && setShowExcluirSemestreModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>🗑️ Excluir Semestre {periodo}</h3>
              <p className="modal-subtitle">
                Esta ação removerá permanentemente todos os registros de histórico e matrículas associados ao semestre <strong>{periodo}</strong>.
              </p>
            </div>

            <div className="modal-body">
              <div className="delete-warning-box">
                <span className="warning-icon">⚠️</span>
                <div>
                  <strong>Atenção!</strong> Esta operação é irreversível e deve ser usada caso você tenha subido dados de teste ou um arquivo incorreto.
                </div>
              </div>

              {excluirSemestreError && (
                <div className="modal-error-box mt-3">{excluirSemestreError}</div>
              )}
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setShowExcluirSemestreModal(false)}
                disabled={excluirSemestreLoading}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="btn btn-danger"
                onClick={handleExcluirSemestre}
                disabled={excluirSemestreLoading}
              >
                {excluirSemestreLoading ? "Excluindo..." : `Confirmar Exclusão de ${periodo}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


