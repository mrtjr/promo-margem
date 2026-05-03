import { app, dialog, ipcMain, shell } from 'electron'
import { readFile } from 'node:fs/promises'
import { getBackendUrl } from './backend'
import { userDataDir } from './paths'

/**
 * Handlers IPC — registrados no app.whenReady().
 * Nomes batem com os de electron/preload/index.ts.
 */
export function registerIpc(): void {
  ipcMain.handle('backend:url', () => {
    const url = getBackendUrl()
    if (!url) throw new Error('Backend ainda nao iniciou')
    return url
  })

  ipcMain.handle('app:version', () => app.getVersion())

  ipcMain.handle('app:abrirPastaDados', async () => {
    await shell.openPath(userDataDir())
  })

  ipcMain.handle('file:importarCSV', async () => {
    const result = await dialog.showOpenDialog({
      title: 'Importar CSV de fechamento',
      filters: [
        { name: 'CSV', extensions: ['csv'] },
        { name: 'Todos os arquivos', extensions: ['*'] },
      ],
      properties: ['openFile'],
    })
    if (result.canceled || result.filePaths.length === 0) return null
    const path = result.filePaths[0]
    const content = await readFile(path, 'utf-8')
    return { path, content }
  })
}
