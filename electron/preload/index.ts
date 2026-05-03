import { contextBridge, ipcRenderer } from 'electron'

/**
 * API exposta ao renderer via contextBridge.
 *
 * Renderer NUNCA acessa Node, fs, ipcRenderer diretamente. Tudo passa
 * por window.api, que é tipado em src/lib/electron.ts.
 *
 * Manter superficie minima — adicionar handlers só conforme necessidade.
 */
const api = {
  /**
   * URL base do backend FastAPI (porta dinâmica). Renderer usa isso pra
   * configurar axios.baseURL no startup.
   */
  backendURL: (): Promise<string> => ipcRenderer.invoke('backend:url'),

  /**
   * Versão do app (para mostrar em "Sobre").
   */
  appVersion: (): Promise<string> => ipcRenderer.invoke('app:version'),

  /**
   * Abre file dialog nativo pra escolher arquivo CSV (substitui upload HTTP).
   * Retorna null se usuário cancelar.
   */
  importarCSV: (): Promise<{ path: string; content: string } | null> =>
    ipcRenderer.invoke('file:importarCSV'),

  /**
   * Abre o diretorio de dados (%APPDATA%/PromoMargem/) no Explorer.
   * Util pra usuario fazer backup do data.db manualmente.
   */
  abrirPastaDados: (): Promise<void> => ipcRenderer.invoke('app:abrirPastaDados'),
}

contextBridge.exposeInMainWorld('api', api)

export type Api = typeof api
