import { app } from 'electron'
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'

/**
 * Caminhos do app — todos derivam de electron.app.getPath('userData'),
 * que em Windows resolve para %APPDATA%\PromoMargem\.
 *
 * - data.db → banco SQLite (preservado entre updates do app)
 * - logs/   → backend.log + main.log (rotação simples)
 *
 * O `productName` definido em electron-builder.yml define o nome do
 * diretório userData automaticamente — não precisa hardcodear "PromoMargem".
 */

export function userDataDir(): string {
  return app.getPath('userData')
}

export function dbPath(): string {
  return join(userDataDir(), 'data.db')
}

export function logsDir(): string {
  const dir = join(userDataDir(), 'logs')
  mkdirSync(dir, { recursive: true })
  return dir
}

/**
 * Caminho do backend empacotado pelo PyInstaller.
 *
 * - Em produção (app.isPackaged=true): `process.resourcesPath` aponta para
 *   `<app>/resources/`, e o electron-builder copia `resources/backend/` para
 *   lá via `extraResources` (ver electron-builder.yml).
 *
 * - Em dev com USE_BUNDLED_BACKEND=1: `process.resourcesPath` resolve para
 *   `node_modules/electron/dist/resources/` (resources do Electron próprio,
 *   NÃO do projeto). Precisamos cair de volta no path do projeto, que
 *   `app.getAppPath()` retorna corretamente em dev.
 */
export function backendExePath(): string {
  if (app.isPackaged) {
    return join(process.resourcesPath, 'backend', 'promomargem-backend.exe')
  }
  return join(app.getAppPath(), 'resources', 'backend', 'promomargem-backend.exe')
}

/**
 * Caminho do projeto Python em dev (relativo à raiz do repo).
 * Usado por backend.ts para spawnar `python -m uvicorn` em modo dev.
 */
export function pythonBackendDir(): string {
  return join(app.getAppPath(), '..', 'python-backend')
}
