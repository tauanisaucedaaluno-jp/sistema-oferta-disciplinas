// Configuração central da URL da API backend.
// Em desenvolvimento: usa http://localhost:8000.
// Em produção (Vercel): usa a variável de ambiente VITE_API_URL.
export const API_BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
