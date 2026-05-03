import axios, { AxiosInstance } from 'axios'
import { electronApi, isElectron } from './electron'

/**
 * Singleton de axios configurado contra o backend embutido.
 *
 * Em Electron: baseURL vem do main process (porta dinamica via window.api.backendURL).
 * Em desenvolvimento web puro (raro — só pra rodar `vite --rendererOnly`):
 * cai em VITE_API_URL ou /api.
 */

let _client: AxiosInstance | null = null

export async function getApi(): Promise<AxiosInstance> {
  if (_client) return _client

  let baseURL: string
  if (isElectron()) {
    baseURL = await electronApi.backendURL()
  } else {
    baseURL = (import.meta.env.VITE_API_URL as string | undefined) || '/api'
  }

  _client = axios.create({
    baseURL,
    timeout: 30_000,
  })
  return _client
}

/**
 * Helper sincrono que assume que getApi() ja foi chamado pelo menos 1x.
 * Usado em handlers de evento onde await fica desconfortavel.
 */
export function api(): AxiosInstance {
  if (!_client) throw new Error('api() antes de getApi() — chame getApi() no startup')
  return _client
}
