/**
 * Wrapper tipado para a API exposta pelo preload via contextBridge.
 *
 * Sempre que adicionar um handler em electron/preload/index.ts, replicar
 * a assinatura aqui. Renderer nunca chama ipcRenderer direto — usa esses
 * helpers (que validam tipo e dão autocomplete).
 */

export interface ElectronApi {
  backendURL: () => Promise<string>
  appVersion: () => Promise<string>
  importarCSV: () => Promise<{ path: string; content: string } | null>
  abrirPastaDados: () => Promise<void>
}

declare global {
  interface Window {
    api?: ElectronApi
  }
}

export function isElectron(): boolean {
  return typeof window !== 'undefined' && !!window.api
}

export const electronApi: ElectronApi = {
  async backendURL() {
    if (!window.api) throw new Error('Nao esta rodando dentro do Electron')
    return window.api.backendURL()
  },
  async appVersion() {
    if (!window.api) return 'web'
    return window.api.appVersion()
  },
  async importarCSV() {
    if (!window.api) throw new Error('Importacao via dialog so funciona no app desktop')
    return window.api.importarCSV()
  },
  async abrirPastaDados() {
    if (!window.api) throw new Error('Acesso ao Explorer so funciona no app desktop')
    return window.api.abrirPastaDados()
  },
}
