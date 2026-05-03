import { app } from 'electron'
import { spawn, ChildProcess } from 'node:child_process'
import { createServer } from 'node:net'
import { dirname, join } from 'node:path'
import { createWriteStream, WriteStream } from 'node:fs'
import { backendExePath, dbPath, logsDir, pythonBackendDir } from './paths'

/**
 * Gerencia o ciclo de vida do backend Python embutido.
 *
 * Em DEV (app.isPackaged=false e USE_BUNDLED_BACKEND != "1"):
 *   spawna `python -m uvicorn app.main:app` direto do venv local.
 *   Edição de Python → uvicorn --reload pega.
 *
 * Em PROD (ou USE_BUNDLED_BACKEND=1):
 *   spawna o promomargem-backend.exe gerado pelo PyInstaller.
 *
 * Porta: dinâmica (acha primeira livre acima de 50000) — evita conflito
 * com qualquer outro processo na máquina e permite múltiplas instâncias
 * em dev (cada worktree pode subir seu próprio).
 *
 * Health check: poll GET /health até 200 OK ou timeout 30s.
 */

let child: ChildProcess | null = null
let logStream: WriteStream | null = null
let backendUrl: string | null = null

async function findFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = createServer()
    srv.unref()
    srv.on('error', reject)
    srv.listen(0, '127.0.0.1', () => {
      const addr = srv.address()
      if (typeof addr === 'string' || addr === null) {
        reject(new Error('Falha ao obter porta livre'))
        return
      }
      const port = addr.port
      srv.close(() => resolve(port))
    })
  })
}

async function waitHealthy(url: string, timeoutMs = 30_000): Promise<void> {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(`${url}/health`)
      if (res.ok) return
    } catch {
      // ainda subindo
    }
    await new Promise((r) => setTimeout(r, 500))
  }
  throw new Error(`Backend nao respondeu em ${timeoutMs}ms`)
}

export async function startBackend(): Promise<string> {
  if (backendUrl) return backendUrl

  const port = await findFreePort()
  const url = `http://127.0.0.1:${port}`

  const useBundled =
    app.isPackaged || process.env.USE_BUNDLED_BACKEND === '1'

  const env: NodeJS.ProcessEnv = {
    ...process.env,
    DB_PATH: dbPath(),
    PORT: String(port),
    HOST: '127.0.0.1',
  }

  let exe: string
  let args: string[]
  let cwd: string

  if (useBundled) {
    exe = backendExePath()
    args = [
      '--host', '127.0.0.1',
      '--port', String(port),
    ]
    // cwd = mesmo dir do .exe (PyInstaller onedir precisa do _internal/ ao
    // lado). Em dev resolve para resources/backend; em prod, idem via
    // process.resourcesPath. Usar dirname(exe) cobre os dois casos sem
    // duplicar lógica de paths.
    cwd = dirname(exe)
  } else {
    const pyDir = pythonBackendDir()
    exe = join(pyDir, '.venv', 'Scripts', 'python.exe')
    args = [
      '-m', 'uvicorn',
      'app.main:app',
      '--host', '127.0.0.1',
      '--port', String(port),
    ]
    cwd = pyDir
  }

  const logPath = join(logsDir(), 'backend.log')
  logStream = createWriteStream(logPath, { flags: 'a' })
  logStream.write(`\n=== ${new Date().toISOString()} START ${exe} ${args.join(' ')} ===\n`)

  child = spawn(exe, args, {
    cwd,
    env,
    windowsHide: true,
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  child.stdout?.pipe(logStream, { end: false })
  child.stderr?.pipe(logStream, { end: false })

  child.on('exit', (code, signal) => {
    logStream?.write(`=== EXIT code=${code} signal=${signal} ===\n`)
    backendUrl = null
    child = null
  })

  await waitHealthy(url)
  backendUrl = url
  return url
}

export async function stopBackend(): Promise<void> {
  if (!child) return
  return new Promise((resolve) => {
    const timeout = setTimeout(() => {
      child?.kill('SIGKILL')
      resolve()
    }, 3_000)
    child!.once('exit', () => {
      clearTimeout(timeout)
      logStream?.end()
      logStream = null
      resolve()
    })
    child!.kill('SIGTERM')
  })
}

export function getBackendUrl(): string | null {
  return backendUrl
}
