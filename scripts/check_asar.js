// Inspeciona dist/win-unpacked/resources/app.asar pra confirmar
// que o CSS final do renderer foi empacotado e tem o tamanho esperado.
const asar = require('@electron/asar');
const fs = require('node:fs');
const path = require('node:path');

const ASAR = path.join('dist', 'win-unpacked', 'resources', 'app.asar');

// asar list mostrou paths com backslash (windows), mas internamente
// o getNode() splita por path.sep, então usar path.sep do runtime.
const tree = asar.listPackage(ASAR);
const cssEntry = tree.find((e) => e.endsWith('.css'));
console.log('css entry in asar:', JSON.stringify(cssEntry));

if (!cssEntry) {
  console.error('FAIL: nenhum .css encontrado no asar');
  process.exit(1);
}

// normaliza pra path.sep
const normalized = cssEntry.replace(/^[\\/]+/, '').split(/[\\/]/).join(path.sep);
console.log('extracting:', normalized);

const buf = asar.extractFile(ASAR, normalized);
console.log('size in asar:', buf.length, 'bytes');

const onDisk = fs.readFileSync(path.join('out', 'renderer', 'assets', path.basename(cssEntry)));
console.log('size on disk:', onDisk.length, 'bytes');

const identical = Buffer.compare(buf, onDisk) === 0;
console.log('identical:', identical);

// Validacao amostral do conteudo
const text = buf.toString('utf8');
const checks = [
  ['tracking-editorial', text.includes('tracking-editorial')],
  ['Fraunces font', text.includes('Fraunces')],
  ['var(--claude-coral)', text.includes('var(--claude-coral)')],
  ['claude-card', text.includes('claude-card')],
  ['text-4xl', text.includes('text-4xl')],
];
for (const [name, ok] of checks) console.log(`  ${ok ? 'OK' : 'MISS'}  ${name}`);
