import React, { useState, useEffect } from "react";
import logoImg from "../assets/logo.png";
import { API_BASE } from "../apiConfig";

interface DefinirSenhaProps {
  initialToken?: string | null;
  onLoginSuccess: (token: string) => void;
  onVoltarLogin: () => void;
}

export default function DefinirSenha({ initialToken, onLoginSuccess, onVoltarLogin }: DefinirSenhaProps) {
  const [token, setToken] = useState<string>("");
  const [novaSenha, setNovaSenha] = useState<string>("");
  const [confirmarSenha, setConfirmarSenha] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sucesso, setSucesso] = useState(false);

  useEffect(() => {
    if (initialToken) {
      setToken(initialToken);
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const t = params.get("token");
    if (t) {
      setToken(t);
    } else {
      setError("Token de ativação não encontrado na URL. Por favor, utilize o link recebido por e-mail ou solicite um novo acesso.");
    }
  }, [initialToken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!token) {
      setError("Link de ativação inválido ou ausente.");
      return;
    }

    if (novaSenha.length < 6) {
      setError("A senha deve ter no mínimo 6 caracteres.");
      return;
    }

    if (novaSenha !== confirmarSenha) {
      setError("A confirmação de senha não confere.");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/auth/definir-senha`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          token: token,
          nova_senha: novaSenha,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Erro ao definir senha.");
      }

      setSucesso(true);

      // Limpa os parâmetros de URL para manter endereço limpo
      try {
        window.history.replaceState({}, document.title, window.location.pathname);
      } catch {}

      // Se retornou access_token, faz o login após 1.5s
      setTimeout(() => {
        if (data.access_token) {
          onLoginSuccess(data.access_token);
        } else {
          onVoltarLogin();
        }
      }, 1500);

    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro de conexão ao definir senha.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <img src={logoImg} alt="OfertaPampa Logo" className="login-logo" />
          <h2>Definir Senha de Acesso</h2>
          <p>Crie sua senha segura de coordenador para acessar seu painel individual</p>
        </div>

        {sucesso ? (
          <div style={{ textAlign: "center", padding: "1.5rem 0" }}>
            <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🎉</div>
            <h3 style={{ color: "#0f766e", marginBottom: "0.5rem" }}>Senha definida com sucesso!</h3>
            <p style={{ color: "#64748b", fontSize: "0.9rem" }}>Entrando no sistema automaticamente...</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="login-form">
            {error && <div className="login-error-box">{error}</div>}

            {!token && (
              <div className="form-group">
                <label htmlFor="token-manual">Cole o Token de Ativação</label>
                <input
                  id="token-manual"
                  type="text"
                  placeholder="Cole aqui o token recebido..."
                  value={token}
                  onChange={(e) => setToken(e.target.value.trim())}
                  required
                />
              </div>
            )}

            <div className="form-group">
              <label htmlFor="novaSenha">Nova Senha (mínimo 6 caracteres)</label>
              <input
                id="novaSenha"
                type="password"
                placeholder="••••••••"
                value={novaSenha}
                onChange={(e) => setNovaSenha(e.target.value)}
                required
                minLength={6}
              />
            </div>

            <div className="form-group">
              <label htmlFor="confirmarSenha">Confirmar Nova Senha</label>
              <input
                id="confirmarSenha"
                type="password"
                placeholder="••••••••"
                value={confirmarSenha}
                onChange={(e) => setConfirmarSenha(e.target.value)}
                required
                minLength={6}
              />
            </div>

            <button type="submit" className="btn btn-primary btn-block" disabled={loading || !token}>
              {loading ? "Gravando senha..." : "Definir Senha e Entrar"}
            </button>

            <button
              type="button"
              className="btn btn-outline btn-block"
              style={{ marginTop: "0.75rem" }}
              onClick={onVoltarLogin}
            >
              Voltar ao Login
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
