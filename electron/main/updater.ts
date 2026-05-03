import { app, Notification } from 'electron'
import { autoUpdater } from 'electron-updater'
import { join } from 'node:path'
import { logsDir } from './paths'

/**
 * Auto-update silencioso.
 *
 * Comportamento:
 *   - Checa update no startup e a cada 4h
 *   - Download em background (autoDownload)
 *   - Notifica via Notification nativa quando download completa
 *   - Instala automaticamente no próximo `quit` (autoInstallOnAppQuit)
 *
 * Em DEV (app.isPackaged=false), não faz nada — evita ruído no terminal.
 * Em PROD, usa GitHub Releases privado configurado em electron-builder.yml.
 */

export function setupUpdater(): void {
  if (!app.isPackaged) return

  autoUpdater.autoDownload = true
  autoUpdater.autoInstallOnAppQuit = true

  // Logs em %APPDATA%\PromoMargem\logs\updater.log
  // (electron-updater usa console.log por default — basta interceptar)
  const logPath = join(logsDir(), 'updater.log')
  const log = require('fs').createWriteStream(logPath, { flags: 'a' })
  autoUpdater.logger = {
    info: (msg: string) => log.write(`[info] ${new Date().toISOString()} ${msg}\n`),
    warn: (msg: string) => log.write(`[warn] ${new Date().toISOString()} ${msg}\n`),
    error: (msg: string) => log.write(`[error] ${new Date().toISOString()} ${msg}\n`),
    debug: () => {},
  } as never

  autoUpdater.on('update-downloaded', (info) => {
    new Notification({
      title: 'PromoMargem atualizado',
      body: `Versao ${info.version} pronta. Sera instalada no proximo fechamento.`,
    }).show()
  })

  autoUpdater.on('error', (err) => {
    log.write(`[error] ${new Date().toISOString()} ${err?.message || err}\n`)
  })

  void autoUpdater.checkForUpdatesAndNotify()
  setInterval(() => {
    void autoUpdater.checkForUpdates()
  }, 4 * 60 * 60 * 1000)
}
