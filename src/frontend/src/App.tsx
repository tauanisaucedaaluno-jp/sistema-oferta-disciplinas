import { useEffect, useState } from "react";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Detalhe from "./pages/Detalhe";
import "./App.css";

type Page = "login" | "dashboard" | "detalhe";

function App() {
  const [token, setToken] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<Page>("login");
  const [selectedConceitoId, setSelectedConceitoId] = useState<string | null>(null);
  const [selectedPeriodo, setSelectedPeriodo] = useState<string>("2024/1");
  const [cursoCodigo, setCursoCodigo] = useState<string>("CC");

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

  const handleSelectDisciplina = (conceitoId: string, periodo: string) => {
    setSelectedConceitoId(conceitoId);
    setSelectedPeriodo(periodo);
    // Extrai o código do curso a partir do prefixo do conceito (ex: "CC-CALC1" -> "CC")
    const parts = conceitoId.split("-");
    if (parts.length > 0) {
      setCursoCodigo(parts[0]);
    } else {
      setCursoCodigo("CC");
    }
    setCurrentPage("detalhe");
  };

  return (
    <>
      {currentPage === "login" && (
        <Login onLoginSuccess={handleLoginSuccess} />
      )}
      
      {currentPage === "dashboard" && token && (
        <Dashboard
          token={token}
          onLogout={handleLogout}
          onSelectDisciplina={handleSelectDisciplina}
        />
      )}
      
      {currentPage === "detalhe" && token && selectedConceitoId && (
        <Detalhe
          token={token}
          cursoCodigo={cursoCodigo}
          conceitoId={selectedConceitoId}
          periodo={selectedPeriodo}
          onBack={() => setCurrentPage("dashboard")}
        />
      )}
    </>
  );
}

export default App;

export default App;
