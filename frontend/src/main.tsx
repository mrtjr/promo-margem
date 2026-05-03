import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import axios from 'axios'
import { electronApi, isElectron } from './lib/electron'
import App from './App.tsx'
import './index.css'

/**
 * Bootstrap minimo: configura axios.defaults.baseURL antes de renderizar.
 *
 * Quando rodando dentro do Electron: pega URL do backend embutido (porta
 * dinamica) via preload. Quando rodando como web puro (vite --rendererOnly,
 * util pra dev rapido de UI): usa VITE_API_URL ou /api como fallback.
 *
 * Definir em axios.defaults significa que TODAS as chamadas existentes em
 * App.tsx (que usam axios.get/post direto) funcionam sem refactor.
 */
async function bootstrap(): Promise<void> {
  if (isElectron()) {
    try {
      const url = await electronApi.backendURL()
      axios.defaults.baseURL = url
    } catch (err) {
      console.error('Backend nao disponivel:', err)
      axios.defaults.baseURL = 'http://127.0.0.1:8000'
    }
  } else {
    axios.defaults.baseURL =
      (import.meta.env.VITE_API_URL as string | undefined) || '/api'
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void bootstrap()
