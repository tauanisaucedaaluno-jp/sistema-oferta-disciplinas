import { useEffect, useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Detalhe from "./pages/Detalhe";
import DefinirSenha from "./pages/DefinirSenha";
import "./App.css";

type Page = "login" | "definir-senha" | "dashboard" | "detalhe";

import ErrorBoundary from "./components/ErrorBoundary";

function App() {
  const [token, setToken] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<Page>("login");
  const [tokenAtivacao, setTokenAtivacao] = useState<string | null>(null);
  const [selectedConceitoId, setSelectedConceitoId] = useState<string | null>(null);
  const [curso, setCurso] = useState<string>("TODOS");
  const [periodo, setPeriodo] = useState<string>("");
  const [cursoCodigo, setCursoCodigo] = useState<string>("TODOS");
  const [demandas, setDemandas] = useState<any[]>([]);
  const [periodosList, setPeriodosList] = useState<any[]>([]);
  const [cursos, setCursos] = useState<any[]>([]);

  useEffect(() => {
    // 1. Verifica se há token de ativação/definição de senha na URL
    const params = new URLSearchParams(window.location.search);
    const tok = params.get("token");
    if (tok || window.location.pathname.includes("definir-senha")) {
      if (tok) setTokenAtivacao(tok);
      setCurrentPage("definir-senha");
      return;
    }

    // 2. Tenta carregar a sessão do localStorage
    const savedToken = localStorage.getItem("token");
    if (savedToken) {
      setToken(savedToken);
      setCurrentPage("dashboard");
    }
  }, []);

  const handleLoginSuccess = (newToken: string) => {
    localStorage.setItem("token", newToken);
    setToken(newToken);
    setCurrentPage("dashboard");
  };

  const handleLogout = () => {
    localStorage.removeItem("token");
    setToken(null);
    setCurrentPage("login");
    setSelectedConceitoId(null);
    setPeriodosList([]);
    setDemandas([]);
    setPeriodo("");
  };

  const handleSelectDisciplina = (conceitoId: string, itemCursoCodigo: string, itemPeriodo: string) => {
    setSelectedConceitoId(conceitoId);
    setCursoCodigo(itemCursoCodigo);
    setPeriodo(itemPeriodo);
    setCurrentPage("detalhe");
  };

  /** Decodifica o payload do JWT (sem validar assinatura — só para exibição) */
  const getUserEmail = (): string => {
    if (!token) return "";
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.sub || "";
    } catch {
      return "";
    }
  };

  return (
    <ErrorBoundary>
      {currentPage === "login" && (
        <Login
          onLoginSuccess={handleLoginSuccess}
        />
      )}

      {currentPage === "definir-senha" && (
        <DefinirSenha
          initialToken={tokenAtivacao}
          onLoginSuccess={handleLoginSuccess}
          onVoltarLogin={() => setCurrentPage("login")}
        />
      )}
      
      {currentPage === "dashboard" && token && (
        <Dashboard
          token={token}
          userEmail={getUserEmail()}
          curso={curso}
          setCurso={setCurso}
          periodo={periodo}
          setPeriodo={setPeriodo}
          demandas={demandas}
          setDemandas={setDemandas}
          periodosList={periodosList}
          setPeriodosList={setPeriodosList}
          cursos={cursos}
          setCursos={setCursos}
          onLogout={handleLogout}
          onSelectDisciplina={handleSelectDisciplina}
        />
      )}
      
      {currentPage === "detalhe" && token && selectedConceitoId && (
        <Detalhe
          token={token}
          cursoCodigo={cursoCodigo}
          conceitoId={selectedConceitoId}
          periodo={periodo}
          onBack={() => setCurrentPage("dashboard")}
        />
      )}
    </ErrorBoundary>
  );
}

export default App;
