// O electron-vite roda do root do projeto (onde fica package.json), mas
// o vite renderer tem `root: ./frontend`. PostCSS é invocado pelo vite e
// seu cwd vira o root do PROCESSO (não do vite renderer), então o Tailwind
// não acha `tailwind.config.js` por busca padrão e cai num config default
// sem `content` — o erro `border-border class does not exist` vem disso.
//
// Fix: path absoluto pro tailwind.config.js neste mesmo diretório.
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))

export default {
  plugins: {
    tailwindcss: { config: resolve(here, 'tailwind.config.js') },
    autoprefixer: {},
  },
}
