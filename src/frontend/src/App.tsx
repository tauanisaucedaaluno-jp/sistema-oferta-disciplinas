import { useEffect, useState } from "react";
import logoImg from "./assets/logo.png";
import "./App.css";

/**
 * Componente principal do frontend para testar a comunicação com a API
 * e apresentar a tela de boas-vindas do sistema OfertaPampa.
 */
function App() {
  const [apiStatus, setApiStatus] = useState<"loading" | "connected" | "disconnected">("loading");
  const [errorDetails, setErrorDetails] = useState<string | null>(null);

  const checkConnection = async () => {
    setApiStatus("loading");
    setErrorDetails(null);
    try {
      const response = await fetch("http://localhost:8000/health");
      if (response.ok) {
        const data = await response.json();
        if (data.status === "ok") {
          setApiStatus("connected");
        } else {
          setApiStatus("disconnected");
          setErrorDetails("Resposta inesperada do servidor.");
        }
      } else {
        setApiStatus("disconnected");
        setErrorDetails(`Erro HTTP: ${response.status}`);
      }
    } catch (error) {
      setApiStatus("disconnected");
      setErrorDetails(error instanceof Error ? error.message : "Erro desconhecido ao tentar conectar.");
    }
  };

  useEffect(() => {
    checkConnection();
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="logo-container">
          <img src={logoImg} alt="OfertaPampa Logo" className="app-logo" />
        </div>
      </header>

      <main className="app-content">
        <div className="card">
          <h1>OfertaPampa</h1>
          <p className="subtitle">
            Sistema de Apoio à Decisão de Oferta de Disciplinas — UNIPAMPA
          </p>
          
          <div className="status-container">
            <span className="status-label">Status da API (Backend):</span>
            <div className={`status-badge ${apiStatus}`}>
              <span className="pulse-dot"></span>
              {apiStatus === "loading" && "Verificando..."}
              {apiStatus === "connected" && "Conectado"}
              {apiStatus === "disconnected" && "Desconectado"}
            </div>
          </div>

          {errorDetails && (
            <div className="error-box">
              <strong>Detalhes do Erro:</strong>
              <p>{errorDetails}</p>
            </div>
          )}

          <div className="button-group">
            <button type="button" onClick={checkConnection} className="btn btn-primary">
              Testar Conexão Novamente
            </button>
          </div>
        </div>

        <div className="info-section">
          <h2>Ambiente Pronto (Epic 0)</h2>
          <p>
            O frontend React (Vite + TypeScript) e o backend Python (FastAPI + PostgreSQL) estão
            configurados e prontos para o desenvolvimento das próximas funcionalidades de ETL e
            motor de regras.
          </p>
          <div className="issues-badge-list">
            <span className="issue-badge done">#1 Backend Python OK</span>
            <span className="issue-badge done">#2 Postgres Local OK</span>
            <span className="issue-badge done">#3 Alembic Migrations OK</span>
            <span className="issue-badge done">#4 Vite React Skeleton OK</span>
          </div>
        </div>
      </main>

      <footer className="app-footer">
        <p>© 2026 OfertaPampa — Universidade Federal do Pampa (UNIPAMPA)</p>
      </footer>
    </div>
  );
}

export default App;
