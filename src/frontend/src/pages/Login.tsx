import React, { useState } from "react";
import logoImg from "../assets/logo.png";

interface LoginProps {
  onLoginSuccess: (token: string) => void;
  onIrParaDefinirSenha?: (token?: string) => void;
}

const API_BASE = "http://localhost:8000";

export default function Login({ onLoginSuccess }: LoginProps) {
  const [tab, setTab] = useState<"login" | "cadastrar">("login");

  // Estados de Login
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Estados de Cadastro Direto
  const [emailCadastro, setEmailCadastro] = useState("");
  const [senhaCadastro, setSenhaCadastro] = useState("");
  const [confirmarSenha, setConfirmarSenha] = useState("");
  const [cadastroLoading, setCadastroLoading] = useState(false);
  const [cadastroError, setCadastroError] = useState<string | null>(null);

  const handleSubmitLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, senha }),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Falha ao realizar login. Verifique suas credenciais.");
      }

      const data = await response.json();
      onLoginSuccess(data.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro de conexão ao tentar fazer login.");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitCadastro = async (e: React.FormEvent) => {
    e.preventDefault();
    setCadastroError(null);

    if (senhaCadastro.length < 6) {
      setCadastroError("A senha deve conter no mínimo 6 caracteres.");
      return;
    }

    if (senhaCadastro !== confirmarSenha) {
      setCadastroError("A confirmação de senha não confere com a senha informada.");
      return;
    }

    setCadastroLoading(true);

    try {
      const response = await fetch(`${API_BASE}/auth/cadastrar`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email: emailCadastro,
          senha: senhaCadastro,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Erro ao realizar cadastro.");
      }

      // Login imediato após criação de conta
      if (data.access_token) {
        onLoginSuccess(data.access_token);
      }
    } catch (err) {
      setCadastroError(err instanceof Error ? err.message : "Erro de conexão ao realizar cadastro.");
    } finally {
      setCadastroLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <img src={logoImg} alt="OfertaPampa Logo" className="login-logo" />
          <h2>Sistema de Oferta de Disciplinas</h2>
          <p>Planejamento acadêmico e previsão de demanda de matrículas</p>
        </div>

        {/* Abas Alternadoras */}
        <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem", borderBottom: "1px solid #e2e8f0", paddingBottom: "0.5rem" }}>
          <button
            type="button"
            style={{
              flex: 1,
              padding: "0.5rem",
              background: tab === "login" ? "#0f766e" : "transparent",
              color: tab === "login" ? "#fff" : "#64748b",
              border: "none",
              borderRadius: "6px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s",
            }}
            onClick={() => { setTab("login"); setError(null); }}
          >
            Entrar no Sistema
          </button>
          <button
            type="button"
            style={{
              flex: 1,
              padding: "0.5rem",
              background: tab === "cadastrar" ? "#0f766e" : "transparent",
              color: tab === "cadastrar" ? "#fff" : "#64748b",
              border: "none",
              borderRadius: "6px",
              fontWeight: 600,
              cursor: "pointer",
              transition: "all 0.2s",
            }}
            onClick={() => { setTab("cadastrar"); setCadastroError(null); }}
          >
            Criar Nova Conta
          </button>
        </div>

        {tab === "login" ? (
          <form onSubmit={handleSubmitLogin} className="login-form">
            {error && <div className="login-error-box">{error}</div>}

            <div className="form-group">
              <label htmlFor="email">E-mail institucional</label>
              <input
                id="email"
                type="email"
                placeholder="coordenador@unipampa.edu.br"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="senha">Senha</label>
              <input
                id="senha"
                type="password"
                placeholder="••••••••"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? "Entrando..." : "Entrar no Sistema"}
            </button>
          </form>
        ) : (
          <form onSubmit={handleSubmitCadastro} className="login-form">
            {cadastroError && <div className="login-error-box">{cadastroError}</div>}

            <p style={{ color: "#64748b", fontSize: "0.88rem", marginBottom: "1rem" }}>
              Cadastre sua conta de coordenador(a) diretamente aqui. Você definirá sua senha agora e terá acesso imediato ao seu painel exclusivo.
            </p>

            <div className="form-group">
              <label htmlFor="email-cadastro">E-mail institucional</label>
              <input
                id="email-cadastro"
                type="email"
                placeholder="coordenador.curso@unipampa.edu.br"
                value={emailCadastro}
                onChange={(e) => setEmailCadastro(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label htmlFor="senha-cadastro">Senha de Acesso (mínimo 6 caracteres)</label>
              <input
                id="senha-cadastro"
                type="password"
                placeholder="••••••••"
                value={senhaCadastro}
                onChange={(e) => setSenhaCadastro(e.target.value)}
                required
                minLength={6}
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmar-senha">Confirmar Senha</label>
              <input
                id="confirmar-senha"
                type="password"
                placeholder="••••••••"
                value={confirmarSenha}
                onChange={(e) => setConfirmarSenha(e.target.value)}
                required
                minLength={6}
              />
            </div>

            <button type="submit" className="btn btn-primary btn-block" disabled={cadastroLoading}>
              {cadastroLoading ? "Criando sua conta..." : "Criar Conta e Acessar"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

