import { useEffect, useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Detalhe from "./pages/Detalhe";
import "./App.css";

type Page = "login" | "dashboard" | "detalhe";

import ErrorBoundary from "./components/ErrorBoundary";

function App() {
  const [token, setToken] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<Page>("login");
  const [selectedConceitoId, setSelectedConceitoId] = useState<string | null>(null);
  const [curso, setCurso] = useState<string>("ALES");
  const [periodo, setPeriodo] = useState<string>("2026/1");
  const [modo, setModo] = useState<string>("regular");
  const [cursoCodigo, setCursoCodigo] = useState<string>("ALES");

  useEffect(() => {
    // Tenta carregar a sessão do localStorage
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
        <Login onLoginSuccess={handleLoginSuccess} />
      )}
      
      {currentPage === "dashboard" && token && (
        <Dashboard
          token={token}
          userEmail={getUserEmail()}
          curso={curso}
          setCurso={setCurso}
          periodo={periodo}
          setPeriodo={setPeriodo}
          modo={modo}
          setModo={setModo}
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
