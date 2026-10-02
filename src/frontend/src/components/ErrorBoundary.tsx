import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error in component tree:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          backgroundColor: "#f8fafc",
          fontFamily: "system-ui, -apple-system, sans-serif",
          padding: "2rem",
          textAlign: "center"
        }}>
          <div style={{
            backgroundColor: "#ffffff",
            padding: "2.5rem",
            borderRadius: "12px",
            boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
            maxWidth: "500px",
            width: "100%"
          }}>
            <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>⚠️</div>
            <h2 style={{ color: "#1e293b", margin: "0 0 0.5rem 0", fontSize: "1.5rem" }}>
              Ocorreu um erro inesperado
            </h2>
            <p style={{ color: "#64748b", margin: "0 0 1.5rem 0", fontSize: "0.95rem" }}>
              Ocorreu um problema ao renderizar esta tela. Clique no botão abaixo para tentar novamente ou voltar à página principal.
            </p>
            {this.state.error && (
              <pre style={{
                backgroundColor: "#f1f5f9",
                padding: "0.75rem",
                borderRadius: "6px",
                fontSize: "0.8rem",
                color: "#e11d48",
                overflowX: "auto",
                marginBottom: "1.5rem",
                textAlign: "left"
              }}>
                {this.state.error.message}
              </pre>
            )}
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              style={{
                backgroundColor: "#0284c7",
                color: "#ffffff",
                border: "none",
                padding: "0.75rem 1.5rem",
                borderRadius: "6px",
                fontWeight: 600,
                fontSize: "0.95rem",
                cursor: "pointer",
                transition: "background-color 0.2s"
              }}
            >
              Recarregar Aplicação
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
