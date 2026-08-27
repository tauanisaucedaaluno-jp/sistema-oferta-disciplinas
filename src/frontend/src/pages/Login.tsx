import React, { useState } from "react";
import logoImg from "../assets/logo.png";

interface LoginProps {
  onLoginSuccess: (token: string) => void;
}

const API_BASE = "http://localhost:8000";

export default function Login({ onLoginSuccess }: LoginProps) {
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
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

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <img src={logoImg} alt="OfertaPampa Logo" className="login-logo" />
          <h2>Olá, bem-vinda(o)!</h2>
          <p>Digite suas credenciais de coordenador para gerenciar a oferta</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="login-error-box">{error}</div>}

          <div className="form-group">
            <label htmlFor="email">E-mail institucional</label>
            <input
              id="email"
              type="email"
              placeholder="exemplo@unipampa.edu.br"
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

        <div className="login-hint">
          <p>🔑 Credenciais de teste: <code>coordenador@unipampa.edu.br</code> / <code>admin123</code></p>
        </div>
      </div>
    </div>
  );
}
