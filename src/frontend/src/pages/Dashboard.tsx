import React, { useEffect, useState } from "react";
import logoImg from "../assets/logo.png";

interface DisciplinaDemand {
  conceito_id: string;
  disciplina_nome: string;
  periodo_sugerido: number | null;
  periodicidade_oferta: string | null;
  grupo_a_qtd: number;
  grupo_b_qtd: number;
  grupo_c_qtd: number;
  demanda_estimada: number;
}

interface DashboardProps {
  token: string;
  onLogout: () => void;
  onSelectDisciplina: (conceitoId: string, periodo: string) => void;
}

export default function Dashboard({ token, onLogout, onSelectDisciplina }: DashboardProps) {
  const [demandas, setDemandas] = useState<DisciplinaDemand[]>([]);
  const [curso, setCurso] = useState("CC");
  const [periodo, setPeriodo] = useState("2024/1");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDemandas = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`http://localhost:8001/demanda?curso_codigo=${curso}&periodo_atual=${periodo}`, {
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
      const response = await fetch(`http://localhost:8001/demanda/exportar?curso_codigo=${curso}&periodo_atual=${periodo}`, {
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

  return (
    <div className="dashboard-container">
      <header className="dashboard-header">
        <div className="header-logo-group">
          <img src={logoImg} alt="OfertaPampa Logo" className="dashboard-logo" />
          <div className="header-titles">
            <h1>OfertaPampa</h1>
            <span className="badge-unipampa">UNIPAMPA</span>
          </div>
        </div>
        <div className="header-actions">
          <span className="user-email">coordenador@unipampa.edu.br</span>
          <button onClick={onLogout} className="btn btn-outline-danger btn-sm">
            Sair
          </button>
        </div>
      </header>

      <main className="dashboard-content">
        <div className="filter-card">
          <div className="filter-title">
            <h3>Filtros de Análise</h3>
            <p>Selecione as opções abaixo para recarregar as estimativas do motor de regras</p>
          </div>
          <div className="filters-row">
            <div className="form-group flex-1">
              <label htmlFor="select-curso">Curso de Graduação</label>
              <select
                id="select-curso"
                value={curso}
                onChange={(e) => setCurso(e.target.value)}
              >
                <option value="CC">Ciência da Computação (CC)</option>
                <option value="ES">Engenharia de Software (ES)</option>
              </select>
            </div>

            <div className="form-group flex-1">
              <label htmlFor="select-periodo">Período Letivo Alvo</label>
              <select
                id="select-periodo"
                value={periodo}
                onChange={(e) => setPeriodo(e.target.value)}
              >
                <option value="2024/1">2024/1 (Ímpar - Atual)</option>
                <option value="2024/2">2024/2 (Par - Próximo)</option>
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
                    <th>Código</th>
                    <th>Nome da Disciplina</th>
                    <th className="text-center">Período Sugerido</th>
                    <th className="text-center">Grupo A (Cursando)</th>
                    <th className="text-center">Grupo B (Aptos)</th>
                    <th className="text-center">Grupo C (Potenciais)</th>
                    <th className="text-right">Demanda Estimada</th>
                  </tr>
                </thead>
                <tbody>
                  {demandas.map((item) => (
                    <tr 
                      key={item.conceito_id} 
                      onClick={() => onSelectDisciplina(item.conceito_id, periodo)}
                      className="clickable-row"
                      title="Clique para auditar as matrículas deste conceito"
                    >
                      <td><strong>{item.conceito_id}</strong></td>
                      <td>{item.disciplina_nome}</td>
                      <td className="text-center">{item.periodo_sugerido ? `${item.periodo_sugerido}º` : "-"}</td>
                      <td className="text-center"><span className="badge badge-a">{item.grupo_a_qtd}</span></td>
                      <td className="text-center"><span className="badge badge-b">{item.grupo_b_qtd}</span></td>
                      <td className="text-center"><span className="badge badge-c">{item.grupo_c_qtd}</span></td>
                      <td className="text-right highlight-demand"><strong>{item.demanda_estimada}</strong></td>
                    </tr>
                  ))}
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
