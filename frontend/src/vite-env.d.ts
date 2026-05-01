/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * URL do backend. Em produção fica vazio (usa /api via nginx proxy
   * configurado em frontend/nginx.conf). Em `npm run dev` defina:
   *   VITE_API_URL=http://localhost:8000
   * num arquivo `.env` ou `.env.local` em frontend/.
   */
  readonly VITE_API_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
