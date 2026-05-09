import { useState, useEffect, useRef } from 'react'
import { LayoutDashboard, Package, Calculator, TrendingUp, AlertTriangle, Sparkles, ArrowRight, Gauge, ShoppingBag, FileText, Save, Copy, Check, Send, Bot, User, Trash2, Clipboard, AlertCircle, Target, History, ArrowDownCircle, ArrowUpCircle, X, ArrowUpRight, ArrowDownRight, Minus, PieChart, Receipt, Percent, Plus, Scale, Building2, Wallet, BarChart3, Lock, Skull, Wand2, ChevronDown, ChevronRight } from 'lucide-react'
import axios from 'axios'
import type { Produto, Grupo, Stats } from './types'
import { EmptyState } from './components/EmptyState'
import { FeedbackBanner, type FeedbackMessage } from './components/FeedbackBanner'
import { MetricValue } from './components/MetricValue'
import { WidgetSkeleton } from './components/WidgetSkeleton'
import { useEscapeKey } from './hooks/useEscapeKey'
import { useModalA11y } from './hooks/useModalA11y'
import { formatCurrency, formatDate, formatDateTime, formatNumber, formatPercent } from './lib/format'

// API base URL: Electron injeta axios.defaults.baseURL no preload/main.
// Mantenha relativo; VITE_API_URL so deve sobrescrever em desenvolvimento.
const API_URL = (import.meta.env.VITE_API_URL as string | undefined) || ''

const CIDADES = ["TEIXEIRA DE FREITAS", "ITAMARAJU"]

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [clienteDrillTarget, setClienteDrillTarget] = useState<number | null>(null)

  // Abre Clientes com drill direto ao chamar do widget Dashboard.
  const abrirClienteDrill = (id: number) => {
    setClienteDrillTarget(id)
    setCurrentPage('clientes')
  }

  // Stats refetch ao montar E sempre que o usuário volta ao Dashboard.
  // Sem isso, mutations em outras páginas (fechamento do dia, importar CSV,
  // registrar quebra, exclusão) não eram refletidas nos KPIs do Painel de
  // Decisão até o app ser reaberto — o stats vinha do mount inicial e
  // nunca era invalidado.
  useEffect(() => {
    if (currentPage !== 'dashboard') return
    let cancelado = false
    const fetch = async () => {
      try {
        const res = await axios.get(`${API_URL}/stats`)
        if (!cancelado) setStats(res.data)
      } catch (err) {
        console.error("Failed to fetch stats", err)
      } finally {
        if (!cancelado) setLoading(false)
      }
    }
    fetch()
    return () => { cancelado = true }
  }, [currentPage])

  return (
    <div className="flex h-screen bg-[color:var(--claude-cream)] text-[color:var(--claude-ink)] font-sans">
      {/* Sidebar */}
      <aside className="w-64 flex flex-col text-[color:var(--claude-cream)]"
             style={{ background: 'linear-gradient(180deg, #1C1B17 0%, #252219 100%)' }}>
        <div className="p-6">
          <h1 className="headline text-[28px] leading-none tracking-editorial">
            <span className="text-[color:var(--claude-cream)]">Promo</span>
            <span className="text-[color:var(--claude-coral-soft)]">Margem</span>
          </h1>
          <p className="section-label mt-2 text-[color:var(--claude-cream)]/50">Gestão Inteligente</p>
        </div>

        <nav className="flex-1 mt-6 px-3 space-y-1 overflow-y-auto">
          <NavItem 
            isActive={currentPage === 'dashboard'} 
            onClick={() => setCurrentPage('dashboard')}
            icon={<LayoutDashboard size={20} />} 
            label="Dashboard" 
          />
          <NavItem 
            isActive={currentPage === 'chat'} 
            onClick={() => setCurrentPage('chat')}
            icon={<Sparkles size={20} />} 
            label="Chat com IA" 
          />
          <NavItem
            isActive={currentPage === 'produtos'}
            onClick={() => setCurrentPage('produtos')}
            icon={<Package size={20} />}
            label="Produtos"
          />
          <NavItem
            isActive={currentPage === 'clientes'}
            onClick={() => setCurrentPage('clientes')}
            icon={<User size={20} />}
            label="Clientes"
          />
          <div className="mt-4 pt-4 pb-2 px-4 section-label text-[color:var(--claude-cream)]/40 border-t border-white/10">Operações</div>
          <NavItem 
            isActive={currentPage === 'compras'} 
            onClick={() => setCurrentPage('compras')}
            icon={<ShoppingBag size={20} />} 
            label="Entrada (Excel)" 
          />
          <NavItem
            isActive={currentPage === 'relatorios'}
            onClick={() => setCurrentPage('relatorios')}
            icon={<FileText size={20} />}
            label="Fechamento do Dia"
          />
          <NavItem
            isActive={currentPage === 'briefing'}
            onClick={() => setCurrentPage('briefing')}
            icon={<Sparkles size={20} />}
            label="Briefing Diário"
          />
          <NavItem
            isActive={currentPage === 'projecao'}
            onClick={() => setCurrentPage('projecao')}
            icon={<Target size={20} />}
            label="Projeção D+1"
          />
          <NavItem
            isActive={currentPage === 'simulador'}
            onClick={() => setCurrentPage('simulador')}
            icon={<Calculator size={20} />}
            label="Simulador"
          />
          <NavItem
            isActive={currentPage === 'promo_engine'}
            onClick={() => setCurrentPage('promo_engine')}
            icon={<Wand2 size={20} />}
            label="Promo Inteligente"
          />
          <NavItem
            isActive={currentPage === 'historico'}
            onClick={() => setCurrentPage('historico')}
            icon={<History size={20} />}
            label="Histórico"
          />
          <NavItem
            isActive={currentPage === 'quebras'}
            onClick={() => setCurrentPage('quebras')}
            icon={<Skull size={20} />}
            label="Quebras"
          />
          <div className="mt-4 pt-4 pb-2 px-4 section-label text-[color:var(--claude-cream)]/40 border-t border-white/10">Financeiro</div>
          <NavItem
            isActive={currentPage === 'dre'}
            onClick={() => setCurrentPage('dre')}
            icon={<PieChart size={20} />}
            label="DRE"
          />
          <NavItem
            isActive={currentPage === 'bp'}
            onClick={() => setCurrentPage('bp')}
            icon={<Scale size={20} />}
            label="Balanço Patrimonial"
          />
          <NavItem
            isActive={currentPage === 'dfc'}
            onClick={() => setCurrentPage('dfc')}
            icon={<Wallet size={20} />}
            label="DFC"
          />
          <NavItem
            isActive={currentPage === 'dmpl'}
            onClick={() => setCurrentPage('dmpl')}
            icon={<BarChart3 size={20} />}
            label="DMPL"
          />
        </nav>

        <div className="p-4 border-t border-white/5">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full flex items-center justify-center text-xs font-bold text-[color:var(--claude-ink)]"
                 style={{ background: 'var(--claude-coral-soft)' }}>JR</div>
            <div>
              <p className="text-sm font-medium text-[color:var(--claude-cream)]">Gestor Comercial</p>
              <div className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[color:var(--claude-sage)] animate-pulse"></span>
                <p className="text-[10px] text-[color:var(--claude-cream)]/50 uppercase tracking-widest">Online</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {loading && !['chat', 'compras', 'produtos', 'dashboard', 'bp', 'promo_engine', 'dfc', 'dmpl'].includes(currentPage) ? (
          <EmptyState variant="loading" className="h-full" title="Carregando…" />
        ) : (
          <div className="flex-1 overflow-y-auto">
            {currentPage === 'dashboard' && <DashboardPage stats={stats} onNavigate={setCurrentPage} onAbrirCliente={abrirClienteDrill} />}
            {currentPage === 'chat' && <ChatPage />}
            {currentPage === 'produtos' && <ProdutosPage />}
            {currentPage === 'clientes' && (
              <ClientesPage
                key={clienteDrillTarget ?? 'standalone'}
                initialClienteId={clienteDrillTarget}
              />
            )}
            {currentPage === 'compras' && <ComprasPage onComplete={() => setCurrentPage('produtos')} />}
            {currentPage === 'relatorios' && <RelatoriosPage />}
            {currentPage === 'briefing' && <BriefingPage />}
            {currentPage === 'projecao' && <ProjecaoPage />}
            {currentPage === 'simulador' && <SimuladorPage />}
            {currentPage === 'promo_engine' && <SimuladorPage initialTab="engine" />}
            {currentPage === 'historico' && <HistoricoPage />}
            {currentPage === 'quebras' && <QuebrasPage />}
            {currentPage === 'dre' && <DREPage />}
            {currentPage === 'bp' && <BPPage />}
            {currentPage === 'dfc' && <DFCPage />}
            {currentPage === 'dmpl' && <DMPLPage />}
          </div>
        )}
      </main>
    </div>
  )
}

function NavItem({ icon, label, isActive, onClick }: any) {
  return (
    <button
      onClick={onClick}
      className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 ${
        isActive
          ? 'bg-[color:var(--claude-coral)]/18 text-[color:var(--claude-coral-soft)] border border-[color:var(--claude-coral)]/30'
          : 'text-[color:var(--claude-cream)]/60 hover:bg-white/5 hover:text-[color:var(--claude-cream)] border border-transparent'
      }`}
    >
      {icon}
      <span className="text-sm font-medium">{label}</span>
    </button>
  )
}

// ============================================================================
// Confirm — modal genérico de confirmação (substitui window.confirm nativo).
// Estilo coerente com claude-card; suporta variante perigosa (vermelho) e
// estado de loading (durante a ação assíncrona).
// ============================================================================

type ConfirmProps = {
  open: boolean
  title: string
  body?: React.ReactNode
  confirmLabel?: string
  cancelLabel?: string
  danger?: boolean    // estiliza botão vermelho + ícone alerta
  loading?: boolean   // desabilita ambos os botões e troca label do confirmar
  onConfirm: () => void
  onCancel: () => void
}

function Confirm({
  open, title, body,
  confirmLabel = 'Confirmar', cancelLabel = 'Cancelar',
  danger = false, loading = false,
  onConfirm, onCancel,
}: ConfirmProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  // Politica de fechamento: ESC fecha SE nao estiver processando uma acao
  // critica em andamento. Click no backdrop segue mesma regra (linha 269).
  useEscapeKey(() => onCancel(), { disabled: !open || loading })
  // A11y: foco entra no modal ao abrir e volta pra origem ao fechar.
  useModalA11y(open ? containerRef : { current: null })

  if (!open) return null
  const accent = danger ? 'var(--claude-coral)' : 'var(--claude-amber)'
  const titleId = 'confirm-title'
  return (
    <div
      className="fixed inset-0 bg-[color:var(--claude-ink)]/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
      onClick={() => !loading && onCancel()}
    >
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="claude-card p-6 max-w-md w-full"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center"
              style={{ background: `color-mix(in srgb, ${accent} 15%, transparent)` }}
            >
              <AlertTriangle size={20} style={{ color: accent }} />
            </div>
            <div>
              <p className="section-label">Confirmação</p>
              <h3 id={titleId} className="headline text-xl">{title}</h3>
            </div>
          </div>
          <button
            onClick={() => !loading && onCancel()}
            disabled={loading}
            className="p-1 text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)] disabled:opacity-50"
            aria-label="Fechar"
          >
            <X size={18} />
          </button>
        </div>

        {body && (
          <div className="text-sm text-[color:var(--claude-ink)] mb-5">{body}</div>
        )}

        <div className="flex gap-2 justify-end">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-sm rounded-lg border border-[color:var(--border)] text-[color:var(--claude-ink)] hover:bg-[color:var(--claude-cream-deep)] disabled:opacity-50"
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className="px-4 py-2 text-sm rounded-lg font-medium text-white hover:opacity-90 disabled:opacity-50"
            style={{ background: accent }}
          >
            {loading ? 'Processando…' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

function ComprasPage({ onComplete }: any) {
  const [produtos, setProdutos] = useState<Produto[]>([])
  const [grupos, setGrupos] = useState<Grupo[]>([])
  const [rows, setRows] = useState<any[]>([
    { id: Date.now(), matchedId: null, codigo: '', name: '', cidade: '', qtd: '', peso: '', vl_fp: '', grupo_id: null }
  ])
  const [submitting, setSubmitting] = useState(false)
  // Feedback inline (substitui alert nativos: avisos modais bloqueavam o
  // fluxo e tinham tom destoante do resto do app).
  const [feedback, setFeedback] = useState<FeedbackMessage | null>(null)

  useEffect(() => {
    axios.get(`${API_URL}/produtos`).then(res => setProdutos(res.data))
    axios.get(`${API_URL}/grupos`).then(res => setGrupos(res.data))
  }, [])

  const handlePaste = (e: React.ClipboardEvent) => {
    e.preventDefault()
    const clipboardData = e.clipboardData.getData('text')
    const lines = clipboardData.split(/\r?\n/).filter(line => line.trim() !== '')
    
    const newRows = lines.map(line => {
      const parts = line.split('\t').map(p => p.trim())
      // Formato aceito (7 colunas — código é opcional no final):
      //   Prod | Cid | Qtd | Peso | Valor | Categoria | Código
      // Detecta pelo nº de colunas; com 6 colunas usa o formato legado (sem código).
      let name = '', cidade = '', qtd = '', peso = '', vl_fp = '', cat_text = '', codigo = ''
      if (parts.length >= 7) {
        [name, cidade, qtd, peso, vl_fp, cat_text, codigo] = parts
      } else {
        [name, cidade, qtd, peso, vl_fp, cat_text] = parts
      }

      // Auto-match: primeiro por código (se veio), depois por nome
      let matched = null as any
      if (codigo) {
        matched = produtos.find(p => (p.codigo || '').toLowerCase() === codigo.toLowerCase())
      }
      if (!matched) {
        matched = produtos.find(p =>
          p.nome.toLowerCase().includes((name || '').toLowerCase()) ||
          (name || '').toLowerCase().includes(p.nome.toLowerCase())
        )
      }

      // Match category
      let matchedGroupId = matched?.grupo_id || null
      if (!matchedGroupId && cat_text) {
        const foundGroup = grupos.find(g => g.nome.toLowerCase().includes(cat_text.toLowerCase()))
        if (foundGroup) matchedGroupId = foundGroup.id
      }

      // Match city
      let matchedCidade = cidade || ''
      if (cidade) {
        const foundCidade = CIDADES.find(c => c.toLowerCase().includes(cidade.toLowerCase()))
        if (foundCidade) matchedCidade = foundCidade
      }

      return {
        id: Math.random(),
        matchedId: matched?.id || null,
        codigo: codigo || matched?.codigo || '',
        name: name || '',
        cidade: matchedCidade,
        qtd: qtd || '',
        peso: peso || '',
        vl_fp: vl_fp || '',
        grupo_id: matchedGroupId
      }
    })

    setRows(newRows)
  }

  const updateRow = (id: number, field: string, value: any) => {
    setRows(rows.map(row => row.id === id ? { ...row, [field]: value } : row))
  }

  const isValidRow = (r: any) => {
    return r.name?.trim() && r.peso && r.vl_fp && r.grupo_id && r.cidade;
  }

  const handleSubmit = async () => {
    const validEntradas = rows
      .filter(r => isValidRow(r))
      .map(r => ({
        produto_id: r.matchedId,
        nome_produto: r.name ? r.name.trim() : '',
        codigo: r.codigo ? String(r.codigo).trim() : null,
        quantidade: parseInt(String(r.qtd).replace(/\D/g, '')) || 0,
        peso: parseFloat(String(r.peso).replace(',', '.')),
        custo_unitario: parseFloat(String(r.vl_fp).replace(',', '.')),
        cidade: r.cidade,
        grupo_id: r.grupo_id
      }))

    if (validEntradas.length === 0) {
      setFeedback({
        tone: 'warn',
        mensagem: 'Toda linha precisa ter Produto, Cidade, Peso, Valor e Categoria preenchidos.',
      })
      return
    }

    setFeedback(null)
    setSubmitting(true)
    try {
      await axios.post(`${API_URL}/entradas/bulk`, { entradas: validEntradas })
      setFeedback({
        tone: 'ok',
        mensagem: `${validEntradas.length} lançamento${validEntradas.length === 1 ? '' : 's'} salvo${validEntradas.length === 1 ? '' : 's'}.`,
      })
      // Pequeno delay pro usuario ver a confirmacao antes do redirect.
      setTimeout(() => onComplete(), 600)
    } catch (err) {
      setFeedback({
        tone: 'alert',
        mensagem: 'Erro ao salvar lançamentos no servidor. Confira os dados e tente de novo.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-center">
        <div>
          <h2 className="headline text-4xl tracking-editorial mb-2 flex items-center gap-3">
            <Clipboard className="text-blue-500" /> Entrada de Estoque Inteligente
          </h2>
          <p className="text-slate-500 font-medium">Os produtos que não estiverem no sistema serão <b>criados automaticamente</b>.</p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="bg-blue-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-blue-700 shadow-xl shadow-blue-600/20 transition-all active:scale-95 flex items-center gap-2"
          >
            <Save size={20} /> {submitting ? 'Salvando…' : 'Finalizar Cadastro'}
          </button>
        </div>
      </header>

      <FeedbackBanner feedback={feedback} onDismiss={() => setFeedback(null)} />

      <div 
        onPaste={handlePaste}
        className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden"
      >
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Status</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Produto (Excel)</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Código ERP</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Sistema</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Cidade</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">QTD (Vol)</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">PESO Unit.</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">VALOR</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">CATEGORIA</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map(row => (
              <tr key={row.id} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4 text-center">
                  {row.matchedId ? (
                    <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 text-emerald-600" title="Produto Vinculado">
                      <Check size={14} />
                    </div>
                  ) : (isValidRow(row) ? (
                    <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 text-blue-600" title="Novo Produto (Será Criado)">
                      <Sparkles size={14} />
                    </div>
                  ) : (
                    <div className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-amber-100 text-amber-600">
                      <AlertCircle size={14} />
                    </div>
                  ))}
                </td>
                <td className="px-6 py-4">
                  <input
                    type="text" value={row.name}
                    className="w-full bg-transparent outline-none text-sm font-semibold"
                    onChange={(e) => updateRow(row.id, 'name', e.target.value)}
                  />
                </td>
                <td className="px-6 py-4">
                  <input
                    type="text" value={row.codigo || ''}
                    placeholder="—"
                    className="w-24 bg-blue-50/50 border border-slate-200 rounded px-2 py-1 text-xs font-mono font-bold text-blue-700 outline-none focus:ring-2 focus:ring-blue-500"
                    onChange={(e) => updateRow(row.id, 'codigo', e.target.value)}
                  />
                </td>
                <td className="px-6 py-4">
                  <select
                    className="w-full bg-slate-100/50 border border-slate-200 rounded-lg pl-2 pr-7 py-1.5 text-xs outline-none focus:ring-2 focus:ring-blue-500 truncate"
                    value={row.matchedId || ''}
                    onChange={(e) => {
                      const id = parseInt(e.target.value)
                      updateRow(row.id, 'matchedId', id || null)
                      // Preenche o código visível com o código do produto, se houver
                      const match = produtos.find(p => p.id === id)
                      if (match && match.codigo && !row.codigo) {
                        updateRow(row.id, 'codigo', match.codigo)
                      }
                    }}
                  >
                    <option value="">— novo item —</option>
                    {produtos.map(p => (
                      <option key={p.id} value={p.id}>{p.nome}{p.codigo ? ` [${p.codigo}]` : ''}</option>
                    ))}
                  </select>
                </td>
                <td className="px-6 py-4">
                  <select 
                    className={`w-full border rounded-lg px-2 py-1.5 text-xs outline-none focus:ring-2 focus:ring-blue-500 ${row.cidade ? 'bg-white border-slate-200' : 'bg-rose-50 border-rose-200 text-rose-600'}`}
                    value={row.cidade || ''}
                    onChange={(e) => updateRow(row.id, 'cidade', e.target.value)}
                  >
                    <option value="">(Selecione)</option>
                    {CIDADES.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </td>
                <td className="px-6 py-4">
                  <input type="text" value={row.qtd} className="w-16 mx-auto bg-slate-50 rounded px-1 py-1 text-sm text-center" onChange={(e) => updateRow(row.id, 'qtd', e.target.value)} />
                </td>
                <td className="px-6 py-4">
                  <input type="text" value={row.peso} className="w-20 mx-auto bg-slate-50 rounded px-1 py-1 text-sm font-black text-center" onChange={(e) => updateRow(row.id, 'peso', e.target.value)} />
                </td>
                <td className="px-6 py-4">
                  <input type="text" value={row.vl_fp} className="w-20 mx-auto bg-blue-50 rounded px-1 py-1 text-sm font-black text-blue-700 text-center" onChange={(e) => updateRow(row.id, 'vl_fp', e.target.value)} />
                </td>
                <td className="px-6 py-4">
                  <select 
                    className={`w-full border rounded-lg px-2 py-1.5 text-xs outline-none focus:ring-2 focus:ring-blue-500 ${row.grupo_id ? 'bg-white border-slate-200' : 'bg-rose-50 border-rose-200 text-rose-600'}`}
                    value={row.grupo_id || ''}
                    onChange={(e) => updateRow(row.id, 'grupo_id', parseInt(e.target.value))}
                  >
                    <option value="">(Obrigatório)</option>
                    {grupos.map(g => (
                      <option key={g.id} value={g.id}>{g.nome}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="p-4 bg-slate-50 border-t flex justify-center">
            <button 
              onClick={() => setRows([...rows, { id: Math.random(), matchedId: null, codigo: '', name: '', cidade: '', qtd: '', peso: '', vl_fp: '', grupo_id: null }])}
              className="text-[10px] font-black text-slate-400 hover:text-blue-600 uppercase tracking-widest"
            >
              + Adicionar Linha Manual
            </button>
        </div>
      </div>
    </div>
  )
}

// Heuristica: SKU 'AUTO-*' eh assinatura de cadastro automatico (criado pelo
// passo de produtos faltantes ou pelo flow legado de auto-import). Backend
// nao expoe created_at/updated_at, entao usamos a marca do SKU como proxy
// pra "produto criado pela importacao, ainda nao revisado". Funciona ate o
// momento em que o usuario edita e troca o SKU manualmente — a partir dai
// some da lista de "recentes", o que eh exatamente o comportamento desejado.
function ehProdutoRecemImportado(p: Produto): boolean {
  return !!p.sku && p.sku.startsWith('AUTO-')
}

// Normalizacao basica para matching textual fuzzy (acento + caso). Variante
// local do `normalizarChave` que vive perto do ImportCSVModal — duplica em
// vez de mover pra cima pra evitar ricochete em codigo nao-relacionado.
function normalizarTexto(s: string): string {
  return (s || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
}

// Mapa keyword -> nome canonico de grupo. As keys batem contra os nomes
// reais cadastrados em `/grupos` (case-insensitive). Lista intencional-
// mente curta — vale mais sugerir nada do que sugerir errado e treinar
// o usuario a desconfiar. Quando crescer, virar config persistida.
const PALAVRAS_CHAVE_GRUPO: Record<string, string[]> = {
  TEMPEROS: [
    'acafrao', 'oregano', 'pimenta', 'paprica', 'chimichurri',
    'corante', 'tempero', 'lemon pepper', 'edu guedes', 'cominho',
    'coentro', 'colorau', 'cravo', 'canela', 'curry',
    'manjericao', 'noz moscada', 'gengibre', 'salsa', 'cebolinha',
  ],
  ALIMENTICIOS: [
    'cebola', 'manga', 'abobora', 'tomate', 'batata',
    'cenoura', 'beterraba', 'pera', 'maca', 'banana',
    'mamao', 'melancia', 'melao', 'laranja', 'limao',
    'abacaxi', 'frutas', 'legumes', 'hortifruti', 'verdura',
  ],
  EMBALAGENS: [
    'saco', 'caixa', 'embalagem', 'plastico', 'papel',
    'sacola', 'pote', 'bandeja', 'filme pvc',
  ],
  CEREAIS: [
    'arroz', 'feijao', 'milho', 'farinha', 'aveia',
    'macarrao', 'lentilha', 'soja', 'trigo', 'granola',
  ],
}

// Sugere id de grupo baseado em keywords no nome. Retorna null se nada
// bater — UI deve mostrar a sugestao como "leve" (botao opcional, nunca
// auto-aplicado), conforme o spec do usuario.
function sugerirGrupoPorNome(nome: string, grupos: Grupo[]): number | null {
  if (!nome) return null
  const norm = normalizarTexto(nome)
  for (const grupo of grupos) {
    const kws = PALAVRAS_CHAVE_GRUPO[grupo.nome.toUpperCase()] || []
    if (kws.some(kw => norm.includes(kw))) return grupo.id
  }
  return null
}

type PendenciaTipo = 'grupo_padrao' | 'sem_codigo' | 'nome_curto' | 'margem_suspeita' | 'custo_zero'

const PENDENCIA_LABEL: Record<PendenciaTipo, { texto: string; cor: string; tooltip: string }> = {
  grupo_padrao: {
    texto: 'no grupo padrão',
    cor: 'bg-rose-50 text-rose-700 border border-rose-200',
    tooltip: 'No grupo padrão (default da importação) — categorize para ABC/XYZ refletir bem',
  },
  sem_codigo: {
    texto: 'sem código ERP',
    cor: 'bg-slate-100 text-slate-700 border border-slate-200',
    tooltip: 'Sem código — não fará match automático na próxima importação do CSV',
  },
  nome_curto: {
    texto: 'nome curto',
    cor: 'bg-amber-50 text-amber-700 border border-amber-200',
    tooltip: 'Nome com menos de 4 caracteres — provavelmente abreviação ou rascunho',
  },
  margem_suspeita: {
    texto: 'margem aparenta fórmula',
    cor: 'bg-amber-50 text-amber-700 border border-amber-200',
    tooltip: 'Margem entre 34,5% e 35,5% — sinal de custo derivado de regra fixa, não custo real',
  },
  custo_zero: {
    texto: 'custo zerado',
    cor: 'bg-rose-100 text-rose-800 border border-rose-300',
    tooltip: 'Custo zero — vai inflar a margem para 100% e poluir todas as análises',
  },
}

// Detecta pendencias de qualidade no produto. Cada tipo eh um sinal
// independente; o "score" eh apenas a contagem (.length da lista).
// Heuristicas conservadoras — preferem falso-negativo a falso-positivo.
function pendenciasProduto(p: Produto, grupoDefaultId: number | undefined): PendenciaTipo[] {
  const pendencias: PendenciaTipo[] = []
  if (grupoDefaultId != null && p.grupo_id === grupoDefaultId) pendencias.push('grupo_padrao')
  if (!p.codigo) pendencias.push('sem_codigo')
  if (p.nome.length < 4) pendencias.push('nome_curto')
  if (p.custo <= 0) {
    pendencias.push('custo_zero')
  } else if (Math.abs(p.margem - 0.35) < 0.005) {
    // 35,0% +/- 0,5% — assinatura de custo = preco * 0.65 da simulacao.
    // Se o usuario informou custo de fato 35%, conviver com falso positivo
    // eh aceitavel (custa 1 clique pra dispensar abrindo a edicao).
    pendencias.push('margem_suspeita')
  }
  return pendencias
}

// Edicao local em buffer — usada na vista de revisao para acumular
// alteracoes antes do PATCH explicito.
type EdicaoLocal = {
  nome?: string
  codigo?: string | null
  grupo_id?: number | null
  custo?: number
  preco_venda?: number
}

type FiltroRapido = 'todos' | 'recentes' | 'sem_codigo' | 'sem_grupo'
type VistaProdutos = 'tabela' | 'revisao'

function ProdutosPage() {
  const [produtos, setProdutos] = useState<Produto[]>([])
  const [grupos, setGrupos] = useState<Grupo[]>([])
  const [editando, setEditando] = useState<any | null>(null)

  // Filtros operacionais — busca por texto, filtro por grupo cadastrado,
  // e atalhos rapidos (recentes/sem_codigo/sem_grupo) acessiveis tanto pelos
  // pills de saude quanto programaticamente.
  const [busca, setBusca] = useState('')
  const [grupoFiltro, setGrupoFiltro] = useState<'todos' | number>('todos')
  const [filtroRapido, setFiltroRapido] = useState<FiltroRapido>('todos')

  // Selecao em lote: Set<id> persiste entre re-renders e atravessa mudancas
  // de filtro (ids fora do filtro atual permanecem selecionados se voltarem
  // ao escopo). Modal bulkAcao controla qual lote aplicar.
  const [selecionados, setSelecionados] = useState<Set<number>>(new Set())
  const [bulkAcao, setBulkAcao] = useState<'grupo' | null>(null)

  // Vista da pagina: tabela (visao geral) vs revisao (fila assistida pra
  // produtos AUTO-* com cards inline editaveis). Persiste durante a sessao;
  // nao salva em localStorage pra evitar surpresa (volta sempre em 'tabela').
  const [vista, setVista] = useState<VistaProdutos>('tabela')

  // Edicoes locais nao-comitadas no modo revisao. Map<id, partial> com so
  // os campos que diferem do produto salvo. Salva eh per-card; campos voltam
  // ao original sao removidos do map automaticamente (via setEdicao).
  const [edicoesLocais, setEdicoesLocais] = useState<Record<number, EdicaoLocal>>({})
  const [salvandoId, setSalvandoId] = useState<number | null>(null)
  const [errosSave, setErrosSave] = useState<Record<number, string>>({})

  const carregar = () => {
    axios.get(`${API_URL}/produtos`).then(res => setProdutos(res.data))
  }

  useEffect(() => {
    carregar()
    axios.get(`${API_URL}/grupos`).then(res => setGrupos(res.data))
  }, [])

  // Heuristica de "grupo padrao": primeiro id da lista de grupos. Funciona
  // porque o cadastro automatico sempre cai no menor id (ALIMENTICIOS=1 no
  // setup de homologacao). Se o backend mudar isso, basta ajustar aqui.
  const grupoDefaultId = grupos[0]?.id

  // Agregados pre-filtro — alimenta os pills de saude e nao reflete os
  // filtros atuais (por design, o painel mostra a saude TOTAL do catalogo).
  const recemImportados = produtos.filter(ehProdutoRecemImportado).length
  const semCodigo = produtos.filter(p => !p.codigo).length
  const noGrupoDefault = grupoDefaultId != null
    ? produtos.filter(p => p.grupo_id === grupoDefaultId).length
    : 0

  // Aplica filtros — derived state, sem useMemo (lista pequena, custo zero).
  const produtosFiltrados = produtos.filter(p => {
    if (busca) {
      const q = busca.toLowerCase().trim()
      const nomeMatch = p.nome.toLowerCase().includes(q)
      const codMatch = !!p.codigo && p.codigo.toLowerCase().includes(q)
      if (!nomeMatch && !codMatch) return false
    }
    if (grupoFiltro !== 'todos' && p.grupo_id !== grupoFiltro) return false
    if (filtroRapido === 'recentes' && !ehProdutoRecemImportado(p)) return false
    if (filtroRapido === 'sem_codigo' && !!p.codigo) return false
    if (filtroRapido === 'sem_grupo') {
      if (grupoDefaultId == null || p.grupo_id !== grupoDefaultId) return false
    }
    return true
  })

  // Selecao "todos" opera sobre o que o usuario VE — ids fora do filtro nao
  // sao tocados. Vacuous truth no caso vazio: guard evita "all selected"
  // quando a lista filtrada eh zero.
  const todosVisiveisSelecionados = produtosFiltrados.length > 0
    && produtosFiltrados.every(p => selecionados.has(p.id))
  const toggleTodosVisiveis = () => {
    setSelecionados(prev => {
      const novo = new Set(prev)
      if (todosVisiveisSelecionados) {
        produtosFiltrados.forEach(p => novo.delete(p.id))
      } else {
        produtosFiltrados.forEach(p => novo.add(p.id))
      }
      return novo
    })
  }
  const toggleUm = (id: number) => {
    setSelecionados(prev => {
      const novo = new Set(prev)
      if (novo.has(id)) novo.delete(id)
      else novo.add(id)
      return novo
    })
  }
  const limparSelecao = () => setSelecionados(new Set())

  const aplicarFiltroRapido = (f: FiltroRapido) => {
    // Toggle: clicar 2x no mesmo pill volta para 'todos'.
    setFiltroRapido(prev => (prev === f ? 'todos' : f))
  }

  // Atualiza edicoes locais. Auto-limpa campos que voltaram pro valor
  // original (evita "salvar" virar no-op se o usuario digitou e desfez).
  const atualizarEdicao = (id: number, patch: EdicaoLocal) => {
    setEdicoesLocais(prev => {
      const original = produtos.find(p => p.id === id)
      const atual = prev[id] || {}
      const merged: EdicaoLocal = { ...atual, ...patch }
      if (original) {
        const efetivo: EdicaoLocal = {}
        const campos: Array<keyof EdicaoLocal> = ['nome', 'codigo', 'grupo_id', 'custo', 'preco_venda']
        for (const k of campos) {
          if (merged[k] === undefined) continue
          // Compara como string pra ignorar tipos diferentes (null vs '')
          const novoVal = merged[k] === '' ? null : merged[k]
          const origVal = (original as any)[k]
          if (novoVal !== origVal) (efetivo as any)[k] = novoVal
        }
        const novo = { ...prev }
        if (Object.keys(efetivo).length === 0) {
          delete novo[id]
        } else {
          novo[id] = efetivo
        }
        return novo
      }
      return { ...prev, [id]: merged }
    })
    // Limpa erro previo do mesmo id ao retomar edicao.
    setErrosSave(prev => {
      if (!prev[id]) return prev
      const novo = { ...prev }
      delete novo[id]
      return novo
    })
  }

  // Salva uma edicao via PATCH parcial. Sucesso limpa edicoesLocais e
  // refresca a lista (margem recomputa server-side). Falha mostra erro
  // inline preservando o buffer pra o usuario corrigir/retentar.
  const salvarEdicao = async (id: number) => {
    const edits = edicoesLocais[id]
    if (!edits || Object.keys(edits).length === 0) return
    setSalvandoId(id)
    try {
      await axios.patch(`${API_URL}/produtos/${id}`, edits)
      setEdicoesLocais(prev => {
        const novo = { ...prev }
        delete novo[id]
        return novo
      })
      carregar()
    } catch (e: any) {
      setErrosSave(prev => ({
        ...prev,
        [id]: e?.response?.data?.detail || 'Erro ao salvar.',
      }))
    } finally {
      setSalvandoId(null)
    }
  }

  // Lista da vista de revisao: AUTO-* (todo o universo de "criado pela
  // importacao"), ordenado por contagem de pendencias desc — quem tem
  // mais sinais de problema fica no topo da fila. Filtros texto/grupo
  // tambem se aplicam pra deixar a fila navegavel quando crescer.
  const produtosRevisao = produtos
    .filter(ehProdutoRecemImportado)
    .filter(p => {
      if (busca) {
        const q = busca.toLowerCase().trim()
        const nomeMatch = p.nome.toLowerCase().includes(q)
        const codMatch = !!p.codigo && p.codigo.toLowerCase().includes(q)
        if (!nomeMatch && !codMatch) return false
      }
      if (grupoFiltro !== 'todos' && p.grupo_id !== grupoFiltro) return false
      return true
    })
    .sort((a, b) => {
      const pa = pendenciasProduto(a, grupoDefaultId).length
      const pb = pendenciasProduto(b, grupoDefaultId).length
      return pb - pa
    })

  // Contagem do badge da tab — produtos AUTO-* COM ao menos 1 pendencia.
  // Quando zera, a tab continua disponivel mas sem badge (fila vazia).
  const autosPendentesTotal = produtos.filter(p =>
    ehProdutoRecemImportado(p)
    && pendenciasProduto(p, grupoDefaultId).length > 0
  ).length

  return (
    <div className="max-w-6xl mx-auto p-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="headline text-4xl tracking-editorial">Gestão de SKUs</h2>
        <p className="text-xs text-slate-500">
          {vista === 'revisao'
            ? `${produtosRevisao.length} na fila de revisão`
            : produtosFiltrados.length === produtos.length
              ? `${produtos.length} SKU${produtos.length === 1 ? '' : 's'}`
              : `${produtosFiltrados.length} de ${produtos.length} SKUs`}
        </p>
      </div>

      {/* Tabs: tabela completa vs fila de revisao assistida */}
      {produtos.length > 0 && (
        <div className="flex items-center gap-1 mb-4 border-b border-slate-200">
          <button
            onClick={() => setVista('tabela')}
            className={`px-4 py-2 text-sm font-semibold transition-colors border-b-2 -mb-px ${
              vista === 'tabela'
                ? 'text-blue-600 border-blue-600'
                : 'text-slate-500 hover:text-slate-700 border-transparent'
            }`}
          >
            Tabela completa
          </button>
          <button
            onClick={() => setVista('revisao')}
            className={`px-4 py-2 text-sm font-semibold transition-colors border-b-2 -mb-px flex items-center gap-2 ${
              vista === 'revisao'
                ? 'text-blue-600 border-blue-600'
                : 'text-slate-500 hover:text-slate-700 border-transparent'
            }`}
            title="Fila assistida para revisar SKUs criados pela importação — edição inline com sugestão de grupo e detecção de pendências"
          >
            <span>Revisar autos</span>
            {autosPendentesTotal > 0 && (
              <span className={`text-[10px] font-black px-1.5 py-0.5 rounded-full ${
                vista === 'revisao' ? 'bg-blue-600 text-white' : 'bg-amber-500 text-white'
              }`}>
                {autosPendentesTotal}
              </span>
            )}
          </button>
        </div>
      )}

      {/* Saude do catalogo — pills clicaveis aplicam filtro rapido. So aparece
          em vista tabela; na vista revisao a propria fila ja eh o "painel de
          pendencias" com mais detalhe. */}
      {vista === 'tabela' && produtos.length > 0 && (recemImportados > 0 || semCodigo > 0 || noGrupoDefault > 0) && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          {recemImportados > 0 && (
            <button
              onClick={() => aplicarFiltroRapido('recentes')}
              className={`text-xs px-3 py-1.5 rounded-full font-semibold transition-colors ${
                filtroRapido === 'recentes'
                  ? 'bg-amber-600 text-white'
                  : 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200'
              }`}
              title="Produtos cadastrados pelo passo de importação — convém revisar grupo, custo e nome"
            >
              {recemImportados} criado{recemImportados === 1 ? '' : 's'} pela importação
            </button>
          )}
          {grupoDefaultId != null && noGrupoDefault > 0 && (
            <button
              onClick={() => aplicarFiltroRapido('sem_grupo')}
              className={`text-xs px-3 py-1.5 rounded-full font-semibold transition-colors ${
                filtroRapido === 'sem_grupo'
                  ? 'bg-rose-600 text-white'
                  : 'bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200'
              }`}
              title="Produtos no grupo padrão — categorize para análises ABC/XYZ ficarem corretas"
            >
              {noGrupoDefault} no grupo padrão "{grupos[0]?.nome}"
            </button>
          )}
          {semCodigo > 0 && (
            <button
              onClick={() => aplicarFiltroRapido('sem_codigo')}
              className={`text-xs px-3 py-1.5 rounded-full font-semibold transition-colors ${
                filtroRapido === 'sem_codigo'
                  ? 'bg-slate-700 text-white'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300'
              }`}
              title="Sem código ERP — não vão fazer match automático na próxima importação"
            >
              {semCodigo} sem código ERP
            </button>
          )}
        </div>
      )}

      {/* Toolbar de busca + filtro por grupo */}
      {produtos.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <input
            type="text"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por nome ou código…"
            className="flex-1 min-w-[200px] px-3 py-2 rounded-lg border border-slate-200 text-sm focus:ring-2 focus:ring-blue-500 outline-none bg-white"
          />
          <select
            value={grupoFiltro === 'todos' ? '' : String(grupoFiltro)}
            onChange={(e) => setGrupoFiltro(e.target.value ? parseInt(e.target.value) : 'todos')}
            className="px-3 py-2 rounded-lg border border-slate-200 text-sm bg-white focus:ring-2 focus:ring-blue-500 outline-none"
          >
            <option value="">Todos os grupos</option>
            {grupos.map(g => (
              <option key={g.id} value={g.id}>{g.nome}</option>
            ))}
          </select>
          {(busca || grupoFiltro !== 'todos' || filtroRapido !== 'todos') && (
            <button
              onClick={() => { setBusca(''); setGrupoFiltro('todos'); setFiltroRapido('todos') }}
              className="text-xs text-slate-500 hover:text-slate-900 px-2 py-2"
            >
              Limpar filtros
            </button>
          )}
        </div>
      )}

      {/* Barra contextual de selecao em lote — so vale na vista tabela */}
      {vista === 'tabela' && selecionados.size > 0 && (
        <div className="flex flex-wrap items-center gap-3 mb-4 px-4 py-2.5 bg-blue-50 border border-blue-200 rounded-xl">
          <span className="text-sm font-bold text-blue-900">
            {selecionados.size} selecionado{selecionados.size === 1 ? '' : 's'}
          </span>
          <button
            onClick={() => setBulkAcao('grupo')}
            className="text-xs font-bold bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Mover para grupo…
          </button>
          <button
            onClick={limparSelecao}
            className="ml-auto text-xs text-blue-700 hover:underline"
          >
            Limpar seleção
          </button>
        </div>
      )}

      {/* VISTA REVISAO: stack vertical de cards inline-editaveis */}
      {vista === 'revisao' && (
        <div className="space-y-3">
          {produtosRevisao.length > 0 ? (
            <>
              {autosPendentesTotal === 0 && (
                <div className="px-4 py-3 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-800">
                  <strong>Fila zerada.</strong> Nenhum SKU recém-importado tem pendência detectável. Os cards abaixo continuam visíveis para edição rápida.
                </div>
              )}
              {produtosRevisao.map(p => (
                <RevisaoCard
                  key={p.id}
                  produto={p}
                  grupos={grupos}
                  grupoDefaultId={grupoDefaultId}
                  edicao={edicoesLocais[p.id]}
                  onChange={atualizarEdicao}
                  onSalvar={salvarEdicao}
                  salvando={salvandoId === p.id}
                  erro={errosSave[p.id]}
                />
              ))}
            </>
          ) : (
            <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-8">
              <EmptyState
                variant="empty"
                compact
                icon={<Package size={28} />}
                title={produtos.filter(ehProdutoRecemImportado).length === 0
                  ? 'Nenhum SKU recém-importado. Cadastros novos aparecem aqui após o commit do CSV.'
                  : 'Nenhum SKU bate com os filtros aplicados.'}
              />
            </div>
          )}
        </div>
      )}

      {/* VISTA TABELA: tabela completa (default) */}
      {vista === 'tabela' && (
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-4 py-4 w-10">
                <input
                  type="checkbox"
                  checked={todosVisiveisSelecionados}
                  onChange={toggleTodosVisiveis}
                  disabled={produtosFiltrados.length === 0}
                  className="accent-blue-600 cursor-pointer disabled:opacity-30"
                  aria-label="Selecionar todos visíveis"
                />
              </th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Produto</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Código</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Grupo</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Custo Médio</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Margem</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Estoque</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {produtosFiltrados.length > 0 ? produtosFiltrados.map(p => {
              const grupoNome = grupos.find(g => g.id === p.grupo_id)?.nome
              const recemImp = ehProdutoRecemImportado(p)
              const noDefault = grupoDefaultId != null && p.grupo_id === grupoDefaultId
              return (
                <tr key={p.id} className={`hover:bg-slate-50/50 transition-colors ${
                  selecionados.has(p.id) ? 'bg-blue-50/40' : ''
                }`}>
                  <td className="px-4 py-4">
                    <input
                      type="checkbox"
                      checked={selecionados.has(p.id)}
                      onChange={() => toggleUm(p.id)}
                      className="accent-blue-600 cursor-pointer"
                      aria-label={`Selecionar ${p.nome}`}
                    />
                  </td>
                  <td className="px-6 py-4 text-sm font-bold text-slate-900">
                    <span className="flex items-center gap-1.5 flex-wrap">
                      {p.nome}
                      {recemImp && (
                        <span
                          title="Cadastrado pela importação do CSV — convém revisar grupo e custo"
                          className="text-[9px] font-black tracking-widest uppercase px-1.5 py-0.5 rounded bg-amber-100 text-amber-700"
                        >
                          Auto
                        </span>
                      )}
                      {p.bloqueado_engine && (
                        <span title="Excluído do Engine de Promoção (blacklist)" className="inline-flex items-center text-rose-500">
                          <Lock size={12} />
                        </span>
                      )}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-xs font-mono">
                    {p.codigo
                      ? <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 font-bold tracking-wider">{p.codigo}</span>
                      : <span className="text-slate-300 italic">—</span>}
                  </td>
                  <td className="px-6 py-4 text-xs">
                    {grupoNome
                      ? <span className={`px-2 py-0.5 rounded font-semibold ${
                          noDefault
                            ? 'bg-slate-100 text-slate-500 italic'
                            : 'bg-slate-50 text-slate-700'
                        }`}>{grupoNome}</span>
                      : <span className="text-slate-300 italic">— sem grupo —</span>}
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600 text-center">{formatCurrency(p.custo)}</td>
                  <td className="px-6 py-4 text-center">
                    <span className={`px-2 py-1 rounded-full text-[10px] font-black ${
                      p.margem >= 0.17 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                    }`}>{formatPercent(p.margem)}</span>
                  </td>
                  <td className="px-6 py-4 text-sm text-center font-extrabold text-slate-500">
                    {formatNumber(p.estoque_qtd || 0, { maximumFractionDigits: 0 })}
                    <span className="text-[10px] text-slate-400 ml-1">UN</span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={() => setEditando(p)}
                      className="text-xs font-bold text-blue-600 hover:text-blue-700 hover:underline"
                    >
                      Editar
                    </button>
                  </td>
                </tr>
              )
            }) : (
              <tr>
                <td colSpan={8} className="px-6 py-8">
                  <EmptyState
                    variant="empty"
                    compact
                    icon={<Package size={28} />}
                    title={produtos.length === 0
                      ? 'Nenhum item em estoque. Comece fazendo uma Entrada de Compra.'
                      : 'Nenhum SKU bate com os filtros aplicados.'}
                  />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      )}

      {editando && (
        <ProdutoEditModal
          produto={editando}
          grupos={grupos}
          onClose={() => setEditando(null)}
          onSaved={() => { setEditando(null); carregar(); }}
        />
      )}

      {bulkAcao === 'grupo' && (
        <BulkGrupoModal
          produtosSelecionados={produtos.filter(p => selecionados.has(p.id))}
          grupos={grupos}
          onClose={() => setBulkAcao(null)}
          onApplied={() => {
            setBulkAcao(null)
            limparSelecao()
            carregar()
          }}
        />
      )}
    </div>
  )
}

function ProdutoEditModal({ produto, grupos, onClose, onSaved }: any) {
  const [nome, setNome] = useState(produto.nome || '')
  const [codigo, setCodigo] = useState(produto.codigo || '')
  const [grupoId, setGrupoId] = useState<number | null>(produto.grupo_id || null)
  const [custo, setCusto] = useState(String(produto.custo ?? ''))
  const [precoVenda, setPrecoVenda] = useState(String(produto.preco_venda ?? ''))
  const [bloqueadoEngine, setBloqueadoEngine] = useState<boolean>(!!produto.bloqueado_engine)
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const titleId = 'produto-edit-title'

  // ESC fecha (mesmo padrao dos outros modais), exceto durante o save assincrono
  useEscapeKey(onClose, { disabled: salvando })
  // Foco entra no modal ao abrir; trap em Tab/Shift+Tab; restaura no unmount.
  useModalA11y(containerRef)

  const salvar = async () => {
    setErro(null)
    setSalvando(true)
    try {
      const payload: any = {
        nome: nome.trim() || undefined,
        codigo: codigo,   // string vazia é aceita: backend normaliza pra NULL
        grupo_id: grupoId,
        custo: parseFloat(custo.replace(',', '.')) || 0,
        preco_venda: parseFloat(precoVenda.replace(',', '.')) || 0,
        bloqueado_engine: bloqueadoEngine,
      }
      await axios.patch(`${API_URL}/produtos/${produto.id}`, payload)
      onSaved()
    } catch (e: any) {
      setErro(e?.response?.data?.detail || 'Erro ao salvar.')
    } finally {
      setSalvando(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-6"
      onClick={() => !salvando && onClose()}
    >
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="bg-white rounded-3xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <div>
            <p className="section-label">SKU {produto.sku}</p>
            <h3 id={titleId} className="headline text-2xl tracking-editorial">Editar produto</h3>
          </div>
          <button
            onClick={onClose}
            disabled={salvando}
            className="text-slate-400 hover:text-slate-700 p-1 disabled:opacity-50"
            title="Fechar (ESC)"
            aria-label="Fechar"
          >
            <X size={20} />
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Nome</label>
            <input
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              className="w-full mt-1 p-2.5 rounded-lg border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none text-sm"
            />
          </div>

          <div>
            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">
              Código ERP <span className="text-blue-600 normal-case font-semibold">(usado no matching do CSV)</span>
            </label>
            <input
              type="text"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
              placeholder="ex.: 1234, CORANT01, etc."
              className="w-full mt-1 p-2.5 rounded-lg border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none font-mono text-sm"
            />
            <p className="text-[11px] text-slate-500 mt-1">Deixe vazio para não usar código. Deve ser único no sistema.</p>
          </div>

          <div>
            <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Grupo</label>
            <select
              value={grupoId ?? ''}
              onChange={(e) => setGrupoId(e.target.value ? parseInt(e.target.value) : null)}
              className="w-full mt-1 p-2.5 rounded-lg border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none text-sm bg-white"
            >
              <option value="">— sem grupo —</option>
              {grupos.map((g: any) => (
                <option key={g.id} value={g.id}>{g.nome}</option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Custo (R$)</label>
              <input
                type="text"
                value={custo}
                onChange={(e) => setCusto(e.target.value)}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none text-sm"
              />
            </div>
            <div>
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Preço Venda (R$)</label>
              <input
                type="text"
                value={precoVenda}
                onChange={(e) => setPrecoVenda(e.target.value)}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none text-sm"
              />
            </div>
          </div>

          {/* Blacklist do Engine de Promoção */}
          <div className="p-3 rounded-lg border border-slate-200 bg-slate-50">
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={bloqueadoEngine}
                onChange={(e) => setBloqueadoEngine(e.target.checked)}
                className="mt-0.5 accent-rose-600 cursor-pointer"
              />
              <div className="flex-1">
                <p className="text-sm font-bold text-slate-900 flex items-center gap-1.5">
                  <Lock size={13} className="text-rose-600" /> Excluir do Engine de Promoção
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5 leading-tight">
                  Quando marcado, o solver de "Promo Inteligente" nunca vai propor este SKU em promoção. Útil para loss-leaders, contratos com fornecedor ou produtos com margem já gerenciada.
                </p>
              </div>
            </label>
          </div>
        </div>

        {erro && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-sm text-rose-700">
            {erro}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900"
          >
            Cancelar
          </button>
          <button
            onClick={salvar}
            disabled={salvando}
            className="bg-blue-600 text-white px-5 py-2 rounded-xl font-bold text-sm hover:bg-blue-700 disabled:opacity-50 transition-all"
          >
            {salvando ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  )
}

// Modal de edicao em lote — focada em "mover de grupo", o caso mais comum
// pos-importacao (todos os produtos novos caem no grupo padrao). Aplicacao
// eh sequencial (PATCH 1 por 1) com barra de progresso; falhas individuais
// nao abortam o lote, ficam visiveis pra revisao manual.
function BulkGrupoModal({ produtosSelecionados, grupos, onClose, onApplied }: any) {
  const [grupoId, setGrupoId] = useState<number | null>(null)
  const [salvando, setSalvando] = useState(false)
  const [progresso, setProgresso] = useState({ feitos: 0, total: 0 })
  const [falhas, setFalhas] = useState<Array<{ id: number; nome: string; erro: string }>>([])
  const containerRef = useRef<HTMLDivElement>(null)
  const titleId = 'bulk-grupo-title'

  // Mantem o mesmo padrao dos outros modais (ESC fecha, foco trap, restaura).
  useEscapeKey(onClose, { disabled: salvando })
  useModalA11y(containerRef)

  const aplicar = async () => {
    if (!grupoId) return
    setSalvando(true)
    setProgresso({ feitos: 0, total: produtosSelecionados.length })
    setFalhas([])
    for (const p of produtosSelecionados) {
      let falha: { id: number; nome: string; erro: string } | null = null
      try {
        await axios.patch(`${API_URL}/produtos/${p.id}`, { grupo_id: grupoId })
      } catch (e: any) {
        falha = {
          id: p.id,
          nome: p.nome,
          erro: e?.response?.data?.detail || 'Erro de rede',
        }
      }
      setProgresso(prev => ({ ...prev, feitos: prev.feitos + 1 }))
      if (falha) setFalhas(prev => [...prev, falha!])
    }
    setSalvando(false)
    // Sucesso total: fecha modal e refresca lista. Com falhas: mantem aberto
    // para o usuario ver os ids problematicos antes de retomar.
    setTimeout(() => {
      // checa state mais recente; usar setFalhas com callback nao funciona
      // aqui porque precisamos do array final pos-loop.
      // Em vez disso, lemos via closure: se o ultimo item nao deu falha
      // E nenhuma falha foi acumulada, fecha.
    }, 0)
  }

  // Fecha automaticamente quando termina sem erros — efeito reativo ao
  // termino do loop (salvando passa a false e falhas continua vazio).
  useEffect(() => {
    if (!salvando && progresso.feitos > 0 && progresso.feitos === progresso.total && falhas.length === 0) {
      onApplied()
    }
  }, [salvando, progresso.feitos, progresso.total, falhas.length, onApplied])

  const grupoSelecionadoNome = grupos.find((g: any) => g.id === grupoId)?.nome

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-6"
      onClick={() => !salvando && onClose()}
    >
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="bg-white rounded-3xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between">
          <div>
            <p className="section-label">Edição em lote</p>
            <h3 id={titleId} className="headline text-2xl tracking-editorial">Mover para grupo</h3>
            <p className="text-xs text-slate-500 mt-1">
              {produtosSelecionados.length} produto{produtosSelecionados.length === 1 ? '' : 's'} ser{produtosSelecionados.length === 1 ? 'á' : 'ão'} movido{produtosSelecionados.length === 1 ? '' : 's'}.
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={salvando}
            className="text-slate-400 hover:text-slate-700 p-1 disabled:opacity-50"
            title="Fechar (ESC)"
            aria-label="Fechar"
          >
            <X size={20} />
          </button>
        </div>

        {progresso.total === 0 && (
          <div className="space-y-3">
            <div>
              <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Grupo de destino</label>
              <select
                value={grupoId ?? ''}
                onChange={(e) => setGrupoId(e.target.value ? parseInt(e.target.value) : null)}
                className="w-full mt-1 p-2.5 rounded-lg border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none text-sm bg-white"
              >
                <option value="">— selecione —</option>
                {grupos.map((g: any) => (
                  <option key={g.id} value={g.id}>{g.nome}</option>
                ))}
              </select>
            </div>
            <div className="max-h-48 overflow-y-auto bg-slate-50 rounded-lg p-3 border border-slate-200">
              <ul className="space-y-1 text-xs">
                {produtosSelecionados.map((p: any) => (
                  <li key={p.id} className="flex items-center justify-between gap-2">
                    <span className="font-semibold text-slate-700 truncate">{p.nome}</span>
                    <span className="text-slate-400 font-mono shrink-0">{p.codigo || '—'}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {progresso.total > 0 && (
          <div className="space-y-2">
            <p className="text-sm text-slate-700">
              {salvando
                ? <>Aplicando <strong>{progresso.feitos}/{progresso.total}</strong>…</>
                : <>Concluído: <strong>{progresso.feitos - falhas.length}/{progresso.total}</strong> aplicados{falhas.length > 0 ? <>, <span className="text-rose-700 font-bold">{falhas.length} falha{falhas.length === 1 ? '' : 's'}</span></> : ''}.</>}
              {grupoSelecionadoNome && <> Grupo: <strong>{grupoSelecionadoNome}</strong>.</>}
            </p>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all"
                style={{ width: `${progresso.total > 0 ? (progresso.feitos / progresso.total) * 100 : 0}%` }}
              />
            </div>
          </div>
        )}

        {!salvando && falhas.length > 0 && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-lg space-y-1">
            <p className="text-sm font-bold text-rose-700">
              {falhas.length} produto{falhas.length === 1 ? '' : 's'} com erro:
            </p>
            <ul className="text-xs text-rose-700 space-y-0.5 max-h-32 overflow-y-auto">
              {falhas.map((f, i) => (
                <li key={i} className="font-mono">• {f.nome} (id {f.id}): {f.erro}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onClose}
            disabled={salvando}
            className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900 disabled:opacity-50"
          >
            {progresso.total > 0 && !salvando ? 'Fechar' : 'Cancelar'}
          </button>
          {progresso.total === 0 && (
            <button
              onClick={aplicar}
              disabled={!grupoId}
              className="bg-blue-600 text-white px-5 py-2 rounded-xl font-bold text-sm hover:bg-blue-700 disabled:opacity-50 transition-all"
            >
              Aplicar
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

// Card inline-editavel da fila de revisao. Um card por produto AUTO-*,
// com 4 campos prioritarios + sugestao de grupo + tags de pendencia.
// Salvar dispara PATCH parcial e some quando o produto deixa de ter
// pendencia visivel (ainda persiste na fila se o usuario quiser revisar
// outras coisas, mas o card vira verde e desce no ranking).
function RevisaoCard({
  produto,
  grupos,
  grupoDefaultId,
  edicao,
  onChange,
  onSalvar,
  salvando,
  erro,
}: {
  produto: Produto
  grupos: Grupo[]
  grupoDefaultId: number | undefined
  edicao: EdicaoLocal | undefined
  onChange: (id: number, patch: EdicaoLocal) => void
  onSalvar: (id: number) => void
  salvando: boolean
  erro: string | undefined
}) {
  const temAlteracoes = !!edicao && Object.keys(edicao).length > 0

  // "Estado efetivo" para detecao de pendencias e calculo de margem:
  // mistura produto salvo com edicoes pendentes — assim as tags de
  // pendencia desaparecem em tempo real conforme o usuario corrige.
  const efetivo: Produto = {
    ...produto,
    ...(edicao?.nome != null ? { nome: edicao.nome } : {}),
    ...(edicao?.codigo !== undefined ? { codigo: edicao.codigo } : {}),
    ...(edicao?.grupo_id !== undefined ? { grupo_id: edicao.grupo_id ?? produto.grupo_id } : {}),
    ...(edicao?.custo != null ? { custo: edicao.custo } : {}),
    ...(edicao?.preco_venda != null ? { preco_venda: edicao.preco_venda } : {}),
  }
  // Recalcula margem com valores em buffer
  const margemEfetiva = efetivo.preco_venda > 0
    ? (efetivo.preco_venda - efetivo.custo) / efetivo.preco_venda
    : 0
  const efetivoComMargem = { ...efetivo, margem: margemEfetiva }

  const pendencias = pendenciasProduto(efetivoComMargem, grupoDefaultId)
  const sugestaoGrupoId = sugerirGrupoPorNome(efetivo.nome, grupos)
  const sugestaoNome = grupos.find(g => g.id === sugestaoGrupoId)?.nome
  const grupoAtualId = efetivo.grupo_id

  const set = (campo: keyof EdicaoLocal, valor: any) => {
    onChange(produto.id, { [campo]: valor })
  }

  // Cor de borda revela estado: verde se sem pendencias, amber se ha
  // alteracoes em buffer, slate se ainda esta intacto com pendencia.
  const borderColor = pendencias.length === 0
    ? 'border-emerald-200'
    : 'border-slate-200'
  const bgColor = pendencias.length === 0 ? 'bg-emerald-50/40' : 'bg-white'
  const ringColor = temAlteracoes ? 'ring-2 ring-amber-300' : ''

  return (
    <div className={`rounded-2xl border-2 p-4 transition-all ${borderColor} ${bgColor} ${ringColor}`}>
      {/* Header: nome editavel + badge + codigo inline */}
      <div className="flex items-start gap-2 mb-2">
        <input
          type="text"
          value={edicao?.nome ?? produto.nome}
          onChange={(e) => set('nome', e.target.value)}
          placeholder="Nome do produto"
          className="flex-1 text-base font-bold text-slate-900 border-b border-transparent hover:border-slate-200 focus:border-blue-500 outline-none bg-transparent px-1 py-0.5 transition-colors"
        />
        <span
          title="SKU AUTO — criado pela importação do CSV"
          className="text-[9px] font-black tracking-widest uppercase px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 shrink-0 mt-1"
        >
          Auto
        </span>
      </div>

      {/* Tags de pendencia — somem assim que o usuario corrige (efetivo recalculado) */}
      {pendencias.length > 0 ? (
        <div className="flex flex-wrap gap-1 mb-3">
          {pendencias.map(p => (
            <span
              key={p}
              title={PENDENCIA_LABEL[p].tooltip}
              className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${PENDENCIA_LABEL[p].cor}`}
            >
              {PENDENCIA_LABEL[p].texto}
            </span>
          ))}
        </div>
      ) : (
        <div className="mb-3">
          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 border border-emerald-200">
            ✓ sem pendências detectadas
          </span>
        </div>
      )}

      {/* Grid de campos — grupo, codigo, custo, preco */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div>
          <label className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Grupo</label>
          <select
            value={grupoAtualId ?? ''}
            onChange={(e) => set('grupo_id', e.target.value ? parseInt(e.target.value) : null)}
            className={`w-full mt-1 p-2 rounded border text-xs bg-white focus:ring-2 focus:ring-blue-500 outline-none ${
              grupoAtualId === grupoDefaultId
                ? 'border-rose-300'
                : 'border-slate-200'
            }`}
          >
            <option value="">— sem grupo —</option>
            {grupos.map(g => (
              <option key={g.id} value={g.id}>
                {g.nome}{g.id === sugestaoGrupoId ? ' ✨' : ''}
              </option>
            ))}
          </select>
          {sugestaoGrupoId != null && grupoAtualId !== sugestaoGrupoId && (
            <button
              type="button"
              onClick={() => set('grupo_id', sugestaoGrupoId)}
              className="mt-1 text-[10px] text-blue-600 hover:underline font-semibold"
              title="Sugestão automática baseada em palavras-chave do nome — clique para aplicar"
            >
              ✨ Sugerir: {sugestaoNome}
            </button>
          )}
        </div>
        <div>
          <label className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Código ERP</label>
          <input
            type="text"
            value={edicao?.codigo ?? produto.codigo ?? ''}
            onChange={(e) => set('codigo', e.target.value || null)}
            placeholder="(opcional)"
            className="w-full mt-1 p-2 rounded border border-slate-200 text-xs font-mono focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
        <div>
          <label className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Custo (R$)</label>
          <input
            type="number" step="0.01" min="0"
            value={edicao?.custo ?? produto.custo}
            onChange={(e) => set('custo', parseFloat(e.target.value) || 0)}
            className={`w-full mt-1 p-2 rounded border text-xs focus:ring-2 focus:ring-blue-500 outline-none ${
              efetivo.custo <= 0 ? 'border-rose-300 bg-rose-50/50' : 'border-slate-200'
            }`}
          />
        </div>
        <div>
          <label className="text-[9px] font-black text-slate-500 uppercase tracking-widest">Preço Venda (R$)</label>
          <input
            type="number" step="0.01"
            value={edicao?.preco_venda ?? produto.preco_venda}
            onChange={(e) => set('preco_venda', parseFloat(e.target.value) || 0)}
            className="w-full mt-1 p-2 rounded border border-slate-200 text-xs focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>
      </div>

      {/* Margem calculada + Salvar */}
      <div className="flex flex-wrap items-center justify-between gap-2 mt-3 pt-3 border-t border-slate-100">
        <div className="text-xs text-slate-500">
          Margem: <strong className={
            margemEfetiva >= 0.17 ? 'text-emerald-700' : 'text-amber-700'
          }>{formatPercent(margemEfetiva)}</strong>
          {temAlteracoes && (
            <span className="ml-2 text-[10px] text-amber-600 font-semibold">· alterações pendentes</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {erro && <span className="text-[10px] text-rose-600 font-semibold">{erro}</span>}
          <button
            disabled={!temAlteracoes || salvando}
            onClick={() => onSalvar(produto.id)}
            className="text-xs font-bold bg-blue-600 text-white px-3 py-1.5 rounded-lg hover:bg-blue-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            {salvando ? 'Salvando…' : 'Salvar alterações'}
          </button>
        </div>
      </div>
    </div>
  )
}

function ChatPage() {
  const [messages, setMessages] = useState<any[]>([
    { role: 'assistant', content: 'Olá! Sou seu Copiloto de Inteligência. Tenho acesso completo ao seu estoque e margens. Como posso te ajudar hoje?' }
  ])
  const [input, setInput] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef<null | HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  const handleSend = async (content?: string) => {
    const text = content || input
    if (!text.trim()) return

    const newMessages = [...messages, { role: 'user', content: text }]
    setMessages(newMessages)
    setInput('')
    setIsTyping(true)

    try {
      const res = await axios.post(`${API_URL}/chat`, { messages: newMessages })
      setMessages([...newMessages, { role: 'assistant', content: res.data.content }])
    } catch (err) {
      setMessages([...newMessages, { role: 'assistant', content: 'Ops, tive um erro na conexão. Pode tentar novamente?' }])
    } finally {
      setIsTyping(false)
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <header className="p-6 border-b flex justify-between items-center bg-slate-50/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white">
            <Bot size={24} />
          </div>
          <div>
            <h2 className="text-xl font-bold">Chat com IA</h2>
            <p className="text-xs text-emerald-600 font-bold uppercase tracking-widest flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Online e Analisando Dados
            </p>
          </div>
        </div>
        <button 
          onClick={() => setMessages([{ role: 'assistant', content: 'Olá! Conversa resetada. Como posso ajudar com seu estoque?' }])}
          className="text-slate-400 hover:text-rose-500 p-2 transition-colors"
          title="Limpar Conversa"
        >
          <Trash2 size={20} />
        </button>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`flex gap-3 max-w-[85%] ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-8 h-8 rounded-lg flex-shrink-0 flex items-center justify-center ${
                  m.role === 'user' ? 'bg-slate-200 text-slate-600' : 'bg-blue-600 text-white'
                }`}>
                  {m.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                </div>
                <div className={`p-4 rounded-2xl shadow-sm border ${
                  m.role === 'user' 
                    ? 'bg-slate-900 text-white border-slate-800' 
                    : 'bg-slate-50 text-slate-800 border-slate-100'
                }`}>
                  <div className="prose prose-slate max-w-none whitespace-pre-wrap leading-relaxed text-sm">
                    {m.content}
                  </div>
                </div>
              </div>
            </div>
          ))}
          {isTyping && (
            <div className="flex justify-start">
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
                  <Bot size={16} />
                </div>
                <div className="bg-slate-50 p-4 rounded-2xl border border-slate-100 flex gap-1">
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce"></span>
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0.2s]"></span>
                  <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:0.4s]"></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input / Footer */}
      <footer className="p-6 border-t bg-slate-50/50">
        <div className="max-w-4xl mx-auto">
          {/* Quick Actions */}
          <div className="flex gap-2 mb-4 overflow-x-auto pb-2 scrollbar-hide">
            <QuickAction icon={<Package size={14} />} label="Analisar Estoque" onClick={() => handleSend("Faça uma análise geral do meu estoque atual.")} />
            <QuickAction icon={<TrendingUp size={14} />} label="Melhorar Margem" onClick={() => handleSend("Como posso subir minha margem global em 1%?")} />
            <QuickAction icon={<Calculator size={14} />} label="Sugerir Promoção" onClick={() => handleSend("Sugira uma promoção para tirar produtos parados.")} />
            <QuickAction icon={<AlertTriangle size={14} />} label="Riscos?" onClick={() => handleSend("Existe algum risco imediato na minha rentabilidade?")} />
          </div>

          <div className="relative">
            <textarea 
              rows={1}
              placeholder="Pergunte qualquer coisa sobre seu estoque..."
              className="w-full p-4 pr-14 rounded-2xl border border-slate-200 focus:ring-2 focus:ring-blue-500 outline-none shadow-sm resize-none"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
            />
            <button 
              onClick={() => handleSend()}
              disabled={!input.trim() || isTyping}
              className="absolute right-2 bottom-2 p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-all active:scale-95"
            >
              <Send size={20} />
            </button>
          </div>
        </div>
      </footer>
    </div>
  )
}

function QuickAction({ icon, label, onClick }: any) {
  return (
    <button 
      onClick={onClick}
      className="flex items-center gap-2 px-3 py-1.5 bg-white border border-slate-200 rounded-lg text-xs font-semibold text-slate-600 hover:bg-blue-50 hover:border-blue-200 hover:text-blue-600 transition-all whitespace-nowrap shadow-sm"
    >
      {icon}
      {label}
    </button>
  )
}

// ============================================================================
// MargemTrendChart — SVG puro, Tufte-inspired
// - Faixa meta 17-19% desenhada como retângulo sage translúcido (referência visual)
// - Linha principal stroke coral; dots coloridos por status do dia
// - Linha média tracejada (stone) como ponto de comparação silencioso
// - Callout do último ponto em mono
// - Dias sem venda aparecem como círculo cinza aberto (mostra ausência sem mentir)
// ============================================================================
type PontoSerie = {
  data: string
  dia_semana: string
  faturamento: number
  custo: number
  margem: number
  status: string
}

function MargemTrendChart({ serie }: { serie: PontoSerie[] }) {
  if (!serie || serie.length < 2) {
    return (
      <div className="h-64 rounded-xl flex flex-col items-center justify-center text-[color:var(--claude-stone)] text-sm">
        <AlertTriangle className="mb-2 text-[color:var(--claude-stone)]/40" size={28} />
        <span className="serif italic">Dados insuficientes para traçar a tendência.</span>
      </div>
    )
  }

  // Canvas virtual — deixa o SVG escalar por viewBox; proporções pensadas em 760x240
  const W = 760
  const H = 240
  const padL = 44
  const padR = 24
  const padT = 18
  const padB = 36
  const innerW = W - padL - padR
  const innerH = H - padT - padB

  // Escala Y: 0% até max(25%, pico+2pp) — nunca comprime a meta 17-19%
  const margens = serie.map(p => p.margem)
  const yMaxDomain = Math.max(0.25, Math.max(...margens) + 0.02)
  const yToPx = (m: number) => padT + innerH - (m / yMaxDomain) * innerH

  // Escala X: índice
  const xToPx = (i: number) => padL + (i / (serie.length - 1)) * innerW

  // Faixa meta
  const metaMin = 0.17
  const metaMax = 0.19
  const metaTop = yToPx(metaMax)
  const metaBot = yToPx(metaMin)

  // Média da janela (desconsidera sem_vendas)
  const comVenda = serie.filter(p => p.status !== 'sem_vendas')
  const media = comVenda.length > 0
    ? comVenda.reduce((s, p) => s + p.margem, 0) / comVenda.length
    : 0

  // Path da linha — quebra quando dia sem_vendas (Tufte: não fingir continuidade)
  let path = ''
  serie.forEach((p, i) => {
    const x = xToPx(i)
    const y = yToPx(p.margem)
    if (p.status === 'sem_vendas') {
      // quebra — próximo ponto recomeça com M
      if (path && !path.endsWith(' ')) path += ' '
      return
    }
    const cmd = path === '' || path.endsWith(' ') ? 'M' : 'L'
    path += `${cmd}${x.toFixed(1)},${y.toFixed(1)} `
  })

  // Cores por status
  const dotColor: Record<string, string> = {
    saudavel:    'var(--claude-sage)',
    acima_meta:  'var(--claude-coral)',
    abaixo_meta: 'var(--claude-amber)',
    sem_vendas:  'var(--claude-stone)',
  }

  // Ticks X: primeiro, meio, último (Tufte: mínimo de ink)
  const tickIdx = [0, Math.floor(serie.length / 2), serie.length - 1]

  // Ticks Y: 0, meta_min, meta_max, topo
  const yTicks = [0, 0.10, metaMin, metaMax, yMaxDomain]

  // Último ponto útil pra callout
  const lastValid = [...serie].reverse().find(p => p.status !== 'sem_vendas') || serie[serie.length - 1]
  const lastIdx = serie.indexOf(lastValid)
  const lastX = xToPx(lastIdx)
  const lastY = yToPx(lastValid.margem)

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className="w-full h-64"
      role="img"
      aria-label="Tendência de margem diária dos últimos 30 dias"
    >
      <defs>
        <linearGradient id="areaMargem" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--claude-coral)" stopOpacity="0.18" />
          <stop offset="100%" stopColor="var(--claude-coral)" stopOpacity="0" />
        </linearGradient>
      </defs>

      {/* Faixa meta — fundo muito sutil */}
      <rect
        x={padL}
        y={metaTop}
        width={innerW}
        height={Math.max(2, metaBot - metaTop)}
        fill="var(--claude-sage)"
        fillOpacity="0.10"
      />
      {/* Linha da meta superior/inferior bem discreta */}
      <line x1={padL} y1={metaTop} x2={W - padR} y2={metaTop} stroke="var(--claude-sage)" strokeOpacity="0.35" strokeDasharray="2 3" />
      <line x1={padL} y1={metaBot} x2={W - padR} y2={metaBot} stroke="var(--claude-sage)" strokeOpacity="0.35" strokeDasharray="2 3" />

      {/* Gridlines Y — stroke quase invisível */}
      {yTicks.map((t, i) => (
        <g key={`gy-${i}`}>
          <line
            x1={padL} y1={yToPx(t)} x2={W - padR} y2={yToPx(t)}
            stroke="var(--border)" strokeOpacity={t === 0 ? 0.6 : 0.3}
          />
          <text
            x={padL - 8} y={yToPx(t) + 4}
            textAnchor="end"
            fontSize="12"
            fill="var(--claude-stone)"
            fontFamily="JetBrains Mono, monospace"
          >
            {formatPercent(t, { maximumFractionDigits: 0 })}
          </text>
        </g>
      ))}

      {/* Média — linha tracejada stone */}
      {media > 0 && (
        <>
          <line
            x1={padL} y1={yToPx(media)} x2={W - padR} y2={yToPx(media)}
            stroke="var(--claude-stone)" strokeOpacity="0.55" strokeDasharray="4 4" strokeWidth="1"
          />
          <text
            x={padL + 4} y={yToPx(media) - 5}
            textAnchor="start" fontSize="11"
            fill="var(--claude-stone)"
            fontFamily="JetBrains Mono, monospace"
          >
            méd. {formatPercent(media)}
          </text>
        </>
      )}

      {/* Área sob a linha — gradient muito sutil */}
      <path
        d={`${path}L${xToPx(serie.length - 1)},${padT + innerH} L${padL},${padT + innerH} Z`}
        fill="url(#areaMargem)"
        opacity="0.6"
      />

      {/* Linha principal */}
      <path
        d={path}
        fill="none"
        stroke="var(--claude-coral)"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />

      {/* Dots por dia */}
      {serie.map((p, i) => {
        const x = xToPx(i)
        const y = yToPx(p.margem)
        const isSemVendas = p.status === 'sem_vendas'
        return (
          <g key={p.data}>
            <circle
              cx={x} cy={isSemVendas ? padT + innerH - 2 : y}
              r={isSemVendas ? 2.5 : 3.5}
              fill={isSemVendas ? 'transparent' : dotColor[p.status] || 'var(--claude-stone)'}
              stroke={dotColor[p.status] || 'var(--claude-stone)'}
              strokeWidth={isSemVendas ? 1 : 1.5}
              opacity={isSemVendas ? 0.5 : 1}
            >
              <title>{`${p.data} (${p.dia_semana}) · ${isSemVendas ? 'sem vendas' : formatPercent(p.margem)} · ${formatCurrency(p.faturamento)}`}</title>
            </circle>
          </g>
        )
      })}

      {/* Callout último ponto */}
      {lastValid.status !== 'sem_vendas' && (
        <g>
          <circle cx={lastX} cy={lastY} r="5" fill="var(--claude-coral)" fillOpacity="0.15" />
          <text
            x={Math.min(lastX + 8, W - padR - 50)}
            y={lastY - 9}
            fontSize="13"
            fontFamily="JetBrains Mono, monospace"
            fontWeight="600"
            fill="var(--claude-ink)"
          >
            {formatPercent(lastValid.margem)}
          </text>
        </g>
      )}

      {/* Ticks X — só primeiro, meio, último */}
      {tickIdx.map(i => {
        const p = serie[i]
        const dia = p.data.slice(8, 10)
        const mes = p.data.slice(5, 7)
        return (
          <text
            key={`tx-${i}`}
            x={xToPx(i)} y={H - 10}
            textAnchor={i === 0 ? 'start' : i === serie.length - 1 ? 'end' : 'middle'}
            fontSize="12"
            fill="var(--claude-stone)"
            fontFamily="JetBrains Mono, monospace"
          >
            {`${dia}/${mes}`}
          </text>
        )
      })}
    </svg>
  )
}

interface TopProdutoItem {
  produto_id: number
  sku: string
  nome: string
  valor: number
  quantidade: number
  transacoes: number
}

interface RupturaItem {
  produto_id: number
  sku: string
  codigo: string | null
  nome: string
  ultima_venda: string | null
  valor_acumulado: number
}

function DashboardPage({ stats, onNavigate, onAbrirCliente }: any) {
  const [saudeCategorias, setSaudeCategorias] = useState<any[]>([])
  const [projecao, setProjecao] = useState<any>(null)
  const [serie, setSerie] = useState<PontoSerie[]>([])
  const [quebraResumo, setQuebraResumo] = useState<any>(null)
  const [topClientes7d, setTopClientes7d] = useState<ClienteRankingItem[]>([])
  const [topProdutos7d, setTopProdutos7d] = useState<TopProdutoItem[]>([])
  const [rupturas, setRupturas] = useState<RupturaItem[]>([])
  // Estados de carga dos 3 widgets do bloco "Exploracao rapida". Sem isso a UI
  // mostrava "Sem dados" no primeiro frame, antes do fetch responder — confunde
  // (parece estado vazio de verdade) e pisca quando a resposta chega.
  const [loadingTopClientes, setLoadingTopClientes] = useState(true)
  const [loadingTopProdutos, setLoadingTopProdutos] = useState(true)
  const [loadingRupturas, setLoadingRupturas] = useState(true)

  useEffect(() => {
    axios.get(`${API_URL}/categorias/saude`).then(res => setSaudeCategorias(res.data)).catch(() => {})
    axios.get(`${API_URL}/projecao/amanha?top_n=0`).then(res => setProjecao(res.data)).catch(() => {})
    axios.get(`${API_URL}/margem/serie?dias=30`).then(res => setSerie(res.data)).catch(() => {})
    axios.get(`${API_URL}/quebras/resumo`).then(res => setQuebraResumo(res.data)).catch(() => {})
    axios
      .get(`${API_URL}/clientes/ranking`, {
        params: { periodo_dias: 7, limit: 5, incluir_consumidor_final: false },
      })
      .then((res) => setTopClientes7d(res.data))
      .catch(() => setTopClientes7d([]))
      .finally(() => setLoadingTopClientes(false))
    axios
      .get(`${API_URL}/produtos/top-vendidos`, { params: { periodo_dias: 7, limit: 5 } })
      .then((res) => setTopProdutos7d(res.data))
      .catch(() => setTopProdutos7d([]))
      .finally(() => setLoadingTopProdutos(false))
    axios
      .get(`${API_URL}/produtos/rupturas`, { params: { limit: 5 } })
      .then((res) => setRupturas(res.data))
      .catch(() => setRupturas([]))
      .finally(() => setLoadingRupturas(false))
  }, [])

  const classificaMargem = (m: number | null | undefined): 'alerta'|'atencao'|'saudavel'|'acima_meta'|'sem_vendas' => {
    if (m == null) return 'sem_vendas'
    if (m < 0.17) return 'alerta'
    if (m < 0.175) return 'atencao'
    if (m <= 0.195) return 'saudavel'
    return 'acima_meta'
  }
  const margemToKpiStatus = (m: number | null | undefined): 'ok'|'alert'|'warn'|'neutral' => {
    const c = classificaMargem(m)
    if (c === 'saudavel' || c === 'acima_meta') return 'ok'
    if (c === 'atencao') return 'warn'
    if (c === 'alerta') return 'alert'
    return 'neutral'
  }
  const tagMargem = (m: number | null | undefined): string => {
    const c = classificaMargem(m)
    if (c === 'acima_meta') return 'acima da meta'
    if (c === 'saudavel') return 'na meta'
    if (c === 'atencao') return 'perto do piso'
    if (c === 'alerta') return 'abaixo critico'
    return ''
  }

  const marginPct = stats?.margem_semana != null ? formatPercent(stats.margem_semana) : null
  const margemSemanaStatus = classificaMargem(stats?.margem_semana)
  const margemSemanaPositiva = margemSemanaStatus === 'saudavel' || margemSemanaStatus === 'acima_meta'
  const projecaoPct = projecao?.margem_prevista != null ? formatPercent(projecao.margem_prevista) : null
  const projecaoConfianca = projecao?.confianca_geral || "sem_dados"

  // Contadores da série pra microcopy do chart
  const diasSaudaveis = serie.filter(p => p.status === 'saudavel').length
  const diasAbaixo = serie.filter(p => p.status === 'abaixo_meta').length
  const diasAcima = serie.filter(p => p.status === 'acima_meta').length
  const diasComVenda = serie.filter(p => p.status !== 'sem_vendas').length

  // Séries pros KPIs (últimos 14 pontos, só dias com venda viram sparkline)
  const serieUltimos14 = serie.slice(-14)
  const spark14Margem = serieUltimos14
    .filter(p => p.status !== 'sem_vendas')
    .map(p => p.margem * 100)
  const spark14Fat = serieUltimos14
    .filter(p => p.status !== 'sem_vendas')
    .map(p => p.faturamento)
  // Sparkline 30d para o hero card (mais largo)
  const spark30Margem = serie
    .filter(p => p.status !== 'sem_vendas')
    .map(p => p.margem * 100)

  // Delta de margem: última vs média dos 7 anteriores (em pontos percentuais)
  const comVendaAll = serie.filter(p => p.status !== 'sem_vendas').map(p => p.margem * 100)
  const ultMargem = comVendaAll.length > 0 ? comVendaAll[comVendaAll.length - 1] : null
  const prev7Margem = comVendaAll.length >= 8 ? comVendaAll.slice(-8, -1) : []
  const mediaPrev7Margem = prev7Margem.length > 0
    ? prev7Margem.reduce((a, b) => a + b, 0) / prev7Margem.length
    : null
  const deltaMargem = ultMargem != null && mediaPrev7Margem != null ? ultMargem - mediaPrev7Margem : 0

  // Delta de faturamento: hoje vs média dos 7 anteriores (em %)
  const comVendaFat = serie.filter(p => p.status !== 'sem_vendas').map(p => p.faturamento)
  const prev7Fat = comVendaFat.length >= 8 ? comVendaFat.slice(-8, -1) : comVendaFat.slice(0, -1)
  const mediaPrev7Fat = prev7Fat.length > 0 ? prev7Fat.reduce((a, b) => a + b, 0) / prev7Fat.length : 0
  const faturamentoHoje = stats?.total_vendas_hoje || 0
  const deltaFatPct = mediaPrev7Fat > 0 ? ((faturamentoHoje - mediaPrev7Fat) / mediaPrev7Fat) * 100 : 0

  // Tone do hero (Margem Semana) — usado no border-left, gradient e sparkline
  const heroToneVar =
    margemSemanaStatus === 'sem_vendas' ? 'var(--claude-stone)'
    : margemSemanaPositiva ? 'var(--claude-sage)'
    : margemSemanaStatus === 'atencao' ? 'var(--claude-amber)'
    : 'var(--claude-coral)'
  const heroToneClass =
    margemSemanaStatus === 'sem_vendas' ? 'text-[color:var(--claude-stone)]'
    : margemSemanaPositiva ? 'text-[color:var(--claude-sage)]'
    : margemSemanaStatus === 'atencao' ? 'text-[color:var(--claude-amber)]'
    : 'text-[color:var(--claude-coral)]'
  const heroPillClass =
    margemSemanaStatus === 'sem_vendas' ? 'pill pill-muted'
    : margemSemanaPositiva ? 'pill pill-ok'
    : margemSemanaStatus === 'atencao' ? 'pill pill-warn'
    : 'pill pill-alert'
  const heroSparkTone: SparkTone =
    margemSemanaStatus === 'sem_vendas' ? 'stone'
    : margemSemanaPositiva ? 'sage'
    : margemSemanaStatus === 'atencao' ? 'amber'
    : 'coral'
  const heroDeltaSemana = ultMargem != null && mediaPrev7Margem != null ? ultMargem - mediaPrev7Margem : 0

  // ===== Prioridades do dia (computadas a partir do estado já carregado) =====
  type Prioridade = {
    key: string
    severidade: 'alta' | 'media' | 'oportunidade'
    titulo: string
    descricao: string
    ctaLabel: string
    onCta: () => void
  }
  const prioridades: Prioridade[] = []
  // 1. Margem fora da meta (semana)
  if (stats?.margem_semana != null && classificaMargem(stats.margem_semana) === 'alerta') {
    prioridades.push({
      key: 'margem_alerta',
      severidade: 'alta',
      titulo: `Margem da semana abaixo do crítico (${formatPercent(stats.margem_semana)})`,
      descricao: 'Meta institucional 17–19%. Revise produtos com margem baixa e considere ajuste de preço.',
      ctaLabel: 'Abrir briefing',
      onCta: () => onNavigate('briefing'),
    })
  } else if (stats?.margem_semana != null && classificaMargem(stats.margem_semana) === 'atencao') {
    prioridades.push({
      key: 'margem_atencao',
      severidade: 'media',
      titulo: `Margem da semana perto do piso (${formatPercent(stats.margem_semana)})`,
      descricao: 'Atenção: margem entre 17 e 17,5%. Acompanhe a tendência e revise os SKUs com pior performance.',
      ctaLabel: 'Ver tendência',
      onCta: () => onNavigate('briefing'),
    })
  }
  // 2. Rupturas
  if ((stats?.rupturas ?? 0) > 0) {
    prioridades.push({
      key: 'rupturas',
      severidade: 'alta',
      titulo: `${stats.rupturas} SKU${stats.rupturas === 1 ? '' : 's'} zerado${stats.rupturas === 1 ? '' : 's'}`,
      descricao: 'Produtos sem estoque que vinham vendendo. Reponha antes que afetem o faturamento de amanhã.',
      ctaLabel: 'Ver lista de rupturas',
      onCta: () => onNavigate('historico'),
    })
  }
  // 3. Cliente top da semana (oportunidade — só se tiver tração)
  const topClienteSem = topClientes7d[0]
  if (topClienteSem && topClienteSem.valor_periodo > 0 && prioridades.length < 3) {
    prioridades.push({
      key: 'cliente_top',
      severidade: 'oportunidade',
      titulo: `${topClienteSem.nome} comprou ${formatCurrency(topClienteSem.valor_periodo)} esta semana`,
      descricao: `Segmento ${topClienteSem.segmento_label}. Use a relação pra negociar pacote ou repor estoque dele.`,
      ctaLabel: 'Abrir cliente',
      onCta: () => onAbrirCliente && onAbrirCliente(topClienteSem.cliente_id),
    })
  }
  prioridades.splice(3) // máximo 3

  const sevTone: Record<string, { bg: string; border: string; icon: string; text: string }> = {
    alta: { bg: 'bg-rose-50', border: 'border-rose-200', icon: 'text-rose-600', text: 'text-rose-900' },
    media: { bg: 'bg-amber-50', border: 'border-amber-200', icon: 'text-amber-700', text: 'text-amber-900' },
    oportunidade: { bg: 'bg-emerald-50', border: 'border-emerald-200', icon: 'text-emerald-700', text: 'text-emerald-900' },
  }

  const SectionLabel = ({ label, hint }: { label: string; hint?: string }) => (
    <div className="flex items-baseline justify-between mt-2 mb-1">
      <p className="section-label">{label}</p>
      {hint && <span className="text-[10px] text-[color:var(--claude-stone)] uppercase tracking-widest">{hint}</span>}
    </div>
  )

  return (
    <div className="max-w-7xl mx-auto p-8 space-y-5">
      {/* Header compacto — sem KPI lateral (movido pra hero) */}
      <header>
        <p className="section-label mb-1">Visão Geral · {formatDate(new Date(), { weekday: 'long', day: '2-digit', month: 'long' })}</p>
        <h2 className="headline text-4xl tracking-editorial">Painel de Decisão</h2>
        <p className="text-[color:var(--claude-stone)] mt-1 text-sm">Inteligência aplicada para garantir seus lucros.</p>
      </header>

      {/* ===================================================================
          BLOCO 1 — Prioridades do dia (até 3 cards de ação, condicional)
          =================================================================== */}
      {prioridades.length > 0 && (
        <div>
          <SectionLabel label="Prioridades do dia" hint={`${prioridades.length} item${prioridades.length === 1 ? '' : 's'}`} />
          <div className={`grid grid-cols-1 ${prioridades.length === 1 ? 'md:grid-cols-1' : prioridades.length === 2 ? 'md:grid-cols-2' : 'md:grid-cols-3'} gap-3 mt-3`}>
            {prioridades.map((p) => {
              const t = sevTone[p.severidade]
              return (
                <div key={p.key} className={`rounded-xl border ${t.border} ${t.bg} p-4 flex flex-col gap-3`}>
                  <div className="flex items-start gap-2">
                    {p.severidade === 'oportunidade' ? (
                      <Sparkles className={`${t.icon} shrink-0 mt-0.5`} size={16} />
                    ) : (
                      <AlertCircle className={`${t.icon} shrink-0 mt-0.5`} size={16} />
                    )}
                    <div className="min-w-0">
                      <p className={`font-semibold text-sm ${t.text} leading-tight`}>{p.titulo}</p>
                      <p className="text-xs text-[color:var(--claude-stone)] mt-1 leading-snug">{p.descricao}</p>
                    </div>
                  </div>
                  <button
                    onClick={p.onCta}
                    className={`text-xs font-bold uppercase tracking-widest ${t.text} hover:underline self-start mt-auto`}
                  >
                    {p.ctaLabel} →
                  </button>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ===================================================================
          BLOCO 2 — Indicadores principais
          =================================================================== */}
      <SectionLabel label="Indicadores principais" hint="janela 30 dias / dia atual" />

      {/* BENTO ROW 1 — Hero (col-span-7) + 2 KPIs medium (col-span-5)
          Inspirado em Muzli/Orbix 2026: hero metric com 2.6x peso visual
          dos satellites; 12-col grid com 20px gutters.
          =================================================================== */}
      <div className="grid grid-cols-12 gap-5">
        {/* HERO: Margem Semana com sparkline 30d e badge premium */}
        <div
          className="col-span-12 lg:col-span-6 claude-card relative overflow-hidden p-7"
          style={{
            background: `radial-gradient(circle at 100% 0%, color-mix(in srgb, ${heroToneVar} 10%, transparent) 0%, transparent 55%), linear-gradient(180deg, #FFFFFF 0%, color-mix(in srgb, var(--claude-cream-deep) 50%, white) 100%)`,
            borderLeft: `3px solid ${heroToneVar}`,
          }}
        >
          {/* halo glow sutil */}
          <div
            aria-hidden="true"
            className="pointer-events-none absolute -top-24 -right-16 w-72 h-72 rounded-full blur-3xl opacity-20"
            style={{ background: heroToneVar }}
          />
          <div className="relative">
            <div className="flex items-start justify-between mb-2">
              <div>
                <p className="section-label">Margem Semana · 7 dias</p>
                <p className="text-xs text-[color:var(--claude-stone)] mt-1">Meta institucional 17 – 19 %</p>
              </div>
              {marginPct != null && tagMargem(stats?.margem_semana) && (
                <span className={heroPillClass}>{tagMargem(stats?.margem_semana)}</span>
              )}
            </div>

            <div className="flex items-end justify-between mt-5 gap-4">
              <MetricValue value={marginPct ?? '—'} size="hero" toneClass={heroToneClass} />
              <div className="pb-3 flex flex-col items-end gap-2">
                <BadgeDelta value={heroDeltaSemana} format="pp" />
                <span className="text-[10px] uppercase tracking-widest text-[color:var(--claude-stone)]">vs semana anterior</span>
              </div>
            </div>

            {spark30Margem.length >= 2 && (
              <div className="mt-5">
                <Sparkline data={spark30Margem} tone={heroSparkTone} height={48} />
              </div>
            )}

            <div className="mt-4 flex items-center gap-4 text-[11px] text-[color:var(--claude-stone)] uppercase tracking-wide">
              <span className="flex items-center gap-1.5"><Gauge size={12} /> 30 dias</span>
              {diasComVenda > 0 && (
                <>
                  <span className="mono"><b className="text-[color:var(--claude-sage)]">{diasSaudaveis}</b>/{diasComVenda} dias na meta</span>
                  {diasAcima > 0 && <span className="mono"><b className="text-[color:var(--claude-coral)]">{diasAcima}</b> acima</span>}
                  {diasAbaixo > 0 && <span className="mono"><b className="text-[color:var(--claude-amber)]">{diasAbaixo}</b> abaixo</span>}
                </>
              )}
            </div>
          </div>
        </div>

        {/* KPI medium — Margem do Dia */}
        <div className="col-span-12 sm:col-span-6 lg:col-span-3">
          <KPICard
            title="Margem do Dia"
            value={stats?.margem_dia != null ? formatPercent(stats.margem_dia) : formatPercent(ultMargem, { scale: 1 })}
            status={margemToKpiStatus(stats?.margem_dia ?? (ultMargem != null ? ultMargem / 100 : null))}
            delta={deltaMargem}
            deltaFormat="pp"
            deltaLabel={(() => {
              const m = stats?.margem_dia ?? (ultMargem != null ? ultMargem / 100 : null)
              const tag = tagMargem(m)
              const base = mediaPrev7Margem != null ? `vs média 7d (${formatPercent(mediaPrev7Margem, { scale: 1 })})` : 'Meta 17–19%'
              return tag ? `${base} · ${tag}` : base
            })()}
            sparklineData={spark14Margem}
          />
        </div>

        {/* KPI medium — Faturamento Hoje */}
        <div className="col-span-12 sm:col-span-6 lg:col-span-3">
          <KPICard
            title="Faturamento Hoje"
            value={formatCurrency(faturamentoHoje)}
            status={faturamentoHoje > 0 ? 'up' : 'neutral'}
            delta={deltaFatPct}
            deltaFormat="pct"
            deltaLabel={mediaPrev7Fat > 0 ? `vs média 7d (${formatCurrency(mediaPrev7Fat, { minimumFractionDigits: 0, maximumFractionDigits: 0 })})` : 'Faturamento do dia'}
            sparklineData={spark14Fat}
          />
        </div>
      </div>

      {/* ===================================================================
          BENTO ROW 2 — 3 KPIs satellite (col-span-4 cada)
          Projeção D+1 / Rupturas / Quebras (mês)
          =================================================================== */}
      <div className="grid grid-cols-12 gap-5">
        <div className="col-span-12 sm:col-span-6 lg:col-span-4">
          <KPICard
            title="Projeção D+1"
            value={projecaoPct ?? '—'}
            subValue={`Confiança: ${projecaoConfianca}`}
            status={projecaoConfianca === "sem_dados" ? 'neutral' : margemToKpiStatus(projecao?.margem_prevista)}
          />
        </div>
        <div className="col-span-12 sm:col-span-6 lg:col-span-4">
          <KPICard
            title="Rupturas"
            value={stats?.rupturas ?? 0}
            subValue={(() => {
              const rupt = stats?.rupturas ?? 0
              const skus = stats?.total_skus
              if (skus == null) return rupt > 0 ? `${rupt} zerado${rupt === 1 ? '' : 's'} · repor` : 'sem dados'
              const skuLabel = skus === 1 ? 'SKU' : 'SKUs'
              if (rupt > 0) return `${rupt}/${skus} zerado${rupt === 1 ? '' : 's'} · repor`
              return `${skus} ${skuLabel} · sem rupturas`
            })()}
            status={(stats?.rupturas ?? 0) > 0 ? "alert" : stats?.total_skus == null ? "neutral" : "ok"}
          />
        </div>
        <div className="col-span-12 lg:col-span-4">
          <KPICard
            title="Quebras (mês)"
            value={quebraResumo
              ? formatCurrency(quebraResumo.valor_total)
              : '—'}
            subValue={!quebraResumo
              ? 'Sem dados'
              : quebraResumo.eventos === 0
                ? 'Sem quebras registradas no mês'
                : `${formatPercent(quebraResumo.pct_faturamento, { maximumFractionDigits: 2 })} do faturamento · ${quebraResumo.eventos} evento${quebraResumo.eventos === 1 ? '' : 's'}`}
            status={!quebraResumo ? 'neutral' : quebraResumo.pct_faturamento > 0.02 ? 'alert' : quebraResumo.pct_faturamento > 0.015 ? 'warn' : 'ok'}
          />
        </div>
      </div>

      {/* ===================================================================
          BENTO ROW 3 — Data viz: Tendência expandida (col-8) + Saúde (col-4)
          =================================================================== */}
      <div className="grid grid-cols-12 gap-5">
        <div className="col-span-12 lg:col-span-8 claude-card p-6 relative overflow-hidden">
          <div className="flex items-start justify-between mb-5">
            <div>
              <p className="section-label mb-1">Últimos 30 dias</p>
              <h3 className="headline text-2xl">Tendência de Margem</h3>
              <p className="text-xs text-[color:var(--claude-stone)] mt-1">
                Faixa verde = meta 17 – 19 %. Dots coral = acima (&gt;19,5%). Âmbar = abaixo. Cinza = sem venda.
              </p>
            </div>
            {diasComVenda > 0 && (
              <div className="flex gap-2 text-[10px]">
                <span className="pill pill-ok"><span className="mono">{diasSaudaveis}</span> saudável</span>
                {diasAcima > 0 && <span className="pill pill-alert"><span className="mono">{diasAcima}</span> acima</span>}
                {diasAbaixo > 0 && <span className="pill pill-warn"><span className="mono">{diasAbaixo}</span> abaixo</span>}
              </div>
            )}
          </div>
          <MargemTrendChart serie={serie} />
        </div>

        <div className="col-span-12 lg:col-span-4 claude-card p-6 flex flex-col">
          <p className="section-label mb-1">Janela de 30 dias</p>
          <h3 className="headline text-2xl mb-1">Saúde por Categoria</h3>
          <p className="text-xs text-[color:var(--claude-stone)] mb-5">Margem real praticada vs meta configurada no grupo.</p>
          <div className="flex-1 space-y-5">
            {saudeCategorias.length > 0 ? saudeCategorias.map((g: any) => (
              <GroupProgress
                key={g.grupo_id}
                label={g.nome}
                margemReal={g.margem_real}
                metaMin={g.margem_minima}
                metaMax={g.margem_maxima}
                faturamento={g.faturamento_periodo}
                skusVendidos={g.skus_vendidos_periodo}
                skusNoGrupo={g.skus_no_grupo}
                status={g.status}
              />
            )) : (
              <EmptyState variant="empty" compact title="Nenhum grupo cadastrado." />
            )}
          </div>
        </div>
      </div>

      {/* ===================================================================
          BLOCO 3 — Exploração rápida: 3 widgets compactos lado-a-lado
          Top Clientes (7d) | Top Produtos (7d) | Rupturas
          =================================================================== */}
      <SectionLabel label="Exploração rápida" hint="últimos 7 dias" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Top 5 Clientes da semana */}
        <div className="claude-card p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="headline text-lg">Top 5 clientes</h3>
            <button
              onClick={() => onNavigate('clientes')}
              className="text-[10px] font-bold text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)] uppercase tracking-widest"
            >
              Ver todos →
            </button>
          </div>
          {loadingTopClientes ? (
            <WidgetSkeleton rows={5} />
          ) : topClientes7d.length === 0 ? (
            <EmptyState variant="empty" compact title="Sem clientes identificados em 7 dias." />
          ) : (
            <ul className="divide-y divide-[color:var(--border)]">
              {topClientes7d.map((c, idx) => (
                <li key={c.cliente_id}>
                  <button
                    onClick={() => onAbrirCliente && onAbrirCliente(c.cliente_id)}
                    className="w-full text-left flex items-center gap-2 py-2 hover:bg-[color:var(--claude-cream-deep)]/30 rounded transition-colors"
                  >
                    <span className="w-5 text-[color:var(--claude-stone)] font-mono tabular-nums text-xs">{idx + 1}.</span>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-[color:var(--claude-ink)] truncate text-sm">{c.nome}</p>
                      <p className="text-[10px] uppercase tracking-widest text-[color:var(--claude-stone)]">{c.segmento_label}</p>
                    </div>
                    <MetricValue value={formatCurrency(c.valor_periodo)} size="sm" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Top 5 Produtos da semana */}
        <div className="claude-card p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="headline text-lg">Top 5 produtos</h3>
            <button
              onClick={() => onNavigate('produtos')}
              className="text-[10px] font-bold text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)] uppercase tracking-widest"
            >
              Ver SKUs →
            </button>
          </div>
          {loadingTopProdutos ? (
            <WidgetSkeleton rows={5} />
          ) : topProdutos7d.length === 0 ? (
            <EmptyState variant="empty" compact title="Sem vendas registradas em 7 dias." />
          ) : (
            <ul className="divide-y divide-[color:var(--border)]">
              {topProdutos7d.map((p, idx) => (
                <li key={p.produto_id} className="flex items-center gap-2 py-2">
                  <span className="w-5 text-[color:var(--claude-stone)] font-mono tabular-nums text-xs">{idx + 1}.</span>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-[color:var(--claude-ink)] truncate text-sm">{p.nome}</p>
                    <p className="text-[10px] uppercase tracking-widest text-[color:var(--claude-stone)]">
                      {p.transacoes} compra{p.transacoes === 1 ? '' : 's'}
                    </p>
                  </div>
                  <MetricValue value={formatCurrency(p.valor)} size="sm" />
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Alerta de rupturas (lista) */}
        <div className="claude-card p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className={`headline text-lg ${rupturas.length > 0 ? 'text-[color:var(--claude-coral)]' : ''}`}>
              Rupturas
            </h3>
            <button
              onClick={() => onNavigate('historico')}
              className="text-[10px] font-bold text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)] uppercase tracking-widest"
            >
              Histórico →
            </button>
          </div>
          {loadingRupturas ? (
            <WidgetSkeleton rows={3} />
          ) : rupturas.length === 0 ? (
            <EmptyState
              variant="empty"
              compact
              icon={<Check size={20} className="text-[color:var(--claude-sage)]" />}
              title="Nenhuma ruptura ativa."
            />
          ) : (
            <ul className="divide-y divide-[color:var(--border)]">
              {rupturas.map((r) => (
                <li key={r.produto_id} className="flex items-center gap-2 py-2">
                  <span className="w-1.5 h-1.5 rounded-full bg-[color:var(--claude-coral)] shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-[color:var(--claude-ink)] truncate text-sm">{r.nome}</p>
                    <p className="text-[10px] uppercase tracking-widest text-[color:var(--claude-stone)]">
                      {r.codigo ? `cód ${r.codigo} · ` : ''}
                      {r.ultima_venda ? `última: ${r.ultima_venda}` : 'sem venda'}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* ===================================================================
          BENTO ROW 4 — Copiloto IA full-width com glow accent (sage halo)
          Pattern Hynex (Muzli 2026): 1 cor vibrante reservada pra AI insights
          =================================================================== */}
      <div className="relative">
        {/* halo glow externo — tom sage discreto */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 rounded-2xl blur-2xl opacity-35"
          style={{ background: 'radial-gradient(circle at 80% 50%, var(--claude-coral) 0%, transparent 60%)' }}
        />
        <div
          className="relative rounded-2xl p-7 text-white shadow-[0_8px_32px_-8px_rgba(28,27,23,0.35)] overflow-hidden"
          style={{
            background: 'radial-gradient(circle at 0% 0%, rgba(232,181,162,0.15) 0%, transparent 50%), linear-gradient(135deg, #1C1B17 0%, #2A2620 60%, #3A2E25 100%)',
            border: '1px solid rgba(232,181,162,0.18)',
          }}
        >
          <div className="flex justify-between items-start mb-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                   style={{ background: 'rgba(232,181,162,0.15)', boxShadow: '0 0 24px -4px rgba(232,181,162,0.4) inset' }}>
                <Sparkles className="text-[color:var(--claude-coral-soft)]" size={20} />
              </div>
              <div>
                <h3 className="headline text-2xl text-white leading-tight">Copiloto IA</h3>
                <p className="text-white/60 text-xs mt-0.5">Motor pronto para responder qualquer dúvida sobre o dia.</p>
              </div>
            </div>
            <button
              onClick={() => onNavigate('chat')}
              className="bg-white/10 hover:bg-white/20 text-white text-xs font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-2"
            >
              Abrir Chat <ArrowRight size={14} />
            </button>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button onClick={() => onNavigate('chat')} className="group bg-white/[0.04] hover:bg-white/[0.10] transition-all p-4 rounded-xl border border-white/10 hover:border-[color:var(--claude-coral-soft)]/40 text-left">
              <p className="section-label text-[color:var(--claude-coral-soft)] mb-2">Comando Sugerido</p>
              <p className="serif text-lg leading-tight mb-1 group-hover:translate-x-0.5 transition-transform">Como está meu lucro hoje?</p>
              <p className="text-[10px] text-white/50 uppercase tracking-widest">Toque para perguntar</p>
            </button>
            <button onClick={() => onNavigate('chat')} className="group bg-white/[0.04] hover:bg-white/[0.10] transition-all p-4 rounded-xl border border-white/10 hover:border-[color:var(--claude-coral-soft)]/40 text-left">
              <p className="section-label text-[color:var(--claude-coral-soft)] mb-2">Comando Sugerido</p>
              <p className="serif text-lg leading-tight mb-1 group-hover:translate-x-0.5 transition-transform">Análise de rupturas.</p>
              <p className="text-[10px] text-white/50 uppercase tracking-widest">Toque para perguntar</p>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Tremor-style KPI primitives — sparkline SVG puro + badge delta + card
// Sem dependências externas; usa tokens Claude Design.
// ============================================================================

type SparkTone = 'sage' | 'coral' | 'amber' | 'stone'

function Sparkline({ data, tone = 'sage', height = 28 }: { data: number[]; tone?: SparkTone; height?: number }) {
  if (!data || data.length < 2) return null
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const w = 100
  const h = height
  const pad = 2

  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * w
    const y = h - pad - ((v - min) / range) * (h - pad * 2)
    return { x, y }
  })

  const linePoints = pts.map(p => `${p.x},${p.y}`).join(' ')
  const areaPath = `M 0,${h} L ${linePoints.split(' ').join(' L ')} L ${w},${h} Z`

  const colorMap: Record<SparkTone, string> = {
    sage: 'var(--claude-sage)',
    coral: 'var(--claude-coral)',
    amber: 'var(--claude-amber)',
    stone: 'var(--claude-stone)',
  }
  const color = colorMap[tone]
  const gradId = `spark-${tone}-${Math.random().toString(36).slice(2, 8)}`
  const last = pts[pts.length - 1]

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full" style={{ height }} preserveAspectRatio="none">
      <defs>
        <linearGradient id={gradId} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.22" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradId})`} />
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
        points={linePoints}
      />
      <circle cx={last.x} cy={last.y} r="1.8" fill={color} vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

type DeltaFormat = 'pp' | 'pct' | 'abs_brl'

function BadgeDelta({ value, format = 'pp', invertColor = false }: { value: number; format?: DeltaFormat; invertColor?: boolean }) {
  const isZero = value === 0 || !isFinite(value) || Math.abs(value) < 0.05
  if (isZero) {
    return (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold mono px-1.5 py-0.5 rounded"
            style={{ background: 'color-mix(in srgb, var(--claude-stone) 12%, transparent)', color: 'var(--claude-stone)' }}>
        <Minus size={10} strokeWidth={3} /> 0
      </span>
    )
  }
  const isPositive = value > 0
  const isGood = invertColor ? !isPositive : isPositive
  const color = isGood ? 'var(--claude-sage)' : 'var(--claude-coral)'
  const Icon = isPositive ? ArrowUpRight : ArrowDownRight
  const label =
    format === 'pp' ? `${formatNumber(value, { minimumFractionDigits: 1, maximumFractionDigits: 1, signed: true })}pp`
    : format === 'pct' ? formatPercent(value, { scale: 1, signed: true })
    : formatCurrency(value, { minimumFractionDigits: 0, maximumFractionDigits: 0, signed: true })

  return (
    <span className="inline-flex items-center gap-0.5 text-[10px] font-semibold mono px-1.5 py-0.5 rounded"
          style={{ background: `color-mix(in srgb, ${color} 12%, transparent)`, color }}>
      <Icon size={10} strokeWidth={2.5} /> {label}
    </span>
  )
}

type KPIStatus = 'up' | 'ok' | 'alert' | 'warn' | 'neutral'
type KPICardProps = {
  title: string
  value: string | number
  subValue?: string
  sub?: string                // alias legado (compat com telas que ainda usam)
  status?: KPIStatus
  tone?: KPIStatus            // alias legado
  delta?: number
  deltaFormat?: DeltaFormat
  deltaLabel?: string
  deltaInvertColor?: boolean
  sparklineData?: number[]
  sparklineTone?: SparkTone
}

function KPICard({
  title, value, subValue, sub, status, tone,
  delta, deltaFormat = 'pp', deltaLabel, deltaInvertColor,
  sparklineData, sparklineTone,
}: KPICardProps) {
  const effectiveStatus: KPIStatus = status ?? tone ?? 'neutral'
  const effectiveSub = subValue ?? sub
  const toneFromStatus: Record<KPIStatus, SparkTone> = {
    up: 'sage', ok: 'sage', alert: 'coral', warn: 'amber', neutral: 'stone',
  }
  const sparkTone: SparkTone = sparklineTone || toneFromStatus[effectiveStatus]
  const dotColor: Record<KPIStatus, string> = {
    up: 'bg-[color:var(--claude-sage)]',
    ok: 'bg-[color:var(--claude-sage)]',
    alert: 'bg-[color:var(--claude-coral)]',
    warn: 'bg-[color:var(--claude-amber)]',
    neutral: 'bg-[color:var(--claude-stone)]/40',
  }
  const hasSpark = sparklineData && sparklineData.length >= 2

  const subText = deltaLabel || effectiveSub || ''
  return (
    <div className="claude-card p-5 transition-all hover:shadow-[0_4px_16px_-8px_rgba(28,27,23,0.16)]">
      <div className="flex items-start justify-between gap-2 min-h-[18px]">
        <p className="section-label">{title}</p>
        {delta !== undefined && <BadgeDelta value={delta} format={deltaFormat} invertColor={deltaInvertColor} />}
      </div>
      <p className="mt-2 min-h-[28px]">
        <MetricValue value={value} size="28px" />
      </p>
      {hasSpark ? (
        <div className="mt-3 -mx-1" aria-hidden="true">
          <Sparkline data={sparklineData!} tone={sparkTone} height={28} />
        </div>
      ) : (
        <div className="mt-3 h-[28px]" />
      )}
      <div className="mt-1 flex items-center justify-between gap-2 min-h-[14px]">
        <p
          className="text-[10px] font-medium text-[color:var(--claude-stone)] uppercase tracking-wide line-clamp-1 flex-1"
          title={typeof subText === 'string' ? subText : undefined}
        >
          {subText}
        </p>
        <span className={`w-2 h-2 rounded-full shrink-0 ${dotColor[effectiveStatus]}`}></span>
      </div>
    </div>
  )
}

function GroupProgress({ label, margemReal, metaMin, metaMax, faturamento, skusVendidos, skusNoGrupo, status }: any) {
  // Cor Claude Design por status
  const barColorMap: Record<string, string> = {
    saudavel:    'bg-[color:var(--claude-sage)]',
    acima_meta:  'bg-[color:var(--claude-coral)]',
    abaixo_meta: 'bg-[color:var(--claude-amber)]',
    sem_vendas:  'bg-[color:var(--claude-stone)]/25',
  }
  const barColor = barColorMap[status] || 'bg-[color:var(--claude-stone)]/25'

  // Escala: 0 a max(meta_max*1.5, 30%) — evita achatar todos na ponta
  const escalaMax = Math.max(metaMax * 1.5, 0.30)
  const widthPct = Math.min(100, Math.max(0, (margemReal / escalaMax) * 100))
  const metaMinPos = (metaMin / escalaMax) * 100
  const metaMaxPos = (metaMax / escalaMax) * 100

  const margemLabel = status === 'sem_vendas' ? '—' : formatPercent(margemReal)
  const metaLabel = `meta ${formatPercent(metaMin, { maximumFractionDigits: 0 })}–${formatPercent(metaMax, { maximumFractionDigits: 0 })}`

  const statusTextColor: any = {
    saudavel:    'text-[color:var(--claude-sage)]',
    acima_meta:  'text-[color:var(--claude-coral)]',
    abaixo_meta: 'text-[color:var(--claude-amber)]',
    sem_vendas:  'text-[color:var(--claude-stone)]/60',
  }

  return (
    <div>
      <div className="flex justify-between items-baseline mb-1.5">
        <span className="text-sm font-medium text-[color:var(--claude-ink)]">{label}</span>
        <span className={`kpi-value text-sm ${statusTextColor[status] || 'text-[color:var(--claude-stone)]'}`}>{margemLabel}</span>
      </div>
      <div className="relative w-full bg-[color:var(--claude-cream-deep)] h-[6px] rounded-full overflow-visible mb-1.5">
        <div className={`h-full rounded-full transition-all duration-700 ${barColor}`} style={{ width: `${widthPct}%` }}></div>
        {/* Faixa-meta como marca discreta */}
        <div
          className="absolute top-[-3px] h-[12px] border-l border-r border-[color:var(--claude-sage)]/70"
          style={{ left: `${metaMinPos}%`, width: `${Math.max(0, metaMaxPos - metaMinPos)}%`, background: 'color-mix(in srgb, var(--claude-sage) 8%, transparent)' }}
          title={metaLabel}
        ></div>
      </div>
      <div className="flex justify-between items-center text-[10px] text-[color:var(--claude-stone)]">
        <span className="uppercase tracking-wide">{metaLabel}</span>
        <span className="mono">
          {status === 'sem_vendas'
            ? 'Sem vendas em 30 dias'
            : `${skusVendidos}/${skusNoGrupo} · ${formatCurrency(Number(faturamento))}`
          }
        </span>
      </div>
    </div>
  )
}

function RelatoriosPage() {
  const [produtos, setProdutos] = useState<Produto[]>([])
  const [grupos, setGrupos] = useState<Grupo[]>([])
  const [salesItems, setSalesItems] = useState<any>({})
  const [salesPrices, setSalesPrices] = useState<any>({})
  const [submitting, setSubmitting] = useState(false)
  const [summary, setSummary] = useState<any>(null)
  const [copied, setCopied] = useState(false)
  const [importOpen, setImportOpen] = useState(false)
  // Feedback inline: substitui os alert() nativos no fluxo de fechamento manual
  // e na ponte CSV → analise. Tom coerente com o resto do app.
  const [feedback, setFeedback] = useState<FeedbackMessage | null>(null)
  // Loading explicito do fetch inicial — sem isso, o estado vazio
  // ("Comece importando o relatório do ERP") aparece no primeiro frame antes
  // de a API responder, parecendo que nao ha produtos cadastrados.
  const [loadingProdutos, setLoadingProdutos] = useState(true)

  const carregarProdutos = () => {
    axios
      .get(`${API_URL}/produtos`)
      .then((res) => setProdutos(res.data))
      .finally(() => setLoadingProdutos(false))
  }

  useEffect(() => {
    carregarProdutos()
    axios.get(`${API_URL}/grupos`).then(res => setGrupos(res.data))
  }, [])

  const handleQtyChange = (id: number, val: string) => {
    const qty = parseFloat(val) || 0
    setSalesItems({ ...salesItems, [id]: qty })
  }

  const handlePriceChange = (id: number, val: string) => {
    const price = parseFloat(val) || 0
    setSalesPrices({ ...salesPrices, [id]: price })
  }

  const handleImportConcluido = async (dataAlvo: string) => {
    // Após o commit, busca a análise do dia e exibe no mesmo fluxo
    // usado pelo fechamento manual.
    try {
      const res = await axios.get(`${API_URL}/fechamento/analise?data=${dataAlvo}`)
      setSummary(res.data)
    } catch (e) {
      setFeedback({
        tone: 'warn',
        mensagem: 'Importação concluída, mas não consegui carregar a análise. Confira pela aba Histórico.',
      })
    }
    setImportOpen(false)
    carregarProdutos()
  }

  const handleFechamento = async () => {
    const items = Object.entries(salesItems)
      .filter(([_, qty]: any) => qty > 0)
      .map(([idStr, qty]: any) => {
        const id = parseInt(idStr)
        const prod = produtos.find(p => p.id === id)
        const price = salesPrices[id] || prod?.preco_venda || 0
        return {
          produto_id: id,
          quantidade: qty,
          preco_venda: price
        }
      })

    if (items.length === 0) {
      setFeedback({
        tone: 'warn',
        mensagem: 'Lance pelo menos uma venda antes de finalizar o dia.',
      })
      return
    }

    setFeedback(null)
    setSubmitting(true)
    try {
      const res = await axios.post(`${API_URL}/fechamento`, { vendas: items })
      setSummary(res.data)
    } catch (err) {
      console.error(err)
      setFeedback({
        tone: 'alert',
        mensagem: 'Erro ao salvar vendas. Confira a conexão com o servidor e tente de novo.',
      })
    } finally {
      setSubmitting(false)
    }
  }

  const copyToWhatsApp = () => {
    if (!summary) return
    const statusLabel = summary.status_meta === 'saudavel' ? '✅ Saudável'
      : summary.status_meta === 'atencao' ? '⚠️ Atenção'
      : summary.status_meta === 'alerta' ? '🚨 Alerta'
      : '📭 Sem vendas'
    const topLines = (summary.top_skus || []).slice(0, 5).map((s: any) =>
      `• ${s.nome} [${s.classe_abc}${s.classe_xyz}] — ${formatNumber(s.quantidade, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}un / ${formatCurrency(s.receita)}`
    ).join('\n')
    const anomaliaLines = (summary.anomalias || []).slice(0, 5).map((a: any) =>
      `• ${a.severidade === 'alta' ? '🔴' : '🟡'} ${a.descricao}`
    ).join('\n')

    const text =
      `📊 *Fechamento ${summary.data}*\n\n` +
      `Status: ${statusLabel}\n` +
      `💰 Faturamento: ${formatCurrency(summary.faturamento_dia)}\n` +
      `🎯 Margem: ${formatPercent(summary.margem_dia)} (média 7d: ${formatPercent(summary.margem_media_7d)})\n` +
      `📈 Variação vs 7d: ${formatPercent(summary.variacao_faturamento_7d_pct, { scale: 1 })}\n` +
      `📦 SKUs vendidos: ${summary.total_skus_vendidos}/${summary.total_skus_cadastrados} · Rupturas: ${summary.rupturas}\n\n` +
      (topLines ? `*Top SKUs:*\n${topLines}\n\n` : '') +
      (anomaliaLines ? `*Anomalias:*\n${anomaliaLines}` : '')

    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (summary) {
    return (
      <AnaliseFechamentoView
        analise={summary}
        onCopy={copyToWhatsApp}
        copied={copied}
        onReset={() => { setSummary(null); setSalesItems({}); setSalesPrices({}); }}
      />
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <header className="flex justify-between items-center">
        <div>
          <h2 className="headline text-4xl tracking-editorial mb-2">Fechamento de Vendas Diárias</h2>
          <p className="text-slate-500">Lance as quantidades vendidas hoje para baixar o estoque ou importe o relatório CSV.</p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={() => setImportOpen(true)}
            className="bg-white text-blue-600 border border-blue-200 px-6 py-3 rounded-xl font-bold hover:bg-blue-50 transition-all flex items-center gap-2"
          >
            <Clipboard size={20} /> Importar CSV
          </button>
          <button
            onClick={handleFechamento}
            disabled={submitting}
            className="bg-emerald-600 text-white px-8 py-3 rounded-xl font-bold hover:bg-emerald-700 shadow-lg shadow-emerald-600/20 transition-all active:scale-95 flex items-center gap-2"
          >
            <Save size={20} /> Finalizar Dia
          </button>
        </div>
      </header>

      {importOpen && (
        <ImportCSVModal
          grupos={grupos}
          produtosExistentes={produtos}
          onClose={() => setImportOpen(false)}
          onCommitted={handleImportConcluido}
        />
      )}

      <FeedbackBanner feedback={feedback} onDismiss={() => setFeedback(null)} />

      {loadingProdutos && (
        <EmptyState variant="loading" title="Carregando produtos…" />
      )}

      {!loadingProdutos && produtos.length === 0 && (
        <div className="claude-card p-8 text-center">
          <div className="inline-flex w-14 h-14 rounded-2xl bg-[color:var(--claude-coral-soft)]/30 items-center justify-center mb-4">
            <FileText className="text-[color:var(--claude-coral)]" size={26} />
          </div>
          <h3 className="headline text-2xl tracking-editorial mb-2">Comece importando o relatório do ERP</h3>
          <p className="text-sm text-[color:var(--claude-stone)] max-w-2xl mx-auto leading-relaxed">
            Exporte o relatório de vendas do seu sistema (formato <span className="font-mono">.csv</span>) e
            anexe aqui. A importação é segura: nada é gravado antes de você revisar o resumo.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 max-w-3xl mx-auto mt-6 text-left">
            <div className="p-3 rounded-xl border border-[color:var(--border)] bg-white">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-6 h-6 rounded-full bg-[color:var(--claude-cream-deep)] text-[color:var(--claude-ink)] text-xs font-bold flex items-center justify-center">1</span>
                <p className="text-[11px] uppercase tracking-widest text-[color:var(--claude-stone)] font-semibold">Anexar</p>
              </div>
              <p className="text-xs text-[color:var(--claude-stone)] leading-snug">
                Você seleciona o CSV do ERP. Aceitamos o relatório dinâmico padrão.
              </p>
            </div>
            <div className="p-3 rounded-xl border border-[color:var(--border)] bg-white">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-6 h-6 rounded-full bg-[color:var(--claude-cream-deep)] text-[color:var(--claude-ink)] text-xs font-bold flex items-center justify-center">2</span>
                <p className="text-[11px] uppercase tracking-widest text-[color:var(--claude-stone)] font-semibold">Conferir</p>
              </div>
              <p className="text-xs text-[color:var(--claude-stone)] leading-snug">
                Mostramos quantos dias, vendas e clientes foram detectados. Linhas estranhas ficam de fora.
              </p>
            </div>
            <div className="p-3 rounded-xl border border-[color:var(--border)] bg-white">
              <div className="flex items-center gap-2 mb-1">
                <span className="w-6 h-6 rounded-full bg-[color:var(--claude-cream-deep)] text-[color:var(--claude-ink)] text-xs font-bold flex items-center justify-center">3</span>
                <p className="text-[11px] uppercase tracking-widest text-[color:var(--claude-stone)] font-semibold">Confirmar</p>
              </div>
              <p className="text-xs text-[color:var(--claude-stone)] leading-snug">
                Importa 1 dia ou todos. Cada dia substitui apenas o seu próprio fechamento.
              </p>
            </div>
          </div>

          <div className="text-[11px] text-[color:var(--claude-stone)] mt-5">
            O que você passa a ver depois de importar: faturamento e margem por dia, ranking de clientes e top compradores por produto.
          </div>

          <div className="flex gap-3 justify-center mt-6">
            <button
              onClick={() => setImportOpen(true)}
              className="bg-[color:var(--claude-ink)] text-white px-6 py-3 rounded-xl font-bold hover:opacity-90 transition-all flex items-center gap-2"
            >
              <Clipboard size={18} /> Importar CSV agora
            </button>
            <a
              href="#"
              onClick={(e) => { e.preventDefault(); }}
              className="px-6 py-3 rounded-xl font-medium text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)] transition-colors text-sm self-center"
            >
              Ou cadastrar produtos manualmente
            </a>
          </div>
        </div>
      )}

      {produtos.length > 0 && (
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Produto</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest w-48">Preço Unit. (R$)</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest w-48 text-center">Qtd Vendida</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {produtos.length > 0 ? produtos.map(p => (
              <tr key={p.id} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4 text-sm font-bold text-slate-900">{p.nome}</td>
                <td className="px-6 py-4">
                  <input 
                    type="number" step="0.01"
                    className="w-full bg-slate-50 p-2 rounded-lg border border-slate-200 font-bold text-slate-600 outline-none focus:bg-white focus:ring-2 focus:ring-blue-500"
                    value={salesPrices[p.id] !== undefined ? salesPrices[p.id] : p.preco_venda.toFixed(2)}
                    onChange={(e) => handlePriceChange(p.id, e.target.value)}
                  />
                </td>
                <td className="px-6 py-4">
                  <input 
                    type="number" step="0.001" placeholder="0.000"
                    className="w-full bg-slate-50 p-2.5 rounded-lg border border-slate-200 text-center font-bold outline-none focus:bg-white focus:ring-2 focus:ring-emerald-500 transition-all"
                    value={salesItems[p.id] !== undefined ? salesItems[p.id] : ''}
                    onChange={(e) => handleQtyChange(p.id, e.target.value)}
                  />
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan={3} className="px-6 py-8">
                  <EmptyState variant="empty" compact title="Nenhum produto cadastrado para venda." />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      )}
    </div>
  )
}


// ============================================================================
// ImportCSVModal — upload + preview + resolução + commit
// Fluxo: estado 'upload' → 'preview' → 'feito'
// ============================================================================
// ============================================================================
// Tipos auxiliares e agrupamento de produtos faltantes (camada de conveniencia
// para o passo de cadastro/validacao). NAO altera o motor de importacao —
// resolucoes continuam sendo um Record<idx, resolucao> consumido pelo backend
// linha a linha. Aqui apenas projetamos uma vista agregada por chave estavel
// (codigo CSV ou nome normalizado) para reduzir retrabalho.
// ============================================================================
type GrupoProdutoFaltante = {
  chave: string                          // estavel, ex.: 'codigo:1234' ou 'nome:CORANT'
  tipo: 'sem_match_conflito' | 'sem_custo'
  // Identidade do produto neste lote
  nome: string                           // nome do CSV (ou cadastrado, se sem_custo)
  codigo: string | null                  // codigo do CSV (ou cadastrado)
  produto_id: number | null              // preenchido quando ja existe (sem_custo / conflito)
  // Resumo operacional do lote (apoio visual; nao altera persistencia)
  ocorrencias: number
  quantidade_total: number
  preco_medio_ponderado: number          // ponderado por quantidade
  // idxs das linhas do preview que pertencem a este grupo
  idxs: number[]
  linhas: any[]                          // ref direta pras linhas, para "Revisar ocorrencias"
}

function normalizarChave(s: string): string {
  // Range ̀-ͯ cobre os "combining diacritical marks" (acentos
  // decompostos via NFD). Escape unicode explicito eh mais robusto contra
  // editores/IDEs que possam reformatar literais invisiveis no source.
  return (s || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .trim()
    .toLowerCase()
    .replace(/\s+/g, ' ')
}

/**
 * Remove o sufixo "(× N pedidos)" que o backend acrescenta ao nome_csv para
 * sinalizar consolidacao de pedidos. Sem essa limpeza, "Cadastrar novo"
 * pre-popularia o nome do produto com o sufixo (ja observado em uso real:
 * 33/65 = 51% dos faltantes do CSV de homologacao tinham o sufixo, e
 * 1 produto ja estava cadastrado no banco como "CEBOLA BRANCA CX2 (× 6 pedidos)").
 *
 * O caractere usado pelo backend eh em-dash (U+2014), nao ×. O regex aceita
 * qualquer nao-letra entre parenteses + N pedidos[s] no final, para cobrir
 * variantes de geracao do servidor sem ficar acoplado a um codepoint
 * especifico.
 */
function limparSufixoConsolidacao(nome: string): string {
  if (!nome) return nome
  return nome.replace(/\s*\([^)]*pedidos?\s*\)\s*$/i, '').trim()
}

/**
 * Sugere o produto cadastrado mais provavel para um grupo faltante.
 * NAO auto-confirma: retorna apenas o id da sugestao para pre-selecionar
 * no select de "Associar". O usuario sempre tem que confirmar/trocar.
 *
 * Ranking (do mais forte para o mais fraco):
 *   1. Codigo ERP exato         — match canonico, raramente falso-positivo
 *   2. Nome normalizado exato   — typo improvavel
 *   3. Substring (qualquer dir) — fallback fraco mas util pra "AÇAFRAO" -> "AÇAFRAO PIATA"
 *
 * Retorna null se nenhum dos rankings encontrar match — usuario abre o
 * select normalmente e escolhe manualmente.
 */
function sugerirProdutoExistente(
  grupo: GrupoProdutoFaltante,
  produtos: any[],
): number | null {
  if (!produtos || produtos.length === 0) return null
  // Limpa o sufixo "(× N pedidos)" antes de normalizar, senao a busca por
  // nome exato/substring jamais bateria com produtos cadastrados sem o
  // sufixo (que eh o caso correto).
  const nomeAlvo = normalizarChave(limparSufixoConsolidacao(grupo.nome))
  const codAlvo = grupo.codigo ? normalizarChave(grupo.codigo) : null

  // 1) codigo ERP exato (canonical)
  if (codAlvo) {
    const m = produtos.find((p: any) => p.codigo && normalizarChave(p.codigo) === codAlvo)
    if (m) return m.id
  }
  // 2) nome normalizado exato
  if (nomeAlvo) {
    const m = produtos.find((p: any) => normalizarChave(p.nome) === nomeAlvo)
    if (m) return m.id
  }
  // 3) substring em qualquer direcao (mais fraco — usuario revisa)
  if (nomeAlvo && nomeAlvo.length >= 4) {
    const m = produtos.find((p: any) => {
      const pn = normalizarChave(p.nome)
      return pn.length >= 4 && (pn.includes(nomeAlvo) || nomeAlvo.includes(pn))
    })
    if (m) return m.id
  }
  return null
}

function agruparProdutosFaltantes(linhas: any[]): GrupoProdutoFaltante[] {
  const mapa = new Map<string, GrupoProdutoFaltante>()
  for (const l of linhas) {
    let chave: string
    let tipo: GrupoProdutoFaltante['tipo']
    if (l.status === 'sem_custo') {
      // Produto ja cadastrado — agrupa por produto_id
      chave = `pid:${l.produto_id}`
      tipo = 'sem_custo'
    } else if (l.status === 'sem_match' || l.status === 'conflito') {
      // Produto sem cadastro — agrupa por codigo CSV (preferencia) ou nome
      const k = l.codigo_csv ? `codigo:${normalizarChave(l.codigo_csv)}` : `nome:${normalizarChave(l.nome_csv)}`
      chave = k
      tipo = 'sem_match_conflito'
    } else {
      continue // ok, fora_periodo, erro nao entram neste passo
    }
    // O backend ja consolida pedidos do CSV em 1 linha por produto (campo
    // l.ocorrencias = N pedidos reais). Reusamos esse N em vez de contar +1
    // para que o card mostre "5 pedidos" em vez de "1 ocorrencia". Quando 2
    // linhas distintas do preview compartilham a mesma chave (caso raro, ex.
    // mesmo nome normalizado sem codigo), os valores somam corretamente.
    const ocorrenciasLinha = Number(l.ocorrencias || 1)
    const existente = mapa.get(chave)
    if (existente) {
      existente.ocorrencias += ocorrenciasLinha
      existente.quantidade_total += Number(l.quantidade || 0)
      existente.idxs.push(l.idx)
      existente.linhas.push(l)
      // Acumula receita pra recalcular preco medio ponderado depois
      ;(existente as any)._receita_acum =
        ((existente as any)._receita_acum || 0) + Number(l.total || 0)
    } else {
      mapa.set(chave, {
        chave,
        tipo,
        nome: l.produto_nome || l.nome_csv,
        codigo: l.codigo_csv || (l.produto_codigo ?? null),
        produto_id: l.produto_id ?? null,
        ocorrencias: ocorrenciasLinha,
        quantidade_total: Number(l.quantidade || 0),
        preco_medio_ponderado: 0,
        idxs: [l.idx],
        linhas: [l],
        // accumulator interno
        ...({ _receita_acum: Number(l.total || 0) } as any),
      })
    }
  }
  // Calcula preco medio ponderado (receita / quantidade)
  const out: GrupoProdutoFaltante[] = []
  for (const g of mapa.values()) {
    const receita = (g as any)._receita_acum || 0
    g.preco_medio_ponderado = g.quantidade_total > 0 ? receita / g.quantidade_total : 0
    delete (g as any)._receita_acum
    out.push(g)
  }
  // Ordena: sem_match primeiro (precisam de mais decisao), depois sem_custo
  out.sort((a, b) => {
    if (a.tipo !== b.tipo) return a.tipo === 'sem_match_conflito' ? -1 : 1
    return b.ocorrencias - a.ocorrencias
  })
  return out
}

function grupoEstaResolvido(grupo: GrupoProdutoFaltante, resolucoes: Record<number, any>): boolean {
  // Olha so o primeiro idx — propagamos sempre, entao se 1 esta ok, todos estao
  const r = resolucoes[grupo.idxs[0]]
  if (!r) return false
  if (r.acao === 'ignorar') return true
  if (r.acao === 'criar') {
    return !!(r.novo_nome && r.novo_grupo_id && r.novo_preco_venda && r.novo_custo && Number(r.novo_custo) > 0)
  }
  if (r.acao === 'associar') {
    return !!r.produto_id
  }
  if (r.acao === 'corrigir_custo') {
    return !!r.novo_custo && Number(r.novo_custo) > 0
  }
  return false
}

// Persistencia local do progresso do passo de produtos faltantes — chave
// estavel por arquivo (nome+tamanho+ultima modificacao). Evita perda
// acidental se o usuario fechar o modal antes do commit.
const STORAGE_PREFIX = 'csvimport:'
const STORAGE_TTL_MS = 7 * 24 * 3600 * 1000 // 7 dias

function chaveStorageDoArquivo(f: File | null): string | null {
  if (!f) return null
  return `${STORAGE_PREFIX}${f.name}:${f.size}:${f.lastModified}`
}

function ImportCSVModal({ grupos, produtosExistentes, onClose, onCommitted }: any) {
  const hoje = new Date().toISOString().slice(0, 10)
  const [estado, setEstado] = useState<'upload' | 'auditoria' | 'produtos_faltantes' | 'preview' | 'sucesso_multi'>('upload')
  const [arquivo, setArquivo] = useState<File | null>(null)
  const [dataAlvo, setDataAlvo] = useState<string>(hoje)
  const [preview, setPreview] = useState<any | null>(null)
  const [auditoria, setAuditoria] = useState<any | null>(null)
  const [resultadoMulti, setResultadoMulti] = useState<any | null>(null)
  const [bloqueiosMulti, setBloqueiosMulti] = useState<any[] | null>(null)
  const [resolucoes, setResolucoes] = useState<Record<number, any>>({})
  const [submitting, setSubmitting] = useState(false)
  const [erro, setErro] = useState<string | null>(null)
  // Sinaliza que o progresso foi restaurado de localStorage neste mount —
  // banner some apos primeira interacao do usuario.
  const [progressoRestaurado, setProgressoRestaurado] = useState<{ count: number } | null>(null)

  const containerRef = useRef<HTMLDivElement>(null)
  const titleId = 'importcsv-title'

  // Limpeza one-shot: descarta entries antigas (>7 dias) ao montar o modal.
  // Mantem localStorage enxuto sem job dedicado.
  useEffect(() => {
    try {
      const now = Date.now()
      const stale: string[] = []
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i)
        if (!k || !k.startsWith(STORAGE_PREFIX)) continue
        try {
          const v = JSON.parse(localStorage.getItem(k) || '{}')
          if (!v.ts || (now - v.ts) > STORAGE_TTL_MS) stale.push(k)
        } catch {
          stale.push(k)
        }
      }
      stale.forEach((k) => localStorage.removeItem(k))
    } catch {}
  }, [])

  // Persiste resolucoes + dataAlvo enquanto o modal esta em uso. Salva a
  // cada mudanca — chamadas a localStorage.setItem sao baratas e o volume
  // por lote eh modesto (~kbs). O save so vale quando ha arquivo + preview.
  useEffect(() => {
    if (!arquivo || !preview) return
    if (Object.keys(resolucoes).length === 0) return
    try {
      const key = chaveStorageDoArquivo(arquivo)
      if (!key) return
      localStorage.setItem(
        key,
        JSON.stringify({ resolucoes, dataAlvo, ts: Date.now() }),
      )
    } catch {}
  }, [resolucoes, dataAlvo, arquivo, preview])

  // ESC fecha o modal — mas nunca durante uma operacao em andamento (upload,
  // commit, multi-data) e nunca na tela de sucesso (a saida certa eh "Ver
  // analise" ou "Fechar", nao um atalho que pula a confirmacao visual).
  useEscapeKey(onClose, { disabled: submitting || estado === 'sucesso_multi' })
  useModalA11y(containerRef)

  // FASE 1: Upload → Auditoria (inspecao SEM gravar nada)
  const enviarAuditoria = async () => {
    if (!arquivo) { setErro('Selecione um arquivo CSV.'); return }
    setErro(null)
    setBloqueiosMulti(null)
    setSubmitting(true)
    try {
      const form = new FormData()
      form.append('arquivo', arquivo)
      const res = await axios.post(`${API_URL}/fechamento/auditoria-csv`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setAuditoria(res.data)
      // Default da data alvo: a data mais recente do CSV (se houver 1+ datas)
      if (res.data.datas_detectadas?.length) {
        setDataAlvo(res.data.datas_detectadas[res.data.datas_detectadas.length - 1])
      }
      setEstado('auditoria')
    } catch (e: any) {
      setErro(e?.response?.data?.detail || 'Erro ao auditar o arquivo.')
    } finally {
      setSubmitting(false)
    }
  }

  // FASE 2A: Auditoria → Importar TODAS as datas (multi-data direto, sem revisao linha-a-linha)
  const importarTodasDatas = async () => {
    if (!arquivo) return
    setErro(null)
    setBloqueiosMulti(null)
    setSubmitting(true)
    try {
      const form = new FormData()
      form.append('arquivo', arquivo)
      const res = await axios.post(`${API_URL}/fechamento/importar-multi-data`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResultadoMulti(res.data)
      setEstado('sucesso_multi')
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      // Backend retorna detail estruturado quando ha pendencias bloqueantes
      if (detail && typeof detail === 'object' && detail.tipo === 'pendencias_multi_data') {
        setBloqueiosMulti(detail.bloqueios)
        setErro(null) // erro vira painel proprio, nao texto no rodape
      } else {
        setErro(typeof detail === 'string' ? detail : 'Erro ao importar as datas. Tente revisar 1 dia por vez.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  // FASE 2B: Auditoria → (produtos_faltantes |) Preview
  // Baixa o preview e roteia para o passo de produtos faltantes se houver
  // pendencias agrupaveis. Sem pendencias, vai direto para o preview classico.
  const irParaPreview = async () => {
    if (!arquivo) { setErro('Selecione um arquivo CSV.'); return }
    if (!dataAlvo) { setErro('Selecione a data do fechamento.'); return }
    setErro(null)
    setSubmitting(true)
    try {
      const form = new FormData()
      form.append('arquivo', arquivo)
      form.append('data', dataAlvo)
      const res = await axios.post(`${API_URL}/fechamento/importar-csv/preview`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setPreview(res.data)
      let iniciais: Record<number, any> = {}
      for (const l of res.data.linhas) {
        if (l.status === 'erro') {
          iniciais[l.idx] = { idx: l.idx, acao: 'ignorar' }
        } else if (l.status !== 'ok') {
          iniciais[l.idx] = { idx: l.idx, acao: 'ignorar' }
        }
      }
      // Restaura progresso anterior do mesmo arquivo (se existir e nao
      // expirou). Mescla por cima dos defaults — sem sobrescrever entries
      // de erro/ok-only que nao existem no salvo.
      let restoredCount = 0
      try {
        const key = chaveStorageDoArquivo(arquivo)
        if (key) {
          const saved = localStorage.getItem(key)
          if (saved) {
            const parsed = JSON.parse(saved)
            if (parsed?.resolucoes && parsed?.ts &&
                (Date.now() - parsed.ts) < STORAGE_TTL_MS) {
              for (const [idxStr, r] of Object.entries(parsed.resolucoes as Record<string, any>)) {
                const idx = Number(idxStr)
                const inicial = iniciais[idx]
                // Conta como "restaurada" toda resolucao que difere do
                // default 'ignorar' OU que foi explicitamente decidida
                // antes (mesmo 'ignorar' pode ter sido decisao consciente).
                if (!inicial || r.acao !== inicial.acao
                    || r.produto_id || r.novo_nome || r.novo_custo) {
                  restoredCount++
                }
              }
              iniciais = { ...iniciais, ...parsed.resolucoes }
              if (parsed.dataAlvo && parsed.dataAlvo !== dataAlvo) {
                setDataAlvo(parsed.dataAlvo)
              }
            }
          }
        }
      } catch {}
      setResolucoes(iniciais)
      if (restoredCount > 0) setProgressoRestaurado({ count: restoredCount })
      // Se ha pendencias agrupaveis (sem_match / conflito / sem_custo), ofere
      // ce o passo de cadastro/validacao agrupada. Senao, segue direto pro
      // preview tradicional (linha-a-linha).
      const grupos = agruparProdutosFaltantes(res.data.linhas)
      setEstado(grupos.length > 0 ? 'produtos_faltantes' : 'preview')
    } catch (e: any) {
      setErro(e?.response?.data?.detail || 'Erro ao processar o arquivo.')
    } finally {
      setSubmitting(false)
    }
  }

  const atualizarResolucao = (idx: number, patch: any) => {
    setResolucoes((prev) => ({ ...prev, [idx]: { ...(prev[idx] || { idx }), ...patch } }))
  }

  // Aplica uma mesma resolucao a TODOS os idx de um grupo de produto faltante.
  // Esta eh a chave da reducao de retrabalho: usuario decide 1 vez por produto
  // e o sistema replica para todas as ocorrencias daquele produto no lote.
  //
  // Higiene: ao trocar de acao (ex.: associar -> criar), descarta campos
  // especificos da acao anterior. Sem isso, um produto_id de 'associar'
  // sobrevive como campo sujo dentro de uma resolucao 'criar', poluindo o
  // payload enviado ao backend.
  const aplicarResolucaoNoGrupo = (idxs: number[], patch: any) => {
    setResolucoes((prev) => {
      const novo = { ...prev }
      for (const idx of idxs) {
        const anterior = novo[idx] || { idx }
        const trocandoAcao = patch.acao && patch.acao !== anterior.acao
        const baseLimpa = trocandoAcao ? { idx, acao: patch.acao } : anterior
        novo[idx] = { ...baseLimpa, ...patch, idx }
      }
      return novo
    })
  }

  // Linhas "criar" sem custo > 0: bloqueia no front antes de bater no server,
  // porque venda com custo=0 vira margem 100% (dado contábil errado).
  const criarSemCusto = Object.values(resolucoes).filter((r: any) =>
    r.acao === 'criar' && (!r.novo_custo || Number(r.novo_custo) <= 0)
  ) as any[]
  const criarSemCampos = Object.values(resolucoes).filter((r: any) =>
    r.acao === 'criar' && (!r.novo_nome || !r.novo_grupo_id || !r.novo_preco_venda || !r.novo_custo)
  ) as any[]
  const associarSemProduto = Object.values(resolucoes).filter((r: any) =>
    r.acao === 'associar' && !r.produto_id
  ) as any[]
  const corrigirSemCusto = Object.values(resolucoes).filter((r: any) =>
    r.acao === 'corrigir_custo' && (!r.novo_custo || Number(r.novo_custo) <= 0)
  ) as any[]
  // Linhas status=sem_custo que o usuário ainda não decidiu (sem resolução
  // salva no state) também bloqueiam — exigem escolha explícita.
  const semCustoNaoResolvidas = (preview?.linhas || []).filter(
    (l: any) => l.status === 'sem_custo' && !resolucoes[l.idx]
  ) as any[]
  const podeCommitar =
    criarSemCusto.length === 0 &&
    criarSemCampos.length === 0 &&
    associarSemProduto.length === 0 &&
    corrigirSemCusto.length === 0 &&
    semCustoNaoResolvidas.length === 0

  const motivoBloqueio = (() => {
    if (podeCommitar) return ''
    const partes: string[] = []
    if (criarSemCampos.length) {
      const detalhes = criarSemCampos.map((r: any) => {
        const faltando = [
          !r.novo_nome && 'nome',
          !r.novo_grupo_id && 'grupo',
          !r.novo_preco_venda && 'preço',
          !r.novo_custo && 'custo',
        ].filter(Boolean).join(', ')
        return `linha ${r.idx}: ${faltando}`
      }).join(' | ')
      partes.push(`Criar com campos faltando — ${detalhes}`)
    }
    if (criarSemCusto.length && !criarSemCampos.length) {
      partes.push(`${criarSemCusto.length} linha(s) criar com custo <= 0`)
    }
    if (associarSemProduto.length) {
      partes.push(`${associarSemProduto.length} linha(s) associar sem produto`)
    }
    if (corrigirSemCusto.length) {
      partes.push(`${corrigirSemCusto.length} linha(s) corrigir custo sem valor`)
    }
    if (semCustoNaoResolvidas.length) {
      partes.push(`${semCustoNaoResolvidas.length} linha(s) "sem custo" não resolvidas`)
    }
    return partes.join(' · ')
  })()

  const commitar = async () => {
    if (!preview) return
    if (!podeCommitar) {
      setErro(motivoBloqueio || 'Há pendências nas resoluções.')
      return
    }
    setErro(null)
    setSubmitting(true)
    try {
      const resolucoesArr = Object.values(resolucoes)
      const payload = {
        data_alvo: dataAlvo,
        linhas: preview.linhas,
        resolucoes: resolucoesArr,
      }
      await axios.post(`${API_URL}/fechamento/importar-csv/commit`, payload)
      // Limpa o storage do arquivo apos commit bem-sucedido. Nova importacao
      // do mesmo arquivo (raro mas possivel) parte de zero.
      try {
        const key = chaveStorageDoArquivo(arquivo)
        if (key) localStorage.removeItem(key)
      } catch {}
      onCommitted(dataAlvo)
    } catch (e: any) {
      setErro(e?.response?.data?.detail || 'Erro ao finalizar a importação.')
    } finally {
      setSubmitting(false)
    }
  }

  // Total de passos da jornada: 4 quando ha produtos faltantes pra resolver,
  // 3 quando o lote ja vem todo reconhecido (passo intermediario nao aparece).
  // A contagem so muda DEPOIS que o preview eh baixado — ate la, assume 3.
  const totalPassos = preview && agruparProdutosFaltantes(preview.linhas).length > 0 ? 4 : 3

  // Prontidao da fase produtos_faltantes: todos os grupos precisam estar
  // resolvidos (associar/criar/corrigir_custo com campos completos OU ignorar
  // explicito) antes de avancar para a revisao linha-a-linha.
  const gruposFaltantesAtuais = preview ? agruparProdutosFaltantes(preview.linhas) : []
  const gruposPendentes = gruposFaltantesAtuais.filter(
    (g: GrupoProdutoFaltante) => !grupoEstaResolvido(g, resolucoes)
  )
  const podeAvancarPF = gruposPendentes.length === 0

  // Estado limite: todos os grupos faltantes resolvidos como 'ignorar'.
  // Avancar eh permitido (decisao consciente do usuario) mas vale aviso —
  // pode ser que ele queira voltar e revisar antes de importar so vendas
  // de produtos ja reconhecidos.
  const todosFaltantesIgnorados = gruposFaltantesAtuais.length > 0 &&
    gruposFaltantesAtuais.every(
      (g: GrupoProdutoFaltante) => resolucoes[g.idxs[0]]?.acao === 'ignorar'
    )

  const tituloFase = (() => {
    switch (estado) {
      case 'upload': return 'Selecionar o arquivo'
      case 'auditoria': return 'Conferir o que foi lido'
      case 'produtos_faltantes': return 'Cadastrar e confirmar produtos'
      case 'preview': return 'Revisar e importar vendas'
      case 'sucesso_multi': return 'Importação concluída'
    }
  })()
  const subtituloFase = (() => {
    switch (estado) {
      case 'upload': return 'Nada será gravado nesta etapa.'
      case 'auditoria': return 'Você ainda não importou — apenas conferimos o arquivo.'
      case 'produtos_faltantes': return 'Resolva 1 vez por produto. Depois disso aplicamos a todas as ocorrências no lote.'
      case 'preview': return 'Confira as linhas e finalize. As resoluções já foram aplicadas.'
      case 'sucesso_multi': return 'As vendas já foram gravadas.'
    }
  })()
  const passoFase = (() => {
    switch (estado) {
      case 'upload': return `PASSO 1 DE ${totalPassos}`
      case 'auditoria': return `PASSO 2 DE ${totalPassos}`
      case 'produtos_faltantes': return `PASSO 3 DE ${totalPassos}`
      case 'preview': return totalPassos === 4 ? 'PASSO 4 DE 4' : 'PASSO 3 DE 3'
      case 'sucesso_multi': return 'CONCLUÍDO'
    }
  })()

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-6"
      onClick={() => {
        // Click no backdrop fecha — exceto durante operacao critica e na tela de
        // sucesso (onde a saida certa eh "Ver analise" ou "Fechar").
        if (!submitting && estado !== 'sucesso_multi') onClose()
      }}
    >
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="bg-white rounded-3xl border border-slate-200 shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header — segue padrao Fraunces editorial usado em todos os modulos */}
        <div className="p-6 border-b border-[color:var(--border)] flex items-center justify-between">
          <div>
            <p className="section-label mb-1">{passoFase}</p>
            <h3 id={titleId} className="headline text-2xl tracking-editorial">{tituloFase}</h3>
            <p className="text-xs text-[color:var(--claude-stone)] mt-1">{subtituloFase}</p>
          </div>
          <button
            onClick={onClose}
            disabled={submitting}
            className="text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)] p-1 disabled:opacity-50"
            title="Fechar sem importar"
            aria-label="Fechar"
          >
            <X size={22} />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {estado === 'upload' && (
            <UploadFase
              arquivo={arquivo}
              onArquivo={setArquivo}
              dataAlvo={dataAlvo}
              onDataAlvo={setDataAlvo}
            />
          )}
          {estado === 'auditoria' && auditoria && (
            <AuditoriaFase
              auditoria={auditoria}
              dataAlvo={dataAlvo}
              onDataAlvo={setDataAlvo}
              bloqueiosMulti={bloqueiosMulti}
              onIrParaPreviewDoDia={(d: string) => {
                setDataAlvo(d)
                setBloqueiosMulti(null)
                irParaPreview()
              }}
            />
          )}
          {estado === 'produtos_faltantes' && preview && (
            <ProdutosFaltantesFase
              preview={preview}
              resolucoes={resolucoes}
              onAplicarGrupo={aplicarResolucaoNoGrupo}
              produtosExistentes={produtosExistentes}
              grupos={grupos}
              progressoRestaurado={progressoRestaurado}
              onDispensarBanner={() => setProgressoRestaurado(null)}
            />
          )}
          {estado === 'preview' && preview && (
            <PreviewFase
              preview={preview}
              resolucoes={resolucoes}
              onResolucao={atualizarResolucao}
              produtosExistentes={produtosExistentes}
              grupos={grupos}
            />
          )}
          {estado === 'sucesso_multi' && resultadoMulti && (
            <SucessoMultiFase resultado={resultadoMulti} />
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="text-sm max-w-[60%]">
            {erro && <span className="text-rose-600 font-semibold">{erro}</span>}
            {!erro && estado === 'preview' && motivoBloqueio && (
              <span className="text-amber-700 font-semibold text-xs">⚠ {motivoBloqueio}</span>
            )}
            {!erro && estado === 'produtos_faltantes' && !podeAvancarPF && (
              <span className="text-amber-700 font-semibold text-xs">
                ⚠ {gruposPendentes.length} produto(s) ainda pendente(s)
              </span>
            )}
            {!erro && estado === 'produtos_faltantes' && podeAvancarPF && !todosFaltantesIgnorados && (
              <span className="text-[color:var(--claude-sage)] font-semibold text-xs">
                ✓ Todos os produtos resolvidos — pronto para revisar
              </span>
            )}
            {!erro && estado === 'produtos_faltantes' && podeAvancarPF && todosFaltantesIgnorados && (
              <span className="text-amber-700 font-semibold text-xs">
                ⚠ Todos os faltantes ignorados — só vendas de produtos já reconhecidos seguirão
              </span>
            )}
          </div>
          <div className="flex gap-2">
            {estado === 'preview' && (
              <button
                onClick={() => {
                  // Se ha grupos faltantes, volta pra eles; senao, volta pra auditoria.
                  if (gruposFaltantesAtuais.length > 0) {
                    setEstado('produtos_faltantes')
                  } else {
                    setEstado('auditoria'); setPreview(null); setResolucoes({})
                  }
                }}
                className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900"
              >
                Voltar
              </button>
            )}
            {estado === 'produtos_faltantes' && (
              <button
                onClick={() => { setEstado('auditoria'); setPreview(null); setResolucoes({}) }}
                className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900"
              >
                Voltar
              </button>
            )}
            {estado === 'auditoria' && (
              <button
                onClick={() => { setEstado('upload'); setAuditoria(null); setBloqueiosMulti(null) }}
                className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900"
              >
                Voltar
              </button>
            )}
            {estado !== 'sucesso_multi' && (
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900"
              >
                Cancelar
              </button>
            )}
            {estado === 'upload' && (
              <button
                onClick={enviarAuditoria}
                disabled={submitting || !arquivo}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-xl font-bold text-sm hover:bg-blue-700 disabled:opacity-50 transition-all"
              >
                {submitting ? 'Conferindo…' : 'Conferir arquivo'}
              </button>
            )}
            {estado === 'auditoria' && auditoria && (
              <>
                <button
                  onClick={irParaPreview}
                  disabled={submitting}
                  className="bg-white text-blue-600 border border-blue-200 px-5 py-2.5 rounded-xl font-bold text-sm hover:bg-blue-50 disabled:opacity-50 transition-all"
                  title={`Vai pra revisão linha por linha apenas das vendas do dia ${dataAlvo}.`}
                >
                  {submitting ? 'Carregando…' : `Revisar apenas ${dataAlvo}`}
                </button>
                {auditoria.total_datas > 1 && (
                  <button
                    onClick={importarTodasDatas}
                    disabled={submitting || (auditoria.total_linhas_validas || 0) === 0 || !!bloqueiosMulti}
                    className="bg-emerald-600 text-white px-6 py-2.5 rounded-xl font-bold text-sm hover:bg-emerald-700 disabled:opacity-50 transition-all"
                    title={bloqueiosMulti
                      ? 'Há produtos não cadastrados — resolva 1 dia por vez antes de importar tudo.'
                      : 'Grava todas as datas em sequência. Funciona quando todos os produtos já estão cadastrados.'}
                  >
                    {submitting ? 'Importando…' : (
                      bloqueiosMulti
                        ? 'Bloqueado — revise os dias abaixo'
                        : `Importar todas as ${auditoria.total_datas} datas de uma vez`
                    )}
                  </button>
                )}
              </>
            )}
            {estado === 'produtos_faltantes' && (
              <button
                onClick={() => setEstado('preview')}
                disabled={!podeAvancarPF}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-xl font-bold text-sm hover:bg-blue-700 disabled:opacity-50 transition-all"
                title={podeAvancarPF
                  ? 'Avançar para a revisão linha-a-linha das vendas'
                  : `Resolva ${gruposPendentes.length} produto(s) pendente(s) para avançar`}
              >
                Avançar para revisão
              </button>
            )}
            {estado === 'preview' && (
              <button
                onClick={commitar}
                disabled={submitting || !podeCommitar}
                className="bg-emerald-600 text-white px-6 py-2.5 rounded-xl font-bold text-sm hover:bg-emerald-700 disabled:opacity-50 transition-all"
                title={motivoBloqueio || ''}
              >
                {submitting ? 'Importando…' : (preview?.ja_existe_fechamento ? 'Substituir e importar' : 'Confirmar importação')}
              </button>
            )}
            {estado === 'sucesso_multi' && (
              <>
                <button
                  onClick={onClose}
                  className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900"
                >
                  Fechar
                </button>
                <button
                  onClick={() => {
                    // Notifica RelatoriosPage do dia mais recente importado pra mostrar a analise
                    const datas = resultadoMulti?.datas_processadas || []
                    if (datas.length > 0) {
                      onCommitted(datas[datas.length - 1])
                    } else {
                      onClose()
                    }
                  }}
                  className="bg-emerald-600 text-white px-6 py-2.5 rounded-xl font-bold text-sm hover:bg-emerald-700 transition-all"
                >
                  Ver análise do último dia
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function UploadFase({ arquivo, onArquivo, dataAlvo, onDataAlvo }: any) {
  return (
    <div className="space-y-5 max-w-md mx-auto py-4">
      <div className="p-4 bg-[color:var(--claude-cream-deep)]/40 border border-[color:var(--border)] rounded-xl text-sm text-[color:var(--claude-ink)]">
        <p className="font-semibold mb-2">O que vai acontecer:</p>
        <ol className="space-y-1.5 text-[13px] text-[color:var(--claude-stone)] list-decimal list-inside">
          <li>Você anexa o arquivo (.csv exportado do seu ERP).</li>
          <li>Conferimos o conteúdo <b>sem gravar nada</b> — você vê quantas datas e quantas vendas existem.</li>
          <li>Se quiser, importa todas as datas de uma vez ou escolhe um dia específico.</li>
          <li>Se já houver fechamento da mesma data, ele será substituído pelo novo.</li>
        </ol>
      </div>

      <div>
        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Arquivo CSV</label>
        <input
          type="file"
          accept=".csv,text/csv"
          onChange={(e) => onArquivo(e.target.files?.[0] || null)}
          className="w-full mt-1 p-2.5 rounded-lg border border-slate-200 bg-white text-sm file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:bg-blue-50 file:text-blue-700 file:text-xs file:font-bold"
        />
        {arquivo && (
          <p className="text-[11px] text-slate-500 mt-1">
            {arquivo.name} · {formatNumber(arquivo.size / 1024, { minimumFractionDigits: 1, maximumFractionDigits: 1 })} KB
          </p>
        )}
      </div>

      <div>
        <label className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Data do fechamento</label>
        <input
          type="date"
          value={dataAlvo}
          onChange={(e) => onDataAlvo(e.target.value)}
          className="w-full mt-1 p-2.5 rounded-lg border border-slate-200 bg-white text-sm"
        />
        <p className="text-[11px] text-slate-500 mt-1">As vendas serão registradas neste dia. Dados em linhas com data diferente serão sinalizados no preview.</p>
      </div>
    </div>
  )
}

// ============================================================================
// AuditoriaFase — inspeção pré-commit (etapa 2 de 3)
// Mostra o que foi lido, descartado e alertado SEM gravar nada.
// ============================================================================

function AuditoriaFase({ auditoria, dataAlvo, onDataAlvo, bloqueiosMulti, onIrParaPreviewDoDia }: any) {
  const sevTone: Record<string, string> = {
    info: 'bg-slate-100 text-slate-700 border-slate-200',
    media: 'bg-amber-50 text-amber-800 border-amber-200',
    alta: 'bg-rose-50 text-rose-800 border-rose-200',
  }
  const statusLabelCurto: Record<string, string> = {
    sem_match: 'Produto não cadastrado',
    conflito: 'Conflito código vs nome',
    sem_custo: 'Produto sem custo',
    erro: 'Aritmética inconsistente',
  }
  return (
    <div className="space-y-5">
      {/* Painel de bloqueio (so quando o backend devolveu 422 com pendencias) */}
      {bloqueiosMulti && bloqueiosMulti.length > 0 && (
        <div className="rounded-xl border border-rose-200 bg-rose-50/60 p-5">
          <div className="flex items-start gap-3 mb-3">
            <div className="w-8 h-8 rounded-full bg-rose-100 flex items-center justify-center shrink-0 mt-0.5">
              <AlertCircle className="text-rose-600" size={18} />
            </div>
            <div>
              <p className="font-semibold text-rose-900">Não dá pra importar todas as datas ainda</p>
              <p className="text-xs text-rose-800/80 mt-0.5">
                Existem produtos no CSV que não têm cadastro no sistema (ou estão sem custo).
                A importação em lote precisa que tudo esteja resolvido. Use o fluxo
                <b> Revisar apenas DATA</b> abaixo para cada dia listado e cadastre os produtos no caminho.
              </p>
            </div>
          </div>
          <div className="space-y-3">
            {bloqueiosMulti.map((b: any) => (
              <div key={b.data} className="rounded-lg border border-rose-200 bg-white p-3">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-mono tabular-nums text-[color:var(--claude-ink)]">
                    {b.data} · <span className="font-semibold text-rose-700">{b.total_pendentes}</span> linha(s) pendente(s)
                  </p>
                  <button
                    onClick={() => onIrParaPreviewDoDia(b.data)}
                    className="text-xs font-bold text-blue-600 hover:text-blue-800 transition-colors"
                  >
                    Revisar este dia →
                  </button>
                </div>
                <ul className="text-xs space-y-1">
                  {b.linhas.map((l: any) => (
                    <li key={l.idx} className="flex items-center justify-between gap-2 py-0.5">
                      <span className="text-[color:var(--claude-stone)] truncate">
                        <span className="font-mono tabular-nums text-[color:var(--claude-ink)]">
                          {l.codigo_csv ? `${l.codigo_csv} ·` : ''}
                        </span>{' '}
                        {l.nome_csv}
                      </span>
                      <span className="text-[10px] uppercase tracking-widest text-rose-700 shrink-0">
                        {statusLabelCurto[l.status] || l.status}
                      </span>
                    </li>
                  ))}
                  {b.total_pendentes > b.linhas.length && (
                    <li className="text-[11px] italic text-[color:var(--claude-stone)] mt-1">
                      …e mais {b.total_pendentes - b.linhas.length} linha(s) neste dia
                    </li>
                  )}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
      {/* Resumo "headline" */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="claude-card p-4">
          <p className="section-label">Dias no arquivo</p>
          <p className="kpi-value text-2xl text-[color:var(--claude-ink)] mt-1">{auditoria.total_datas}</p>
          <p className="text-[11px] text-[color:var(--claude-stone)] mt-1">
            {(auditoria.datas_detectadas || []).join(' · ')}
          </p>
        </div>
        <div className="claude-card p-4">
          <p className="section-label">Vendas que serão importadas</p>
          <p className="kpi-value text-2xl text-[color:var(--claude-sage)] mt-1">
            {auditoria.total_linhas_validas}
          </p>
          <p className="text-[11px] text-[color:var(--claude-stone)] mt-1">
            de {auditoria.total_linhas_lidas} linhas lidas no total
          </p>
        </div>
        <div className="claude-card p-4">
          <p className="section-label">Linhas ignoradas</p>
          <p className={`kpi-value text-2xl mt-1 ${
            auditoria.total_linhas_descartadas > 0
              ? 'text-[color:var(--claude-amber)]'
              : 'text-[color:var(--claude-stone)]'
          }`}>
            {auditoria.total_linhas_descartadas}
          </p>
          <p className="text-[11px] text-[color:var(--claude-stone)] mt-1">
            cabeçalhos, rodapés e marcações de página
          </p>
        </div>
        <div className="claude-card p-4">
          <p className="section-label">Avisos</p>
          <p className={`kpi-value text-2xl mt-1 ${
            (auditoria.alertas?.length || 0) === 0
              ? 'text-[color:var(--claude-sage)]'
              : 'text-[color:var(--claude-amber)]'
          }`}>
            {auditoria.alertas?.length || 0}
          </p>
          <p className="text-[11px] text-[color:var(--claude-stone)] mt-1">
            {(auditoria.alertas?.length || 0) === 0 ? 'tudo dentro do esperado' : 'verificar antes de importar'}
          </p>
        </div>
      </div>

      {/* Resumo por dia */}
      {auditoria.resumo_por_dia && auditoria.resumo_por_dia.length > 0 && (
        <div className="claude-card overflow-hidden">
          <div className="px-4 py-3 border-b border-[color:var(--border)]">
            <p className="section-label">Resumo por dia</p>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-[color:var(--claude-cream-deep)]/40">
              <tr className="text-[10px] uppercase tracking-widest text-[color:var(--claude-stone)]">
                <th className="px-4 py-2 text-left">Data</th>
                <th className="px-4 py-2 text-right">Linhas</th>
                <th className="px-4 py-2 text-right">Quantidade</th>
                <th className="px-4 py-2 text-right">Valor líquido</th>
                <th className="px-4 py-2 text-right">SKUs</th>
                <th className="px-4 py-2 text-right">Clientes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[color:var(--border)]">
              {auditoria.resumo_por_dia.map((d: any) => (
                <tr key={d.data} className="hover:bg-[color:var(--claude-cream-deep)]/20">
                  <td className="px-4 py-2 font-mono tabular-nums">{d.data}</td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">{d.linhas}</td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">
                    {formatNumber(d.qtd_total, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">{formatCurrency(d.valor_total)}</td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">{d.skus_distintos}</td>
                  <td className="px-4 py-2 text-right font-mono tabular-nums">{d.clientes_distintos}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Motivos de descarte (se houver) */}
      {auditoria.motivos_descarte && auditoria.motivos_descarte.length > 0 && (
        <div className="claude-card p-4">
          <p className="section-label mb-1">Linhas que não viraram venda</p>
          <p className="text-[11px] text-[color:var(--claude-stone)] mb-3">
            Estas linhas existem no arquivo mas não são vendas reais — o sistema as ignora.
          </p>
          <ul className="space-y-1.5 text-sm">
            {auditoria.motivos_descarte.map((m: any) => (
              <li key={m.motivo} className="flex items-center justify-between text-[color:var(--claude-stone)]">
                <span>{m.label}</span>
                <span className="font-mono tabular-nums text-[color:var(--claude-ink)]">×{m.count}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Alertas */}
      {auditoria.alertas && auditoria.alertas.length > 0 && (
        <div className="space-y-2">
          {auditoria.alertas.map((a: any, i: number) => (
            <div key={i} className={`p-3 rounded-xl border text-sm ${sevTone[a.severidade] || sevTone.info}`}>
              <div className="flex items-center justify-between">
                <span className="font-medium">{a.label}</span>
                <span className="font-mono tabular-nums text-xs">×{a.count}</span>
              </div>
              {a.exemplos && a.exemplos.length > 0 && (
                <ul className="mt-2 text-xs space-y-0.5 opacity-80">
                  {a.exemplos.slice(0, 3).map((e: any, j: number) => (
                    <li key={j} className="font-mono tabular-nums">
                      cód {e.codigo} → {(e.nomes || []).join(' / ')}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Unidades detectadas */}
      {auditoria.unidades_detectadas && auditoria.unidades_detectadas.length > 0 && (
        <div className="text-xs text-[color:var(--claude-stone)]">
          <span className="uppercase tracking-widest mr-2">Unidades:</span>
          {auditoria.unidades_detectadas.map((u: any, i: number) => (
            <span key={u.unidade} className="font-mono tabular-nums">
              {i > 0 && ' · '}
              {u.unidade} <span className="text-[color:var(--claude-stone)]/70">({u.count})</span>
            </span>
          ))}
        </div>
      )}

      {/* Seleção de data quando >1 data */}
      {auditoria.total_datas > 1 && (
        <div className="claude-card p-4 bg-[color:var(--claude-cream-deep)]/40">
          <p className="section-label mb-2">Como você quer importar?</p>
          <p className="text-xs text-[color:var(--claude-stone)] mb-3">
            Encontramos <b>{auditoria.total_datas} dias</b> diferentes neste arquivo. Você pode:
          </p>
          <ul className="text-xs text-[color:var(--claude-stone)] mb-3 space-y-1 list-disc list-inside">
            <li>
              <b>Importar todas de uma vez</b> — recomendado quando todos os produtos já estão
              cadastrados. Cada dia substitui apenas o seu próprio fechamento.
            </li>
            <li>
              <b>Revisar apenas um dia</b> — se houver produto novo ou sem custo, prefira esta
              opção pra resolver linha a linha antes de gravar:
            </li>
          </ul>
          <select
            value={dataAlvo}
            onChange={(e) => onDataAlvo(e.target.value)}
            className="w-full p-2 rounded-lg border border-[color:var(--border)] bg-white text-sm font-mono tabular-nums"
          >
            {auditoria.datas_detectadas.map((d: string) => (
              <option key={d} value={d}>{d}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// SucessoMultiFase — resultado da importação multi-dia
// ============================================================================

function SucessoMultiFase({ resultado }: any) {
  const dias = resultado.total_dias || 0
  const vendas = resultado.total_vendas_criadas || 0
  const substituidas = resultado.total_vendas_removidas_antes || 0
  return (
    <div className="space-y-5">
      <div className="text-center py-4">
        <div className="inline-flex w-16 h-16 rounded-full bg-emerald-100 items-center justify-center mb-3">
          <Check className="text-emerald-600" size={32} />
        </div>
        <h3 className="headline text-3xl tracking-editorial">Pronto — vendas gravadas</h3>
        <p className="text-[color:var(--claude-stone)] mt-1">
          {dias} dia{dias === 1 ? '' : 's'} importado{dias === 1 ? '' : 's'} ·
          {' '}{vendas} venda{vendas === 1 ? '' : 's'} criada{vendas === 1 ? '' : 's'}
          {substituidas > 0 && (
            <span> · {substituidas} venda{substituidas === 1 ? '' : 's'} antiga{substituidas === 1 ? '' : 's'} substituída{substituidas === 1 ? '' : 's'}</span>
          )}
        </p>
      </div>

      <div className="claude-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-[color:var(--claude-cream-deep)]/40">
            <tr className="text-[10px] uppercase tracking-widest text-[color:var(--claude-stone)]">
              <th className="px-4 py-3 text-left">Dia</th>
              <th className="px-4 py-3 text-right">Vendas gravadas</th>
              <th className="px-4 py-3 text-right">Substituídas do mesmo dia</th>
              <th className="px-4 py-3 text-right">Clientes envolvidos</th>
              <th className="px-4 py-3 text-right">Produtos novos</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[color:var(--border)]">
            {(resultado.por_dia || []).map((d: any) => (
              <tr key={d.data} className="hover:bg-[color:var(--claude-cream-deep)]/20">
                <td className="px-4 py-2 font-mono tabular-nums">{d.data}</td>
                <td className="px-4 py-2 text-right font-mono tabular-nums text-[color:var(--claude-sage)]">
                  +{d.vendas_criadas}
                </td>
                <td className="px-4 py-2 text-right font-mono tabular-nums text-[color:var(--claude-stone)]">
                  {d.vendas_removidas_antes || 0}
                </td>
                <td className="px-4 py-2 text-right font-mono tabular-nums">{d.clientes_afetados ?? '—'}</td>
                <td className="px-4 py-2 text-right font-mono tabular-nums">{d.produtos_criados || 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="p-4 rounded-xl bg-[color:var(--claude-cream-deep)]/40 border border-[color:var(--border)] text-xs text-[color:var(--claude-stone)]">
        <p className="font-semibold text-[color:var(--claude-ink)] mb-1">O que mudou agora:</p>
        <ul className="space-y-1 list-disc list-inside">
          <li>Dashboard atualizado com a margem e o faturamento dos dias importados</li>
          <li>Cada cliente do CSV virou registro consultável em <b>Clientes</b></li>
          <li>Histórico de movimentações registra cada venda + saída de estoque</li>
        </ul>
      </div>
    </div>
  )
}

// ============================================================================
// ProdutosFaltantesFase — passo intermediario de cadastro/validacao agrupada.
// NAO altera o motor de importacao: as resolucoes geradas aqui sao escritas
// no mesmo Record<idx, resolucao> consumido pela fase 'preview'/commit. A
// diferenca eh que, ao decidir, aplicamos a TODAS as ocorrencias do produto
// no lote (mesmo grupo) — reduzindo retrabalho sem mudar persistencia.
// ============================================================================
function ProdutosFaltantesFase({ preview, resolucoes, onAplicarGrupo, produtosExistentes, grupos, progressoRestaurado, onDispensarBanner }: any) {
  const [apenasPendentes, setApenasPendentes] = useState(false)
  const gruposFaltantes = agruparProdutosFaltantes(preview.linhas)
  const totalGrupos = gruposFaltantes.length
  const resolvidos = gruposFaltantes.filter((g: GrupoProdutoFaltante) => grupoEstaResolvido(g, resolucoes)).length
  const pendentes = totalGrupos - resolvidos
  const totalOcorrencias = gruposFaltantes.reduce((s: number, g: GrupoProdutoFaltante) => s + g.ocorrencias, 0)
  const ocorrenciasResolvidas = gruposFaltantes
    .filter((g: GrupoProdutoFaltante) => grupoEstaResolvido(g, resolucoes))
    .reduce((s: number, g: GrupoProdutoFaltante) => s + g.ocorrencias, 0)

  // Filtro de exibicao — quando todos resolvidos, nao oferece o toggle
  // (nada pra esconder); quando ha pendentes, default eh mostrar todos.
  const gruposExibir = apenasPendentes
    ? gruposFaltantes.filter((g: GrupoProdutoFaltante) => !grupoEstaResolvido(g, resolucoes))
    : gruposFaltantes

  return (
    <div className="space-y-5">
      {/* Banner de progresso restaurado — discreto, dispensavel */}
      {progressoRestaurado && (
        <div className="px-3 py-2 bg-[color:var(--claude-sage)]/10 border border-[color:var(--claude-sage)]/30 rounded-lg flex items-center justify-between gap-3">
          <p className="text-[12px] text-[color:var(--claude-sage)]">
            ✓ Progresso restaurado deste arquivo — <strong>{progressoRestaurado.count}</strong>{' '}
            decisão(ões) recuperada(s).
          </p>
          <button
            onClick={onDispensarBanner}
            className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--claude-sage)] hover:opacity-70"
            aria-label="Dispensar aviso"
          >
            Dispensar
          </button>
        </div>
      )}

      {/* Banner de contexto — tom informativo, nao de erro */}
      <div className="p-4 bg-[color:var(--claude-cream-deep)]/40 border border-[color:var(--border)] rounded-xl">
        <p className="text-sm text-[color:var(--claude-ink)]">
          Encontramos produtos que ainda precisam de cadastro ou confirmação antes de importar as vendas.
        </p>
        <p className="text-xs text-[color:var(--claude-stone)] mt-1.5 leading-relaxed">
          Resolva <strong>1 vez por produto neste lote</strong> — aplicamos a todas as ocorrências automaticamente.
          Quantidade e preço médio são apenas referência do arquivo. <strong>O custo deve ser informado manualmente</strong> em toda importação CSV.
        </p>
      </div>

      {/* Resumo do progresso */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <MiniStat label="Produtos pendentes" valor={pendentes} cor={pendentes > 0 ? 'amber' : 'emerald'} />
        <MiniStat label="Já resolvidos" valor={`${resolvidos} de ${totalGrupos}`} cor="emerald" />
        <MiniStat label="Ocorrências cobertas" valor={`${ocorrenciasResolvidas} de ${totalOcorrencias}`} cor="blue" />
        <MiniStat label="Linhas totais" valor={preview.total_linhas} cor="slate" />
      </div>

      {/* Toolbar: filtro + contagem do que esta sendo exibido */}
      {totalGrupos > 0 && pendentes > 0 && resolvidos > 0 && (
        <div className="flex items-center justify-between gap-3 px-1">
          <span className="text-xs text-[color:var(--claude-stone)]">
            Exibindo <strong className="text-[color:var(--claude-ink)]">{gruposExibir.length}</strong> de {totalGrupos} produto(s)
          </span>
          <button
            onClick={() => setApenasPendentes(v => !v)}
            className={`text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 rounded transition-colors border ${
              apenasPendentes
                ? 'bg-[color:var(--claude-coral)] text-white border-[color:var(--claude-coral)]'
                : 'bg-white text-[color:var(--claude-stone)] border-[color:var(--border)] hover:bg-slate-50'
            }`}
            aria-pressed={apenasPendentes}
          >
            {apenasPendentes ? '✓ Apenas pendentes' : 'Apenas pendentes'}
          </button>
        </div>
      )}

      {/* Cards de cada grupo (filtrados se apenasPendentes) */}
      <div className="space-y-3">
        {gruposExibir.length === 0 ? (
          <div className="text-center py-8 text-sm italic text-[color:var(--claude-stone)]">
            {apenasPendentes
              ? 'Nenhum pendente — todos os produtos foram resolvidos.'
              : 'Nenhum produto faltante neste lote.'}
          </div>
        ) : gruposExibir.map((g: GrupoProdutoFaltante) => (
          <GrupoFaltanteCard
            key={g.chave}
            grupo={g}
            resolucao={resolucoes[g.idxs[0]]}
            onAplicar={(patch: any) => onAplicarGrupo(g.idxs, patch)}
            produtos={produtosExistentes}
            grupos={grupos}
            resolvido={grupoEstaResolvido(g, resolucoes)}
          />
        ))}
      </div>
    </div>
  )
}

function GrupoFaltanteCard({ grupo, resolucao, onAplicar, produtos, grupos, resolvido }: any) {
  const [expandido, setExpandido] = useState(false)
  const acaoAtual = resolucao?.acao || (grupo.tipo === 'sem_custo' ? 'corrigir_custo' : null)

  // Nome limpo do sufixo "(× N pedidos)" que o backend acrescenta ao nome_csv
  // para display de consolidacao. Sem isso, o cadastro novo herdaria o sufixo.
  const nomeLimpo = limparSufixoConsolidacao(grupo.nome)

  // Acao padrao para sem_custo: 'corrigir_custo' ja vem pre-selecionada para
  // reduzir cliques (produto ja existe, so falta o custo do lote).
  const iniciaCriar = () => onAplicar({
    acao: 'criar',
    novo_nome: resolucao?.novo_nome ?? nomeLimpo,
    novo_codigo: resolucao?.novo_codigo ?? grupo.codigo ?? '',
    novo_preco_venda: resolucao?.novo_preco_venda ?? grupo.preco_medio_ponderado,
  })

  const tipoLabel = grupo.tipo === 'sem_custo' ? 'Custo pendente' : 'Sem cadastro'

  return (
    <div className={`bg-white rounded-2xl border-2 overflow-hidden transition-all ${
      resolvido
        ? 'border-[color:var(--claude-sage)]/40 bg-[color:var(--claude-sage)]/5'
        : 'border-[color:var(--border)]'
    }`}>
      {/* Header do grupo */}
      <div className="p-4 flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={`pill ${resolvido ? 'pill-ok' : 'pill-warn'}`}>
              {resolvido ? '✓ resolvido' : tipoLabel}
            </span>
            {grupo.codigo && (
              <span className="text-[10px] font-mono text-[color:var(--claude-stone)]">
                cód {grupo.codigo}
              </span>
            )}
          </div>
          <h4 className="text-base font-semibold text-[color:var(--claude-ink)] truncate">
            {nomeLimpo}
          </h4>
          <p className="text-xs text-[color:var(--claude-stone)] mt-1">
            {grupo.ocorrencias === 1
              ? '1 ocorrência neste lote'
              : `${grupo.ocorrencias} ocorrências neste lote`}
            {' · '}
            qtd total {formatNumber(grupo.quantidade_total, { minimumFractionDigits: 0, maximumFractionDigits: 2 })}
            {' · '}
            preço médio {formatCurrency(grupo.preco_medio_ponderado)}
          </p>
        </div>
        <button
          onClick={() => setExpandido(v => !v)}
          className="text-[10px] font-bold uppercase tracking-wider text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)] shrink-0"
          aria-expanded={expandido}
        >
          {expandido ? 'Ocultar' : 'Ver'} ocorrências
        </button>
      </div>

      {/* Ocorrências detalhadas — pedidos reais do CSV via l.linhas_brutas
          (consolidacao do backend). Quando o backend nao expoe linhas_brutas
          (CSV legacy), fallback para a propria linha do preview. */}
      {expandido && (
        <div className="px-4 pb-3 -mt-2">
          <div className="bg-slate-50 rounded-lg p-3 text-[11px] space-y-1 border border-slate-200 max-h-48 overflow-y-auto">
            {grupo.linhas.flatMap((l: any) =>
              (l.linhas_brutas && l.linhas_brutas.length > 0)
                ? l.linhas_brutas.map((lb: any, i: number) => ({ ...lb, _key: `${l.idx}-${i}` }))
                : [{ pedido: `linha ${l.idx}`, cliente: '—', qtd: l.quantidade, preco: l.preco_unitario, _key: `${l.idx}` }]
            ).map((lb: any) => (
              <div key={lb._key} className="font-mono flex justify-between gap-3 text-slate-600">
                <span className="text-slate-500 shrink-0">{lb.pedido}</span>
                <span className="flex-1 truncate text-slate-700">{lb.cliente}</span>
                <span className="shrink-0">
                  {formatNumber(lb.qtd, { minimumFractionDigits: 0, maximumFractionDigits: 2 })} · {formatCurrency(lb.preco)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Ações + formulário inline */}
      <div className="px-4 pb-4 pt-1 border-t border-[color:var(--border)]/60 bg-slate-50/30">
        {grupo.tipo === 'sem_custo' ? (
          <div className="space-y-2 pt-3">
            <div className="flex gap-1.5">
              <BotaoAcao
                ativo={acaoAtual === 'corrigir_custo'}
                onClick={() => onAplicar({ acao: 'corrigir_custo', produto_id: grupo.produto_id })}
                label="Informar custo"
              />
              <BotaoAcao
                ativo={acaoAtual === 'ignorar'}
                onClick={() => onAplicar({ acao: 'ignorar' })}
                label="Ignorar grupo"
              />
            </div>
            {acaoAtual === 'corrigir_custo' && (
              <div className="p-3 bg-white rounded-lg border border-[color:var(--border)] space-y-2">
                <p className="text-[11px] text-[color:var(--claude-stone)]">
                  Produto já existe no cadastro. Informe o custo unitário <strong>desta importação</strong> — o valor será aplicado às {grupo.ocorrencias} ocorrência(s).
                </p>
                <input
                  type="number" step="0.01" min="0.01"
                  value={resolucao?.novo_custo ?? ''}
                  onChange={(e) => onAplicar({ acao: 'corrigir_custo', produto_id: grupo.produto_id, novo_custo: parseFloat(e.target.value) || 0 })}
                  placeholder="Custo unitário *"
                  className={`w-full p-2 rounded border text-sm bg-white ${
                    (!resolucao?.novo_custo || Number(resolucao.novo_custo) <= 0)
                      ? 'border-rose-300 bg-rose-50/50'
                      : 'border-slate-300'
                  }`}
                />
                <p className="text-[10px] text-[color:var(--claude-stone)]">
                  <strong className="text-rose-600">Custo &gt; 0</strong> obrigatório. Não usamos o preço médio do CSV — você precisa confirmar manualmente.
                </p>
              </div>
            )}
            {acaoAtual === 'ignorar' && (
              <p className="text-[11px] text-[color:var(--claude-stone)] italic mt-1">
                As {grupo.ocorrencias} ocorrência(s) deste produto não virarão venda nesta importação.
              </p>
            )}
          </div>
        ) : (
          <div className="space-y-2 pt-3">
            <div className="flex gap-1.5 flex-wrap">
              <BotaoAcao
                ativo={acaoAtual === 'associar'}
                onClick={() => {
                  // Pre-seleciona produto sugerido (se houver) ao entrar em
                  // 'Associar'. Nao auto-confirma — usuario revisa/troca no
                  // select. Se nao ha sugestao, abre vazio (comportamento
                  // anterior).
                  const sugerido = sugerirProdutoExistente(grupo, produtos)
                  onAplicar({ acao: 'associar', produto_id: sugerido })
                }}
                label="Associar a produto existente"
              />
              <BotaoAcao
                ativo={acaoAtual === 'criar'}
                onClick={iniciaCriar}
                label="Cadastrar novo"
              />
              <BotaoAcao
                ativo={acaoAtual === 'ignorar'}
                onClick={() => onAplicar({ acao: 'ignorar' })}
                label="Ignorar grupo"
              />
            </div>

            {acaoAtual === 'associar' && (() => {
              // Detecta se o produto_id atual veio da sugestao automatica
              // (mesmo id que sugerirProdutoExistente retorna agora) — usado
              // pra mostrar a flag "sugerido pelo sistema".
              const sugeridoAgora = sugerirProdutoExistente(grupo, produtos)
              const eSugestao = resolucao?.produto_id != null
                && resolucao.produto_id === sugeridoAgora
              return (
                <div className="p-3 bg-white rounded-lg border border-[color:var(--border)] space-y-2">
                  <p className="text-[11px] text-[color:var(--claude-stone)]">
                    Selecione um produto já cadastrado. A associação será aplicada às {grupo.ocorrencias} ocorrência(s).
                  </p>
                  <select
                    value={resolucao?.produto_id || ''}
                    onChange={(e) => onAplicar({ acao: 'associar', produto_id: e.target.value ? parseInt(e.target.value) : null })}
                    className={`w-full p-2 rounded border text-sm bg-white ${
                      !resolucao?.produto_id ? 'border-rose-300 bg-rose-50/50' : 'border-slate-300'
                    }`}
                  >
                    <option value="">— selecione um produto —</option>
                    {produtos.map((p: any) => (
                      <option key={p.id} value={p.id}>
                        {p.nome} {p.codigo ? `[${p.codigo}]` : ''}
                      </option>
                    ))}
                  </select>
                  {eSugestao && (
                    <p className="text-[10px] text-[color:var(--claude-sage)] flex items-center gap-1">
                      <span>✓</span>
                      <span>Sugestão automática — confirme ou troque acima</span>
                    </p>
                  )}
                </div>
              )
            })()}

            {acaoAtual === 'criar' && (
              <div className="p-3 bg-white rounded-lg border border-[color:var(--border)] space-y-2">
                <p className="text-[11px] text-[color:var(--claude-stone)]">
                  Cadastro assistido — nome e código pré-preenchidos do CSV. <strong>Custo é manual e obrigatório.</strong>
                </p>
                <input
                  type="text"
                  value={resolucao?.novo_nome ?? grupo.nome}
                  onChange={(e) => onAplicar({ acao: 'criar', novo_nome: e.target.value })}
                  placeholder="Nome *"
                  className="w-full p-2 rounded border border-slate-300 text-sm bg-white"
                />
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="text"
                    value={resolucao?.novo_codigo ?? grupo.codigo ?? ''}
                    onChange={(e) => onAplicar({ acao: 'criar', novo_codigo: e.target.value })}
                    placeholder="Código ERP"
                    className="p-2 rounded border border-slate-300 text-sm bg-white font-mono"
                  />
                  <select
                    value={resolucao?.novo_grupo_id ?? ''}
                    onChange={(e) => onAplicar({ acao: 'criar', novo_grupo_id: e.target.value ? parseInt(e.target.value) : null })}
                    className={`p-2 rounded border text-sm bg-white ${
                      !resolucao?.novo_grupo_id ? 'border-rose-300 bg-rose-50/50' : 'border-slate-300'
                    }`}
                  >
                    <option value="">— grupo *—</option>
                    {grupos.map((g: any) => (
                      <option key={g.id} value={g.id}>{g.nome}</option>
                    ))}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <input
                    type="number" step="0.01"
                    value={resolucao?.novo_preco_venda ?? grupo.preco_medio_ponderado}
                    onChange={(e) => onAplicar({ acao: 'criar', novo_preco_venda: parseFloat(e.target.value) || 0 })}
                    placeholder="Preço venda *"
                    className={`p-2 rounded border text-sm bg-white ${
                      !resolucao?.novo_preco_venda ? 'border-rose-300 bg-rose-50/50' : 'border-slate-300'
                    }`}
                  />
                  <input
                    type="number" step="0.01" min="0.01"
                    value={resolucao?.novo_custo ?? ''}
                    onChange={(e) => onAplicar({ acao: 'criar', novo_custo: parseFloat(e.target.value) || 0 })}
                    placeholder="Custo *"
                    className={`p-2 rounded border text-sm bg-white ${
                      (!resolucao?.novo_custo || Number(resolucao.novo_custo) <= 0)
                        ? 'border-rose-300 bg-rose-50/50'
                        : 'border-slate-300'
                    }`}
                  />
                </div>
                <p className="text-[10px] text-[color:var(--claude-stone)]">
                  <strong className="text-rose-600">Custo &gt; 0</strong> obrigatório — não inferimos do preço médio. Será aplicado às {grupo.ocorrencias} ocorrência(s).
                </p>
              </div>
            )}

            {acaoAtual === 'ignorar' && (
              <p className="text-[11px] text-[color:var(--claude-stone)] italic mt-1">
                As {grupo.ocorrencias} ocorrência(s) deste produto não virarão venda nesta importação.
              </p>
            )}

            {!acaoAtual && (
              <p className="text-[11px] text-[color:var(--claude-stone)] italic mt-1">
                Escolha uma ação acima para resolver este grupo.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function PreviewFase({ preview, resolucoes, onResolucao, produtosExistentes, grupos }: any) {
  // Usa as pills semanticas do design system (tokens Claude) em vez de
  // classes de cor literais — consistencia com o resto do produto.
  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      ok: 'pill pill-ok',
      conflito: 'pill pill-warn',
      sem_match: 'pill pill-warn',
      sem_custo: 'pill pill-warn',
      erro: 'pill pill-alert',
      fora_periodo: 'pill pill-muted',
    }
    return map[status] || 'pill pill-muted'
  }
  const statusLabel = (status: string) => {
    const map: Record<string, string> = {
      ok: '✓ ok',
      conflito: 'conflito',
      sem_match: 'sem match',
      sem_custo: 'sem custo',
      erro: 'erro',
    }
    return map[status] || status
  }

  return (
    <div className="space-y-5">
      {/* Resumo */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        <MiniStat label="Linhas" valor={preview.total_linhas} cor="slate" />
        <MiniStat label="OK" valor={preview.linhas_ok} cor="emerald" />
        <MiniStat label="Pendentes" valor={preview.linhas_pendentes} cor="amber" />
        <MiniStat label="Erros" valor={preview.linhas_erro} cor="rose" />
        <MiniStat label="Receita" valor={formatCurrency(preview.receita_total)} cor="blue" />
        <MiniStat label="SKUs" valor={preview.skus_distintos} cor="slate" />
      </div>

      {preview.ja_existe_fechamento && (
        <div className="p-3 bg-amber-50 border border-amber-300 rounded-xl text-sm text-amber-900 flex items-start gap-2">
          <AlertTriangle size={18} className="shrink-0 mt-0.5" />
          <span>
            Já existe fechamento para <strong>{preview.data_alvo}</strong>. Ao confirmar,
            <strong> vendas, ENTRADAS-espelho e SAÍDAS</strong> dos produtos deste dia
            serão apagadas e regeneradas a partir do CSV. Movimentações manuais (Entrada
            de Estoque) <em>não</em> são afetadas. Tem certeza que quer sobrescrever?
          </span>
        </div>
      )}

      {/* Tabela de linhas */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-3 py-2 font-black text-slate-400 uppercase tracking-wider">#</th>
              <th className="px-3 py-2 font-black text-slate-400 uppercase tracking-wider">Cód CSV</th>
              <th className="px-3 py-2 font-black text-slate-400 uppercase tracking-wider">Produto (CSV)</th>
              <th className="px-3 py-2 font-black text-slate-400 uppercase tracking-wider text-right">Qtd</th>
              <th className="px-3 py-2 font-black text-slate-400 uppercase tracking-wider text-right">Preço</th>
              <th className="px-3 py-2 font-black text-slate-400 uppercase tracking-wider text-right">Total</th>
              <th className="px-3 py-2 font-black text-slate-400 uppercase tracking-wider text-center">Status</th>
              <th className="px-3 py-2 font-black text-slate-400 uppercase tracking-wider">Ação / Match</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {preview.linhas.map((l: any) => (
              <tr key={l.idx} className="align-top">
                <td className="px-3 py-2 text-slate-400 font-mono">{l.idx}</td>
                <td className="px-3 py-2 font-mono text-slate-600">{l.codigo_csv || '—'}</td>
                <td className="px-3 py-2 font-semibold text-slate-900 max-w-xs">
                  {l.nome_csv}
                  {l.mensagens && l.mensagens.length > 0 && (
                    <ul className="mt-1 space-y-0.5 text-[10px] text-slate-500 list-disc list-inside">
                      {l.mensagens.map((m: string, i: number) => (
                        <li key={i}>{m}</li>
                      ))}
                    </ul>
                  )}
                </td>
                <td className="px-3 py-2 text-right font-mono">{formatNumber(l.quantidade, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td className="px-3 py-2 text-right font-mono">{formatCurrency(l.preco_unitario)}</td>
                <td className="px-3 py-2 text-right font-mono font-bold">{formatCurrency(l.total)}</td>
                <td className="px-3 py-2 text-center">
                  <span className={statusBadge(l.status)}>
                    {statusLabel(l.status)}
                  </span>
                </td>
                <td className="px-3 py-2 min-w-[280px]">
                  {l.status === 'ok' ? (
                    <span className="text-[11px] text-emerald-700">→ {l.produto_nome}</span>
                  ) : (
                    <LinhaResolucao
                      linha={l}
                      resolucao={resolucoes[l.idx] || (
                        l.status === 'sem_custo'
                          ? { idx: l.idx, acao: 'corrigir_custo', produto_id: l.produto_id }
                          : { idx: l.idx, acao: 'ignorar' }
                      )}
                      onChange={(patch: any) => onResolucao(l.idx, patch)}
                      produtos={produtosExistentes}
                      grupos={grupos}
                    />
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function MiniStat({ label, valor, cor }: any) {
  const mapa: Record<string, string> = {
    slate: 'bg-slate-50 text-slate-700 border-slate-200',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
    rose: 'bg-rose-50 text-rose-700 border-rose-200',
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
  }
  return (
    <div className={`p-3 rounded-xl border ${mapa[cor] || mapa.slate}`}>
      <p className="text-[9px] font-black uppercase tracking-widest opacity-70">{label}</p>
      <p className="text-lg font-black leading-tight mt-0.5">{valor}</p>
    </div>
  )
}

function LinhaResolucao({ linha, resolucao, onChange, produtos, grupos }: any) {
  const acao = resolucao.acao || 'ignorar'

  // Caso especial: produto existe mas está com custo=0. UI simplificada —
  // só pede o custo (e o botão Ignorar como escape).
  if (linha.status === 'sem_custo') {
    return (
      <div className="space-y-1.5">
        <div className="flex gap-1.5">
          <BotaoAcao
            ativo={acao === 'corrigir_custo'}
            onClick={() => onChange({ acao: 'corrigir_custo', produto_id: linha.produto_id })}
            label="Informar custo"
          />
          <BotaoAcao ativo={acao === 'ignorar'} onClick={() => onChange({ acao: 'ignorar' })} label="Ignorar" />
        </div>

        {acao === 'corrigir_custo' && (
          <div className="p-2 bg-amber-50 rounded-lg border border-amber-200 space-y-1.5">
            <p className="text-[10px] text-amber-900">
              Produto: <strong>{linha.produto_nome}</strong>. Informe o custo unitário para gerar a venda.
            </p>
            <input
              type="number" step="0.01" min="0.01"
              value={resolucao.novo_custo ?? ''}
              onChange={(e) => onChange({ novo_custo: parseFloat(e.target.value) || 0 })}
              placeholder="Custo unitário *"
              className={`w-full p-1.5 rounded border text-xs bg-white ${
                (!resolucao.novo_custo || Number(resolucao.novo_custo) <= 0)
                  ? 'border-rose-400 bg-rose-50'
                  : 'border-slate-300'
              }`}
            />
            <p className="text-[10px] text-slate-500">
              <strong className="text-rose-600">Custo &gt; 0</strong> obrigatório. O valor será salvo no produto e usado como CMP.
            </p>
          </div>
        )}

        {acao === 'ignorar' && (
          <p className="text-[10px] text-slate-500 italic">Esta linha não vai virar venda.</p>
        )}
      </div>
    )
  }

  return (
    <div className="space-y-1.5">
      <div className="flex gap-1.5">
        <BotaoAcao ativo={acao === 'associar'} onClick={() => onChange({ acao: 'associar' })} label="Associar" />
        <BotaoAcao ativo={acao === 'criar'} onClick={() => onChange({
          acao: 'criar',
          novo_nome: resolucao.novo_nome ?? linha.nome_csv,
          novo_codigo: resolucao.novo_codigo ?? linha.codigo_csv ?? '',
          novo_preco_venda: resolucao.novo_preco_venda ?? linha.preco_unitario,
        })} label="Criar" />
        <BotaoAcao ativo={acao === 'ignorar'} onClick={() => onChange({ acao: 'ignorar' })} label="Ignorar" />
      </div>

      {acao === 'associar' && (
        <select
          value={resolucao.produto_id || ''}
          onChange={(e) => onChange({ produto_id: e.target.value ? parseInt(e.target.value) : null })}
          className="w-full p-1.5 rounded border border-slate-300 text-xs bg-white"
        >
          <option value="">— selecione um produto —</option>
          {produtos.map((p: any) => (
            <option key={p.id} value={p.id}>
              {p.nome} {p.codigo ? `[${p.codigo}]` : ''}
            </option>
          ))}
        </select>
      )}

      {acao === 'criar' && (
        <div className="p-2 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5">
          <input
            type="text"
            value={resolucao.novo_nome ?? linha.nome_csv}
            onChange={(e) => onChange({ novo_nome: e.target.value })}
            placeholder="Nome"
            className="w-full p-1.5 rounded border border-slate-300 text-xs bg-white"
          />
          <div className="grid grid-cols-2 gap-1.5">
            <input
              type="text"
              value={resolucao.novo_codigo ?? linha.codigo_csv ?? ''}
              onChange={(e) => onChange({ novo_codigo: e.target.value })}
              placeholder="Código ERP"
              className="p-1.5 rounded border border-slate-300 text-xs bg-white font-mono"
            />
            <select
              value={resolucao.novo_grupo_id ?? ''}
              onChange={(e) => onChange({ novo_grupo_id: e.target.value ? parseInt(e.target.value) : null })}
              className="p-1.5 rounded border border-slate-300 text-xs bg-white"
            >
              <option value="">— grupo —</option>
              {grupos.map((g: any) => (
                <option key={g.id} value={g.id}>{g.nome}</option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-1.5">
            <input
              type="number" step="0.01"
              value={resolucao.novo_preco_venda ?? linha.preco_unitario}
              onChange={(e) => onChange({ novo_preco_venda: parseFloat(e.target.value) || 0 })}
              placeholder="Preço venda"
              className="p-1.5 rounded border border-slate-300 text-xs bg-white"
            />
            <input
              type="number" step="0.01" min="0.01"
              value={resolucao.novo_custo ?? ''}
              onChange={(e) => onChange({ novo_custo: parseFloat(e.target.value) || 0 })}
              placeholder="Custo *"
              className={`p-1.5 rounded border text-xs bg-white ${
                (!resolucao.novo_custo || Number(resolucao.novo_custo) <= 0)
                  ? 'border-rose-400 bg-rose-50'
                  : 'border-slate-300'
              }`}
            />
          </div>
          <p className="text-[10px] text-slate-500">
            Todos os campos obrigatórios. <strong className="text-rose-600">Custo &gt; 0</strong> é imprescindível — venda sem custo vira margem 100%.
          </p>
        </div>
      )}

      {acao === 'ignorar' && (
        <p className="text-[10px] text-slate-500 italic">Esta linha não vai virar venda.</p>
      )}
    </div>
  )
}

function BotaoAcao({ ativo, onClick, label }: any) {
  return (
    <button
      onClick={onClick}
      className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider transition-all ${
        ativo
          ? 'bg-blue-600 text-white'
          : 'bg-white border border-slate-300 text-slate-600 hover:bg-slate-50'
      }`}
    >
      {label}
    </button>
  )
}


function ProjecaoPage() {
  const [proj, setProj] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    carregar()
  }, [])

  const carregar = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${API_URL}/projecao/amanha?top_n=30`)
      setProj(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <EmptyState variant="loading" className="h-full" title="Carregando projeção…" />
    )
  }

  if (!proj) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <EmptyState variant="error" title="Erro ao carregar projeção." />
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-start">
        <div>
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Projeção para amanhã</p>
          <h2 className="headline text-4xl tracking-editorial capitalize">{proj.dia_semana} · {formatDate(proj.data_alvo)}</h2>
        </div>
        <button
          onClick={carregar}
          className="bg-white border border-slate-200 px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-50"
        >
          Recalcular
        </button>
      </header>
      <ProjecaoCard proj={proj} />
      <ProjecaoDetalhesSKU proj={proj} />
    </div>
  )
}

function ProjecaoCard({ proj }: any) {
  const confMap: Record<string, { cor: string, label: string }> = {
    alta: { cor: 'bg-emerald-500', label: 'Alta' },
    media: { cor: 'bg-blue-500', label: 'Média' },
    baixa: { cor: 'bg-amber-500', label: 'Baixa' },
    sem_dados: { cor: 'bg-slate-400', label: 'Sem dados' },
  }
  const conf = confMap[proj.confianca_geral] || confMap.sem_dados

  return (
    <div className="bg-gradient-to-br from-indigo-600 to-blue-800 p-6 rounded-3xl text-white shadow-xl shadow-blue-900/20">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h3 className="text-xl font-bold flex items-center gap-2">
            <Target size={20} className="text-blue-200" /> Projeção D+1 · {proj.dia_semana}
          </h3>
          <p className="text-blue-200 text-sm mt-1">
            Baseado em rolling mean 7d + fator dia-da-semana (30d).
          </p>
        </div>
        <span className={`${conf.cor} text-white text-[10px] font-black uppercase tracking-widest px-3 py-1.5 rounded-lg`}>
          Confiança {conf.label}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white/10 p-4 rounded-xl border border-white/5">
          <p className="text-[10px] font-black text-blue-200 uppercase tracking-widest">Faturamento</p>
          <p className="text-2xl font-black leading-tight mt-1">{formatCurrency(proj.faturamento_previsto)}</p>
          <p className="text-[10px] text-blue-200 mt-1">
            {proj.confianca_geral === 'sem_dados'
              ? 'sem comparativo (sem histórico)'
              : `${formatPercent(proj.comparacao_media_7d_pct, { scale: 1, signed: true })} vs média 7d`}
          </p>
        </div>
        <div className="bg-white/10 p-4 rounded-xl border border-white/5">
          <p className="text-[10px] font-black text-blue-200 uppercase tracking-widest">Margem</p>
          <p className="text-2xl font-black leading-tight mt-1">{formatPercent(proj.margem_prevista)}</p>
          <p className="text-[10px] text-blue-200 mt-1">Meta 17–19%</p>
        </div>
        <div className="bg-white/10 p-4 rounded-xl border border-white/5">
          <p className="text-[10px] font-black text-blue-200 uppercase tracking-widest">Custo projetado</p>
          <p className="text-2xl font-black leading-tight mt-1">{formatCurrency(proj.custo_previsto)}</p>
        </div>
        <div className="bg-white/10 p-4 rounded-xl border border-white/5">
          <p className="text-[10px] font-black text-blue-200 uppercase tracking-widest">SKUs com previsão</p>
          <p className="text-2xl font-black leading-tight mt-1">{proj.skus_previstos}</p>
        </div>
      </div>
    </div>
  )
}

function ProjecaoDetalhesSKU({ proj }: any) {
  const skusComPrevisao = (proj.por_sku || []).filter((s: any) => s.quantidade_prevista > 0)
  const skusSemHistorico = (proj.por_sku || []).filter((s: any) => s.confianca === 'sem_dados')

  const confBadge = (conf: string) => {
    const map: Record<string, string> = {
      alta: 'bg-emerald-100 text-emerald-700',
      media: 'bg-blue-100 text-blue-700',
      baixa: 'bg-amber-100 text-amber-700',
      sem_dados: 'bg-slate-100 text-slate-500',
    }
    return map[conf] || map.sem_dados
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
      <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
        <TrendingUp size={18} className="text-blue-500" /> Top SKUs previstos
      </h3>
      {skusComPrevisao.length === 0 ? (
        <EmptyState
          variant="empty"
          icon={<AlertTriangle className="text-amber-600" size={22} />}
          className="bg-amber-50 border border-amber-200 rounded-xl text-amber-900"
          title="Sem histórico suficiente para projeção."
          description="Registre ao menos 3 fechamentos diários para começar a gerar previsões. Confiança alta a partir de 21 dias."
        />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-[10px] uppercase tracking-widest text-slate-400 border-b">
              <th className="text-left pb-2 font-black">Produto</th>
              <th className="text-center pb-2 font-black">Confiança</th>
              <th className="text-right pb-2 font-black">Qtd prev.</th>
              <th className="text-right pb-2 font-black">Receita</th>
              <th className="text-right pb-2 font-black">Margem</th>
              <th className="text-right pb-2 font-black">Fator DoW</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {skusComPrevisao.map((s: any) => (
              <tr key={s.produto_id} className="hover:bg-slate-50/50">
                <td className="py-2.5 font-semibold text-slate-800">{s.nome}</td>
                <td className="py-2.5 text-center">
                  <span className={`inline-flex px-2 py-0.5 rounded-md text-[10px] font-black tracking-wider ${confBadge(s.confianca)}`}>
                    {s.confianca} · {s.dias_historico}d
                  </span>
                </td>
                <td className="py-2.5 text-right font-mono text-slate-600">{formatNumber(s.quantidade_prevista, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                <td className="py-2.5 text-right font-mono font-bold text-slate-900">{formatCurrency(s.receita_prevista)}</td>
                <td className="py-2.5 text-right">
                  <span className={`font-black ${s.margem_prevista >= 0.17 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {formatPercent(s.margem_prevista)}
                  </span>
                </td>
                <td className="py-2.5 text-right">
                  <span className={`text-xs font-bold ${s.dow_factor > 1.05 ? 'text-emerald-600' : s.dow_factor < 0.95 ? 'text-rose-600' : 'text-slate-500'}`}>
                    {formatNumber(s.dow_factor, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}×
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {skusSemHistorico.length > 0 && (
        <p className="text-[11px] text-slate-400 mt-4 italic">
          {skusSemHistorico.length} SKU(s) sem histórico não foram projetados.
        </p>
      )}
    </div>
  )
}

function AnaliseFechamentoView({ analise, onCopy, copied, onReset }: any) {
  const statusConfig: Record<string, { label: string, bg: string, text: string, border: string }> = {
    saudavel:   { label: 'SAUDÁVEL',   bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-500' },
    acima_meta: { label: 'ACIMA DA META', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-500' },
    atencao:    { label: 'ATENÇÃO',    bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-500' },
    alerta:     { label: 'ALERTA',     bg: 'bg-rose-50',    text: 'text-rose-700',    border: 'border-rose-500' },
    sem_vendas: { label: 'SEM VENDAS', bg: 'bg-slate-50',   text: 'text-slate-600',   border: 'border-slate-400' },
  }
  const cfg = statusConfig[analise.status_meta] || statusConfig.sem_vendas

  const abc = analise.classificacao_abc || {}
  const xyz = analise.classificacao_xyz || {}
  const anomaliasOrdenadas = [...(analise.anomalias || [])].sort((a: any, b: any) => {
    const ord: Record<string, number> = { alta: 0, media: 1, baixa: 2, info: 3 }
    return (ord[a.severidade] ?? 4) - (ord[b.severidade] ?? 4)
  })

  // Severidade `info` = nota positiva (margem acima da meta sem suspeita).
  // Distinta de `media`/`alta` (anomalias reais) e de `baixa` (info neutra).
  const sevIcon = (s: string) =>
    s === 'alta' ? <AlertTriangle size={14} className="text-rose-600" /> :
    s === 'media' ? <AlertCircle size={14} className="text-amber-600" /> :
    s === 'info' ? <TrendingUp size={14} className="text-emerald-600" /> :
    <Check size={14} className="text-slate-500" />

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-start">
        <div>
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Fechamento do dia</p>
          <h2 className="headline text-4xl tracking-editorial">{formatDate(analise.data, { weekday: 'long', day: 'numeric', month: 'long' })}</h2>
        </div>
        <div className={`${cfg.bg} ${cfg.text} ${cfg.border} border-2 px-6 py-3 rounded-2xl font-black uppercase text-sm tracking-widest shadow-sm`}>
          {cfg.label}
        </div>
      </header>

      {/* KPIs principais */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KPICard title="Faturamento Hoje" value={formatCurrency(analise.faturamento_dia)} sub={`vs 7d: ${formatPercent(analise.variacao_faturamento_7d_pct, { scale: 1, signed: true })}`} tone={analise.variacao_faturamento_7d_pct >= -5 ? 'ok' : 'alert'} />
        <KPICard title="Margem do Dia" value={formatPercent(analise.margem_dia)} sub={`Meta: 17–19%`} tone={(analise.status_meta === 'saudavel' || analise.status_meta === 'acima_meta') ? 'ok' : analise.status_meta === 'alerta' ? 'alert' : 'warn'} />
        <KPICard title="Margem 7d / 30d" value={formatPercent(analise.margem_media_7d)} sub={`30d: ${formatPercent(analise.margem_media_30d)}`} tone="neutral" />
        <KPICard title="SKUs vendidos" value={`${analise.total_skus_vendidos}/${analise.total_skus_cadastrados}`} sub={`Rupturas: ${analise.rupturas}`} tone={analise.rupturas > 0 ? 'warn' : 'ok'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top SKUs */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-blue-500" /> Top SKUs do Dia
          </h3>
          {(analise.top_skus || []).length === 0 ? (
            <EmptyState variant="empty" compact title="Nenhuma venda registrada." />
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-[10px] uppercase tracking-widest text-slate-400 border-b">
                  <th className="text-left pb-2 font-black">Produto</th>
                  <th className="text-center pb-2 font-black">Classe</th>
                  <th className="text-right pb-2 font-black">Qtd</th>
                  <th className="text-right pb-2 font-black">Receita</th>
                  <th className="text-right pb-2 font-black">Margem</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {analise.top_skus.map((s: any) => (
                  <tr key={s.produto_id} className="hover:bg-slate-50/50">
                    <td className="py-2.5 font-semibold text-slate-800">{s.nome}</td>
                    <td className="py-2.5 text-center">
                      <span className="inline-flex px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 text-[10px] font-black tracking-wider">{s.classe_abc}{s.classe_xyz}</span>
                    </td>
                    <td className="py-2.5 text-right font-mono text-slate-600">{formatNumber(s.quantidade, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                    <td className="py-2.5 text-right font-mono font-bold text-slate-900">{formatCurrency(s.receita)}</td>
                    <td className="py-2.5 text-right">
                      <span className={`font-black ${s.margem_dia >= 0.17 ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {formatPercent(s.margem_dia)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Classificação ABC-XYZ */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
            <Gauge size={18} className="text-blue-500" /> Matriz ABC-XYZ (30d)
          </h3>
          <div className="space-y-4">
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Por receita (ABC)</p>
              <div className="flex gap-2">
                <ClassBadge label="A" count={abc.A || 0} color="bg-emerald-500" />
                <ClassBadge label="B" count={abc.B || 0} color="bg-blue-500" />
                <ClassBadge label="C" count={abc.C || 0} color="bg-slate-400" />
                <ClassBadge label="N/A" count={abc['N/A'] || 0} color="bg-slate-200 text-slate-500" />
              </div>
            </div>
            <div>
              <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">Por previsibilidade (XYZ)</p>
              <div className="flex gap-2">
                <ClassBadge label="X" count={xyz.X || 0} color="bg-emerald-500" />
                <ClassBadge label="Y" count={xyz.Y || 0} color="bg-amber-500" />
                <ClassBadge label="Z" count={xyz.Z || 0} color="bg-rose-500" />
                <ClassBadge label="N/A" count={xyz['N/A'] || 0} color="bg-slate-200 text-slate-500" />
              </div>
            </div>
            <div className="pt-2 text-[11px] text-slate-500 leading-relaxed border-t">
              <b>A</b>=80% da receita · <b>X</b>=venda estável · <b>Z</b>=errática.
              <br/>Alvo de promoção: <b>CX/CY</b> (baixo risco).
            </div>
          </div>
        </div>
      </div>

      {/* Anomalias */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
        <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
          <AlertTriangle size={18} className="text-amber-500" /> Anomalias detectadas ({anomaliasOrdenadas.length})
        </h3>
        {anomaliasOrdenadas.length === 0 ? (
          <EmptyState
            variant="empty"
            compact
            icon={<Check size={18} className="text-emerald-500" />}
            title="Nenhuma anomalia. Dia dentro do esperado."
          />
        ) : (
          <ul className="space-y-2">
            {anomaliasOrdenadas.slice(0, 15).map((a: any, i: number) => (
              <li key={i} className="flex items-start gap-3 p-3 bg-slate-50 rounded-xl">
                <div className="mt-0.5">{sevIcon(a.severidade)}</div>
                <div className="flex-1">
                  <p className="text-sm text-slate-800">{a.descricao}</p>
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mt-1">
                    {a.tipo.replace(/_/g, ' ')} · {a.severidade}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <button
          onClick={onCopy}
          className="flex-1 bg-emerald-600 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 hover:bg-emerald-700 shadow-lg shadow-emerald-600/20 transition-all active:scale-95"
        >
          <Copy size={18} /> {copied ? 'Copiado!' : 'Copiar análise para WhatsApp'}
        </button>
        <button
          onClick={onReset}
          className="flex-1 bg-slate-100 text-slate-600 font-bold py-4 rounded-xl hover:bg-slate-200 transition-all active:scale-95"
        >
          Novo Lançamento
        </button>
      </div>
    </div>
  )
}

function BriefingPage() {
  const [briefing, setBriefing] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<string>(() => new Date().toISOString().slice(0, 10))
  const [simCesta, setSimCesta] = useState<any>(null)
  const [simLoading, setSimLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    carregar(data)
  }, [data])

  const carregar = async (alvo: string) => {
    setLoading(true)
    setSimCesta(null)
    try {
      const res = await axios.get(`${API_URL}/fechamento/narrativa?data=${alvo}&top_recs=10`)
      setBriefing(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const simularCesta = async (urgencia?: string) => {
    setSimLoading(true)
    try {
      const url = urgencia
        ? `${API_URL}/recomendacoes/simular-cesta?data=${data}&urgencia=${urgencia}`
        : `${API_URL}/recomendacoes/simular-cesta?data=${data}`
      const res = await axios.get(url)
      setSimCesta(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setSimLoading(false)
    }
  }

  const copiar = async () => {
    if (!briefing?.narrativa) return
    try {
      await navigator.clipboard.writeText(briefing.narrativa)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (e) {
      console.error(e)
    }
  }

  if (loading) {
    return <EmptyState variant="loading" className="h-full" title="Gerando briefing…" />
  }
  if (!briefing) {
    return <EmptyState variant="error" className="h-full" title="Erro ao carregar briefing." />
  }

  const analise = briefing.analise || {}
  const projecao = briefing.projecao || {}
  const recs = briefing.recomendacoes || []

  const statusMap: Record<string, { bg: string; accent: string; label: string }> = {
    saudavel: { bg: 'var(--claude-sage)',  accent: 'var(--claude-sage)',  label: 'Saudável' },
    atencao:  { bg: 'var(--claude-amber)', accent: 'var(--claude-amber)', label: 'Atenção'  },
    alerta:   { bg: 'var(--claude-coral)', accent: 'var(--claude-coral)', label: 'Alerta'   },
  }
  const statusInfo = statusMap[analise.status_meta] || { bg: 'var(--claude-stone)', accent: 'var(--claude-stone)', label: 'Sem dados' }

  const margemPct = (analise.margem_dia || 0) * 100
  const margemPrevPct = (projecao.margem_prevista || 0) * 100

  return (
    <div className="p-6 overflow-auto h-full">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <p className="section-label mb-1">Narrativa consolidada</p>
            <h1 className="headline text-4xl flex items-center gap-3 tracking-editorial">
              <Sparkles size={28} className="text-[color:var(--claude-coral)]" />
              Briefing Diário
            </h1>
            <p className="text-sm text-[color:var(--claude-stone)] mt-1">
              Fechamento + projeção + próximos movimentos, prontos para o WhatsApp.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={data}
              onChange={(e) => setData(e.target.value)}
              className="px-3 py-2 text-sm border border-[color:var(--border)] rounded-lg bg-white mono"
            />
            <button
              onClick={() => carregar(data)}
              className="px-4 py-2 bg-[color:var(--claude-ink)] text-[color:var(--claude-cream)] text-sm font-medium rounded-lg hover:opacity-90 transition-opacity"
            >
              Atualizar
            </button>
          </div>
        </div>

        {/* Narrativa card */}
        <div
          className="claude-card p-6 border-l-4"
          style={{
            borderLeftColor: statusInfo.accent,
            background: `color-mix(in srgb, ${statusInfo.bg} 5%, white)`
          }}
        >
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              <span className="pill"
                    style={{
                      background: `color-mix(in srgb, ${statusInfo.bg} 15%, transparent)`,
                      color: statusInfo.accent
                    }}>
                {statusInfo.label}
              </span>
              <span className="section-label text-[color:var(--claude-stone)]">
                {briefing.fonte === 'ia' ? 'Gerado por IA' : 'Template determinístico'}
              </span>
            </div>
            <button
              onClick={copiar}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-white hover:bg-[color:var(--claude-cream-deep)] border border-[color:var(--border)] rounded-lg text-xs font-medium transition-colors"
            >
              {copied ? <><Check size={14} /> Copiado</> : <><Clipboard size={14} /> Copiar p/ WhatsApp</>}
            </button>
          </div>
          <div className="prose prose-sm max-w-none whitespace-pre-wrap text-[color:var(--claude-ink)] leading-relaxed serif text-[15px]">
            {briefing.narrativa}
          </div>
        </div>

        {/* KPIs consolidados */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KPICard
            title="Margem do Dia"
            value={formatPercent(margemPct, { scale: 1 })}
            sub={`Meta 17–19% · ${analise.status_meta || '-'}`}
            tone={margemPct >= 17 && margemPct <= 19 ? 'ok' : margemPct < 17 ? 'alert' : 'warn'}
          />
          <KPICard
            title="Faturamento Hoje"
            value={formatCurrency(analise.faturamento_dia || 0)}
            sub={`${formatPercent(analise.variacao_faturamento_7d_pct || 0, { scale: 1, signed: true })} vs 7d`}
            tone={(analise.variacao_faturamento_7d_pct || 0) >= 0 ? 'ok' : 'warn'}
          />
          <KPICard
            title="Projeção D+1"
            value={formatCurrency(projecao.faturamento_previsto || 0)}
            sub={`${projecao.dia_semana || '-'} · margem ${formatPercent(margemPrevPct, { scale: 1 })}`}
            tone="ok"
          />
          <KPICard
            title="SKUs c/ Ação"
            value={recs.length}
            sub={`${recs.filter((r: any) => r.urgencia === 'alta').length} urgência alta`}
            tone={recs.filter((r: any) => r.urgencia === 'alta').length > 0 ? 'warn' : 'ok'}
          />
        </div>

        {/* Simulador de cesta */}
        <div className="claude-card p-5" style={{ background: 'color-mix(in srgb, var(--claude-coral) 4%, white)' }}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="headline text-xl flex items-center gap-2">
              <Calculator size={18} className="text-[color:var(--claude-coral)]" />
              Simular cesta de recomendações
            </h3>
            <div className="flex gap-2">
              <button
                onClick={() => simularCesta('alta')}
                disabled={simLoading}
                className="px-3 py-1.5 text-white text-xs font-medium rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
                style={{ background: 'var(--claude-coral)' }}
              >
                Só urgência alta
              </button>
              <button
                onClick={() => simularCesta()}
                disabled={simLoading}
                className="px-3 py-1.5 text-[color:var(--claude-cream)] text-xs font-medium rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
                style={{ background: 'var(--claude-ink)' }}
              >
                Todas recomendações
              </button>
            </div>
          </div>
          {simLoading && <p className="text-xs text-[color:var(--claude-stone)] serif italic">Calculando impacto…</p>}
          {simCesta && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2">
              <div className="bg-white rounded-lg p-3 border border-[color:var(--border)]">
                <p className="section-label">Margem atual</p>
                <p className="mt-1">
                  <MetricValue value={formatPercent(simCesta.margem_atual, { maximumFractionDigits: 2 })} size="xl" />
                </p>
              </div>
              <div className="bg-white rounded-lg p-3 border border-[color:var(--border)]">
                <p className="section-label">Margem pós</p>
                <p className="mt-1">
                  <MetricValue
                    value={formatPercent(simCesta.nova_margem_estimada, { maximumFractionDigits: 2 })}
                    size="xl"
                    toneClass={simCesta.status === 'seguro' ? 'text-[color:var(--claude-sage)]' : simCesta.status === 'alerta' ? 'text-[color:var(--claude-amber)]' : 'text-[color:var(--claude-coral)]'}
                  />
                </p>
              </div>
              <div className="bg-white rounded-lg p-3 border border-[color:var(--border)]">
                <p className="section-label">Impacto</p>
                <p className="mt-1">
                  <MetricValue value={`-${formatNumber(simCesta.impacto_pp, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}pp`} size="xl" />
                </p>
              </div>
              <div className="bg-white rounded-lg p-3 border border-[color:var(--border)]">
                <p className="section-label">SKUs afetados</p>
                <p className="kpi-value text-xl text-[color:var(--claude-ink)] mt-1">
                  {simCesta.skus_afetados} <span className="text-xs text-[color:var(--claude-stone)] font-normal">· {formatPercent(simCesta.desconto_medio_ponderado, { scale: 1 })} desc</span>
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Recomendações detalhadas */}
        <div>
          <p className="section-label mb-2">Plano de ação</p>
          <h2 className="headline text-2xl mb-4">Recomendações por SKU</h2>
          <div className="space-y-2">
            {recs.map((r: any) => <RecomendacaoCard key={r.produto_id} r={r} />)}
            {recs.length === 0 && (
              <EmptyState
                variant="empty"
                className="claude-card"
                icon={<ShoppingBag size={28} />}
                title="Nenhuma recomendação gerada para esta data."
                description="Registre vendas para o motor de inteligência começar a sugerir movimentos."
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function RecomendacaoCard({ r }: any) {
  const urgBorderMap: Record<string, string> = {
    alta:  'var(--claude-coral)',
    media: 'var(--claude-amber)',
    baixa: 'var(--claude-stone)',
  }
  const urgColor = urgBorderMap[r.urgencia] || 'var(--claude-stone)'

  // Paleta unificada — ações positivas em sage/coral, liquidações em coral mais intenso
  const acaoColorMap: Record<string, string> = {
    ajuste_cima:           'var(--claude-amber)',
    repor_urgente:         'var(--claude-coral)',
    liquidar_forte:        'var(--claude-coral)',
    liquidar_leve:         'var(--claude-amber)',
    promover_alto:         'var(--claude-ink)',
    promover_moderado:     'var(--claude-ink)',
    promover_combo:        'var(--claude-ink)',
    proteger:              'var(--claude-sage)',
    garantir_disponibilidade: 'var(--claude-sage)',
  }
  const acaoColor = acaoColorMap[r.acao] || 'var(--claude-stone)'
  const acaoLabel = r.acao.replace(/_/g, ' ').toUpperCase()

  return (
    <div className="claude-card p-4 border-l-4 hover:shadow-[0_4px_16px_-8px_rgba(28,27,23,0.16)] transition-shadow"
         style={{ borderLeftColor: urgColor }}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded text-white"
                  style={{ background: acaoColor }}>
              {acaoLabel}
            </span>
            <span className="pill"
                  style={{
                    background: `color-mix(in srgb, ${urgColor} 15%, transparent)`,
                    color: urgColor
                  }}>
              urg {r.urgencia}
            </span>
            <span className="pill pill-muted mono">
              {r.classe_abc}-{r.classe_xyz}
            </span>
          </div>
          <h4 className="serif font-semibold text-[color:var(--claude-ink)] mt-2 text-lg leading-tight truncate">{r.nome}</h4>
          <p className="text-xs text-[color:var(--claude-stone)] mono">SKU {r.sku}</p>
          <p className="text-sm text-[color:var(--claude-ink)] mt-2">{r.justificativa}</p>
          <p className="text-xs text-[color:var(--claude-stone)] italic mt-1">→ {r.impacto_esperado}</p>
        </div>
        <div className="text-right flex-shrink-0 space-y-2">
          {r.desconto_sugerido !== null && r.desconto_sugerido !== undefined && (
            <div>
              <p className="section-label">Desc. sug.</p>
              <p className="kpi-value text-xl text-[color:var(--claude-coral)]">-{formatPercent(r.desconto_sugerido, { scale: 1 })}</p>
            </div>
          )}
          {r.preco_sugerido && (
            <div>
              <p className="section-label">Preço sug.</p>
              <p className="kpi-value text-sm text-[color:var(--claude-ink)]">{formatCurrency(r.preco_sugerido)}</p>
            </div>
          )}
          <div>
            <p className="section-label">Margem</p>
            <p className="kpi-value text-sm text-[color:var(--claude-ink)]">
              {formatPercent(r.margem_atual)}
              {r.margem_pos_acao !== null && r.margem_pos_acao !== undefined && (
                <span className="text-[color:var(--claude-stone)]"> → {formatPercent(r.margem_pos_acao)}</span>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

function ClassBadge({ label, count, color }: any) {
  return (
    <div className={`flex-1 rounded-xl p-3 text-center ${color} ${color.includes('text-') ? '' : 'text-white'}`}>
      <p className="text-[10px] font-black uppercase tracking-widest opacity-80">{label}</p>
      <p className="text-lg font-black">{count}</p>
    </div>
  )
}

function SimuladorPage({ initialTab = 'manual' }: { initialTab?: 'manual' | 'engine' }) {
  const [tab, setTab] = useState<'manual' | 'engine'>(initialTab)
  const [produtos, setProdutos] = useState<Produto[]>([])
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [discount, setDiscount] = useState(10)
  const [result, setResult] = useState<any>(null)

  useEffect(() => {
    axios.get(`${API_URL}/produtos`).then(res => setProdutos(res.data))
  }, [])

  const handleSimulate = async () => {
    if (selectedIds.length === 0) return
    const res = await axios.post(`${API_URL}/simular`, {
      sku_ids: selectedIds,
      desconto_pct: discount
    })
    setResult(res.data)
  }

  const toggleSelection = (id: number) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-6">
      <header>
        <p className="section-label mb-1">Promoção · cenários</p>
        <h2 className="headline text-4xl tracking-editorial">Simulador</h2>
        <p className="text-[color:var(--claude-stone)] mt-1">
          Escolha entre montar a cesta manualmente ou deixar o engine propor 3 cestas a partir de uma meta.
        </p>
      </header>

      <div className="flex gap-1 border-b border-[color:var(--border)]">
        {([
          { v: 'manual', label: 'Manual' },
          { v: 'engine', label: 'Engine (orientado a meta)' },
        ] as const).map(t => (
          <button
            key={t.v}
            onClick={() => setTab(t.v as any)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.v
                ? 'border-[color:var(--claude-coral)] text-[color:var(--claude-ink)]'
                : 'border-transparent text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'engine' && <EnginePromocaoPanel />}
      {tab === 'manual' && (
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-lg mb-4">1. Selecione os SKUs</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {produtos.map(p => (
                <button
                  key={p.id}
                  onClick={() => toggleSelection(p.id)}
                  className={`p-3 rounded-xl border-2 text-left transition-all ${
                    selectedIds.includes(p.id) ? 'border-blue-500 bg-blue-50' : 'border-slate-100 hover:border-slate-300'
                  }`}
                >
                  <p className="text-sm font-bold leading-tight">{p.nome}</p>
                </button>
              ))}
            </div>
          </div>
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
            <h3 className="font-bold text-lg mb-4">2. Desconto (%) na Simulação</h3>
            <input 
              type="range" min="0" max="50" step="1" 
              value={discount} 
              onChange={(e) => setDiscount(parseInt(e.target.value))}
              className="w-full h-2 bg-slate-100 rounded-lg accent-blue-600 appearance-none cursor-pointer"
            />
            <div className="flex justify-between mt-4">
              <span className="text-xl font-black text-blue-600">{formatPercent(discount, { scale: 1, maximumFractionDigits: 0 })}</span>
              <button 
                onClick={handleSimulate}
                className="bg-slate-900 text-white px-8 py-2 rounded-xl font-bold transition-all active:scale-95 shadow-lg shadow-slate-900/20"
              >
                Calcular Impacto
              </button>
            </div>
          </div>
        </div>
        <div className="bg-white p-8 rounded-3xl border shadow-2xl relative overflow-hidden">
          <div className="absolute -top-10 -right-10 opacity-5">
             <TrendingUp size={200} />
          </div>
          <h3 className="font-bold text-xl mb-6">Projeção da Meta</h3>
          {result ? (
            <div className="space-y-6">
              <p className="text-xs font-black text-slate-400 uppercase tracking-widest">Margem Estimada Resultante</p>
              <p className="text-5xl font-black text-slate-900 tracking-tighter">{formatPercent(result.nova_margem_estimada)}</p>
              <div className={`p-4 rounded-xl border font-black uppercase text-xs text-center tracking-widest ${
                result.status === 'seguro'
                  ? 'bg-emerald-50 border-emerald-100 text-emerald-600'
                  : result.status === 'alerta'
                    ? 'bg-amber-50 border-amber-100 text-amber-700'
                    : 'bg-rose-50 border-rose-100 text-rose-600'
              }`}>
                 Status: {result.status === 'seguro' ? 'SAUDÁVEL' : result.status === 'alerta' ? 'ATENÇÃO' : 'BLOQUEADO'}
              </div>
              <div className="bg-slate-50 rounded-xl p-4 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-500 font-semibold">Margem atual</span>
                  <span className="font-black text-slate-700">{formatPercent(result.margem_atual)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-semibold">Impacto</span>
                  <span className={`font-black ${result.impacto_pp > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                    {result.impacto_pp > 0 ? '-' : '+'}{formatNumber(Math.abs(result.impacto_pp), { minimumFractionDigits: 2, maximumFractionDigits: 2 })} pp
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed italic">
                * Cálculo ponderado pelo estoque atual. Status bloqueado = margem &lt; 17%.
              </p>
            </div>
          ) : (
            <EmptyState
              variant="empty"
              className="py-12 text-slate-400"
              icon={<Sparkles size={48} />}
              title="Selecione produtos para simular."
            />
          )}
        </div>
      </div>
      )}
    </div>
  )
}

// ============================================================================
// EnginePromocaoPanel — solver inverso (meta → 3 cestas rankeadas)
// ============================================================================

type CestaItem = {
  id: number
  produto_id: number
  produto_nome: string
  produto_sku: string | null
  classe_abc: string | null
  classe_xyz: string | null
  desconto_pct: number
  preco_atual: number
  preco_promo: number
  margem_atual: number
  margem_pos_acao: number
  qtd_baseline: number
  qtd_projetada: number
  receita_projetada: number
  lucro_marginal: number
  beta_usado: number
  qualidade_elasticidade: string
  cobertura_pos_promo_dias: number | null
  risco_stockout_pct: number | null
  flag_risco: string | null
  ordem_entrada: number
}

type CestaPromocao = {
  id: number
  perfil: 'conservador' | 'balanceado' | 'agressivo'
  meta_margem_pct: number
  janela_dias: number
  status: string
  margem_atual: number | null
  margem_projetada: number | null
  lucro_semanal_projetado: number | null
  receita_projetada: number | null
  qtd_skus: number
  desconto_medio_pct: number | null
  motivo_falha: string | null
  promocao_id: number | null
  criado_em: string | null
  decidido_em: string | null
  itens: CestaItem[]
  atinge_meta: boolean
}

type EngineResponse = {
  cestas: CestaPromocao[]
  candidatos_total: number
  candidatos_bloqueados: number
  candidatos_promo_ativa: number
  elasticidades_recalculadas: boolean
  aviso: string | null
}

const PERFIL_LABELS: Record<string, { label: string; desc: string; color: string }> = {
  conservador: { label: 'Conservador', desc: 'Desconto até 10%, margem mantida', color: 'sage' },
  balanceado: { label: 'Balanceado', desc: 'Ponto ótimo do solver', color: 'coral' },
  agressivo: { label: 'Agressivo', desc: 'Maximiza volume, sacrifica 1pp', color: 'amber' },
}

function EnginePromocaoPanel() {
  const [meta, setMeta] = useState(17.5)
  const [janela, setJanela] = useState(7)
  const [maxSkus, setMaxSkus] = useState(15)
  const [response, setResponse] = useState<EngineResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [aprovando, setAprovando] = useState<number | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [toast, setToast] = useState<{ tipo: 'ok' | 'erro'; msg: string } | null>(null)

  const propor = async () => {
    setLoading(true)
    setResponse(null)
    try {
      const res = await axios.post(`${API_URL}/promocoes/engine/propor`, {
        meta_margem_pct: meta / 100,
        janela_dias: janela,
        max_skus_por_cesta: maxSkus,
      })
      setResponse(res.data)
      // Expande a cesta balanceada por padrão se atingiu meta
      const balanceada = res.data.cestas.find((c: CestaPromocao) => c.perfil === 'balanceado')
      if (balanceada) setExpanded(balanceada.id)
    } catch (e: any) {
      setToast({ tipo: 'erro', msg: e?.response?.data?.detail || e.message || 'Erro ao gerar propostas' })
      setTimeout(() => setToast(null), 5000)
    } finally {
      setLoading(false)
    }
  }

  const aprovar = async (cesta: CestaPromocao) => {
    setAprovando(cesta.id)
    try {
      const r = await axios.post(`${API_URL}/promocoes/engine/aprovar/${cesta.id}`, {})
      setToast({
        tipo: 'ok',
        msg: `Cesta ${cesta.perfil} aprovada como Promoção #${r.data.id} (rascunho). Publique em Promoções.`,
      })
      // Atualiza estado local SEM re-rodar o solver: backend já marcou esta
      // como 'aprovada' e as outras 2 como 'descartada' no mesmo run.
      setResponse(prev => prev ? {
        ...prev,
        cestas: prev.cestas.map(c => {
          if (c.id === cesta.id) {
            return { ...c, status: 'aprovada', promocao_id: r.data.id }
          }
          if (c.status === 'proposta') {
            return { ...c, status: 'descartada' }
          }
          return c
        }),
      } : prev)
    } catch (e: any) {
      setToast({ tipo: 'erro', msg: e?.response?.data?.detail || e.message || 'Erro ao aprovar' })
    } finally {
      setAprovando(null)
      setTimeout(() => setToast(null), 5500)
    }
  }

  return (
    <div className="space-y-6">
      {/* Inputs */}
      <div className="claude-card p-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className="section-label">Meta de margem semanal</label>
            <div className="flex items-center gap-3 mt-2">
              <input
                type="range" min="14" max="22" step="0.5"
                value={meta} onChange={e => setMeta(parseFloat(e.target.value))}
                className="flex-1 accent-[color:var(--claude-coral)]"
              />
              <span className="mono text-2xl font-bold w-20 text-right text-[color:var(--claude-ink)]">{formatPercent(meta, { scale: 1 })}</span>
            </div>
            <p className="text-xs text-[color:var(--claude-stone)] mt-1">
              Faixa saudável: 17–19%. Meta determina quão agressivo o solver pode ser.
            </p>
          </div>
          <div>
            <label className="section-label">Janela da promoção</label>
            <div className="flex items-center gap-3 mt-2">
              <input
                type="range" min="3" max="14" step="1"
                value={janela} onChange={e => setJanela(parseInt(e.target.value))}
                className="flex-1 accent-[color:var(--claude-coral)]"
              />
              <span className="mono text-2xl font-bold w-20 text-right text-[color:var(--claude-ink)]">{janela}d</span>
            </div>
            <p className="text-xs text-[color:var(--claude-stone)] mt-1">
              7d cobre ciclo semanal padrão. 14d para escoar encalhado.
            </p>
          </div>
          <div>
            <label className="section-label">Máx SKUs por cesta</label>
            <div className="flex items-center gap-3 mt-2">
              <input
                type="range" min="3" max="25" step="1"
                value={maxSkus} onChange={e => setMaxSkus(parseInt(e.target.value))}
                className="flex-1 accent-[color:var(--claude-coral)]"
              />
              <span className="mono text-2xl font-bold w-20 text-right text-[color:var(--claude-ink)]">{maxSkus}</span>
            </div>
            <p className="text-xs text-[color:var(--claude-stone)] mt-1">
              Cestas menores = comunicação mais simples ao cliente.
            </p>
          </div>
        </div>
        <div className="mt-5 flex justify-end">
          <button
            onClick={propor}
            disabled={loading}
            className="px-5 py-2.5 text-sm rounded-lg font-medium text-white hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
            style={{ background: 'var(--claude-coral)' }}
          >
            {loading ? 'Calculando…' : <><Wand2 size={16} /> Gerar 3 propostas</>}
          </button>
        </div>
      </div>

      {/* Aviso */}
      {response?.aviso && (
        <div className="claude-card p-4 flex items-start gap-3" style={{ borderLeftWidth: '4px', borderLeftColor: 'var(--claude-amber)' }}>
          <AlertCircle className="text-[color:var(--claude-amber)] flex-shrink-0 mt-0.5" size={18} />
          <p className="text-sm text-[color:var(--claude-ink)]">{response.aviso}</p>
        </div>
      )}

      {/* Sumário de candidatos */}
      {response && (
        <div className="grid grid-cols-3 gap-4">
          <div className="claude-card p-3 text-center">
            <p className="section-label">Candidatos elegíveis</p>
            <p className="mt-1 inline-block">
              <MetricValue
                value={response.candidatos_total - response.candidatos_bloqueados - response.candidatos_promo_ativa}
                size="xl"
                toneClass="text-[color:var(--claude-sage)]"
              />
            </p>
          </div>
          <div className="claude-card p-3 text-center">
            <p className="section-label">Bloqueados (blacklist)</p>
            <p className="mt-1 inline-block">
              <MetricValue value={response.candidatos_bloqueados} size="xl" toneClass="text-[color:var(--claude-stone)]" />
            </p>
          </div>
          <div className="claude-card p-3 text-center">
            <p className="section-label">Já em promoção ativa</p>
            <p className="mt-1 inline-block">
              <MetricValue value={response.candidatos_promo_ativa} size="xl" toneClass="text-[color:var(--claude-stone)]" />
            </p>
          </div>
        </div>
      )}

      {/* 3 cestas lado-a-lado */}
      {response?.cestas && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {response.cestas.map(c => (
            <CestaCard
              key={c.id}
              cesta={c}
              expanded={expanded === c.id}
              onToggle={() => setExpanded(prev => prev === c.id ? null : c.id)}
              onAprovar={() => aprovar(c)}
              aprovando={aprovando === c.id}
            />
          ))}
        </div>
      )}

      {!response && !loading && (
        <EmptyState
          variant="empty"
          className="claude-card"
          icon={<Wand2 size={36} />}
          title='Defina a meta e clique em "Gerar 3 propostas" para o engine propor cestas.'
        />
      )}

      {toast && (
        <div className="fixed bottom-6 right-6 z-50 claude-card px-4 py-3 flex items-center gap-2 max-w-md"
             style={{
               borderLeftWidth: '4px',
               borderLeftColor: toast.tipo === 'ok' ? 'var(--claude-sage)' : 'var(--claude-coral)'
             }}>
          {toast.tipo === 'ok'
            ? <Check size={16} className="text-[color:var(--claude-sage)]" />
            : <AlertCircle size={16} className="text-[color:var(--claude-coral)]" />}
          <p className="text-sm text-[color:var(--claude-ink)]">{toast.msg}</p>
        </div>
      )}
    </div>
  )
}

function CestaCard({
  cesta, expanded, onToggle, onAprovar, aprovando,
}: {
  cesta: CestaPromocao
  expanded: boolean
  onToggle: () => void
  onAprovar: () => void
  aprovando: boolean
}) {
  const meta = PERFIL_LABELS[cesta.perfil] || { label: cesta.perfil, desc: '', color: 'stone' }
  const colorVar = meta.color === 'sage' ? 'var(--claude-sage)' : meta.color === 'coral' ? 'var(--claude-coral)' : 'var(--claude-amber)'
  const aprovavel = cesta.status === 'proposta' && cesta.qtd_skus > 0
  const ja_aprovada = cesta.status === 'aprovada'

  return (
    <div className="claude-card overflow-hidden flex flex-col">
      <div className="p-4 border-b border-[color:var(--border)]" style={{ borderLeftWidth: '4px', borderLeftColor: colorVar }}>
        <div className="flex items-start justify-between mb-1">
          <div>
            <p className="section-label" style={{ color: colorVar }}>{meta.label}</p>
            <p className="text-[10px] text-[color:var(--claude-stone)]">{meta.desc}</p>
          </div>
          {ja_aprovada && (
            <span className="text-[10px] px-2 py-0.5 rounded-full font-medium uppercase tracking-wide"
                  style={{ background: 'var(--claude-sage)', color: 'white' }}>
              Aprovada
            </span>
          )}
          {cesta.status === 'descartada' && (
            <span className="text-[10px] px-2 py-0.5 rounded-full font-medium uppercase tracking-wide bg-[color:var(--claude-stone)]/20 text-[color:var(--claude-stone)]">
              Descartada
            </span>
          )}
        </div>

        {cesta.qtd_skus === 0 ? (
          <div className="mt-3 p-3 rounded-lg bg-[color:var(--claude-stone)]/5 text-xs text-[color:var(--claude-stone)] italic">
            {cesta.motivo_falha === 'meta_inalcancavel'
              ? 'Meta inalcançável com candidatos atuais. Reduza a meta ou revise blacklist.'
              : cesta.motivo_falha === 'sem_candidatos'
              ? 'Nenhum SKU elegível.'
              : 'Sem proposta gerada.'}
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-2 mt-3">
              <div>
                <p className="text-[10px] text-[color:var(--claude-stone)] uppercase">Margem proj.</p>
                <p>
                  <MetricValue
                    value={formatPercent(cesta.margem_projetada)}
                    size="xl"
                    toneClass={cesta.atinge_meta ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]'}
                  />
                </p>
                <p className="text-[10px] text-[color:var(--claude-stone)] mono">
                  meta {formatPercent(cesta.meta_margem_pct)}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-[color:var(--claude-stone)] uppercase">Lucro semanal</p>
                <p>
                  <MetricValue
                    value={formatCurrency(cesta.lucro_semanal_projetado || 0, { minimumFractionDigits: 0, maximumFractionDigits: 0, signed: true })}
                    size="xl"
                  />
                </p>
                <p className="text-[10px] text-[color:var(--claude-stone)] mono">
                  receita {formatCurrency(cesta.receita_projetada || 0, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </p>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
              <div>
                <span className="text-[color:var(--claude-stone)]">SKUs:</span>{' '}
                <span className="mono font-semibold">{cesta.qtd_skus}</span>
              </div>
              <div>
                <span className="text-[color:var(--claude-stone)]">Desconto médio:</span>{' '}
                <span className="mono font-semibold">{formatPercent(cesta.desconto_medio_pct, { scale: 1 })}</span>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Botões */}
      <div className="flex border-b border-[color:var(--border)]">
        <button
          onClick={onToggle}
          disabled={cesta.qtd_skus === 0}
          className="flex-1 px-3 py-2 text-xs font-medium text-[color:var(--claude-stone)] hover:bg-[color:var(--claude-cream-deep)]/40 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-1"
        >
          {expanded ? <><ChevronDown size={14} /> Ocultar SKUs</> : <><ChevronRight size={14} /> Ver SKUs</>}
        </button>
        <button
          onClick={onAprovar}
          disabled={!aprovavel || aprovando}
          className="flex-1 px-3 py-2 text-xs font-medium text-white hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed"
          style={{ background: colorVar }}
        >
          {aprovando ? 'Aprovando…' : ja_aprovada ? 'Aprovada' : 'Aprovar'}
        </button>
      </div>

      {/* Detalhes expandidos */}
      {expanded && cesta.itens.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-[color:var(--claude-cream-deep)]/40 text-left">
                <th className="px-2 py-1 section-label">SKU</th>
                <th className="px-2 py-1 section-label text-right">Desc</th>
                <th className="px-2 py-1 section-label text-right">Margem</th>
                <th className="px-2 py-1 section-label text-right">+Lucro</th>
                <th className="px-2 py-1 section-label text-center">Risco</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[color:var(--border)]">
              {cesta.itens.map(it => (
                <CestaItemRow key={it.id} item={it} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function CestaItemRow({ item }: { item: CestaItem }) {
  const [open, setOpen] = useState(false)
  const corRisco = item.flag_risco === 'verde' ? 'var(--claude-sage)' : item.flag_risco === 'amarelo' ? 'var(--claude-amber)' : 'var(--claude-coral)'

  return (
    <>
      <tr className="hover:bg-[color:var(--claude-cream-deep)]/30 cursor-pointer" onClick={() => setOpen(o => !o)}>
        <td className="px-2 py-1.5">
          <p className="font-medium text-[color:var(--claude-ink)] truncate max-w-[140px]" title={item.produto_nome}>{item.produto_nome}</p>
          <p className="text-[10px] text-[color:var(--claude-stone)] mono">
            {item.produto_sku || '—'}
            {item.classe_abc && item.classe_xyz && ` · ${item.classe_abc}-${item.classe_xyz}`}
          </p>
        </td>
        <td className="px-2 py-1.5 text-right mono font-semibold">{formatPercent(item.desconto_pct, { scale: 1, maximumFractionDigits: 0 })}</td>
        <td className="px-2 py-1.5 text-right mono">
          <span className="text-[color:var(--claude-stone)]">{formatPercent(item.margem_atual, { maximumFractionDigits: 0 }).replace('%', '')}</span>
          <span className="text-[color:var(--claude-stone)]/60">→</span>
          <span style={{ color: item.margem_pos_acao >= 0.10 ? 'var(--claude-ink)' : 'var(--claude-coral)' }}>{formatPercent(item.margem_pos_acao, { maximumFractionDigits: 0 })}</span>
        </td>
        <td className="px-2 py-1.5 text-right mono font-semibold text-[color:var(--claude-sage)]">
          {formatCurrency(item.lucro_marginal, { minimumFractionDigits: 0, maximumFractionDigits: 0, signed: true })}
        </td>
        <td className="px-2 py-1.5 text-center">
          <span className="inline-block w-2 h-2 rounded-full" style={{ background: corRisco }} />
        </td>
      </tr>
      {open && (
        <tr className="bg-[color:var(--claude-cream-deep)]/30">
          <td colSpan={5} className="px-3 py-2 text-[11px] text-[color:var(--claude-stone)]">
            <div className="grid grid-cols-2 gap-2">
              <div>
                <span className="text-[color:var(--claude-stone)]">Preço:</span>{' '}
                <span className="mono">{formatCurrency(item.preco_atual)} → {formatCurrency(item.preco_promo)}</span>
              </div>
              <div>
                <span className="text-[color:var(--claude-stone)]">Qtd projetada:</span>{' '}
                <span className="mono">{formatNumber(item.qtd_projetada, { maximumFractionDigits: 0 })} ({formatNumber(item.qtd_baseline, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}/dia × fator)</span>
              </div>
              <div>
                <span className="text-[color:var(--claude-stone)]">Elasticidade β:</span>{' '}
                <span className="mono">{formatNumber(item.beta_usado, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
                <span className="ml-1 text-[10px] uppercase px-1.5 py-0.5 rounded"
                      style={{
                        background: item.qualidade_elasticidade === 'alta' ? 'color-mix(in srgb, var(--claude-sage) 20%, transparent)' :
                                    item.qualidade_elasticidade === 'media' ? 'color-mix(in srgb, var(--claude-amber) 20%, transparent)' :
                                    'color-mix(in srgb, var(--claude-stone) 20%, transparent)',
                      }}>
                  {item.qualidade_elasticidade}
                </span>
              </div>
              <div>
                <span className="text-[color:var(--claude-stone)]">Cobertura pós-promo:</span>{' '}
                <span className="mono">
                  {item.cobertura_pos_promo_dias != null ? `${formatNumber(item.cobertura_pos_promo_dias, { minimumFractionDigits: 1, maximumFractionDigits: 1 })}d` : '∞'}
                  {item.risco_stockout_pct != null && ` (risco ${formatPercent(item.risco_stockout_pct, { maximumFractionDigits: 0 })})`}
                </span>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

// ============================================================================
// HistoricoPage — inspeção e exclusão de entradas/saídas
// ============================================================================
type Movimentacao = {
  movimentacao_id: number
  venda_id: number | null
  tipo: 'ENTRADA' | 'SAIDA' | 'QUEBRA'
  produto_id: number | null
  produto_nome: string
  produto_sku: string | null
  quantidade: number
  peso: number
  custo_unitario: number
  valor_total: number
  cidade: string | null
  motivo: string | null
  data: string | null
}

// ============================================================================
// CLIENTES — ranking RFM + top compradores por produto
// ============================================================================

interface ClienteRankingItem {
  cliente_id: number
  nome: string
  is_consumidor_final: boolean
  total_compras_periodo: number
  valor_periodo: number
  ticket_medio: number
  ultima_compra: string | null
  primeira_compra: string | null
  dias_desde_ultima: number | null
  score_r: number
  score_f: number
  score_m: number
  segmento: string
  segmento_label: string
}

interface TopCompradorItem {
  cliente_id: number
  nome: string
  is_consumidor_final: boolean
  quantidade: number
  valor: number
  transacoes: number
  ultima_compra: string | null
}

const SEGMENTO_TONE: Record<string, string> = {
  champion: 'pill-ok',
  loyal: 'pill-ok',
  big_spender: 'pill-warn',
  at_risk: 'pill-warn',
  lost: 'pill-alert',
  new: 'pill-muted',
  regular: 'pill-muted',
}

function ClientesPage({ initialClienteId }: { initialClienteId?: number | null } = {}) {
  const [aba, setAba] = useState<'ranking' | 'por_produto'>('ranking')
  const [periodo, setPeriodo] = useState(30)
  const [incluirCF, setIncluirCF] = useState(false)
  const [ranking, setRanking] = useState<ClienteRankingItem[]>([])
  const [loadingRanking, setLoadingRanking] = useState(true)
  const [resumo, setResumo] = useState<any | null>(null)
  const [clienteDetalheId, setClienteDetalheId] = useState<number | null>(initialClienteId ?? null)

  const [produtos, setProdutos] = useState<Produto[]>([])
  const [produtoSel, setProdutoSel] = useState<number | null>(null)
  const [topCompradores, setTopCompradores] = useState<TopCompradorItem[]>([])
  const [loadingTop, setLoadingTop] = useState(false)

  useEffect(() => {
    setLoadingRanking(true)
    axios
      .get(`${API_URL}/clientes/ranking`, {
        params: {
          periodo_dias: periodo,
          limit: 100,
          incluir_consumidor_final: incluirCF,
        },
      })
      .then((res) => setRanking(res.data))
      .catch((err) => console.error('Erro ao carregar ranking:', err))
      .finally(() => setLoadingRanking(false))
    // Resumo do período carrega em paralelo
    axios
      .get(`${API_URL}/clientes/resumo`, {
        params: { periodo_dias: periodo, incluir_consumidor_final: incluirCF },
      })
      .then((res) => setResumo(res.data))
      .catch((err) => console.error('Erro ao carregar resumo:', err))
  }, [periodo, incluirCF])

  useEffect(() => {
    if (aba !== 'por_produto') return
    if (produtos.length > 0) return
    axios.get(`${API_URL}/produtos`).then((res) => {
      setProdutos(res.data)
      if (res.data.length && produtoSel === null) setProdutoSel(res.data[0].id)
    })
  }, [aba])

  useEffect(() => {
    if (aba !== 'por_produto' || produtoSel === null) return
    setLoadingTop(true)
    axios
      .get(`${API_URL}/produtos/${produtoSel}/top-compradores`, {
        params: { periodo_dias: periodo, limit: 15, incluir_consumidor_final: true },
      })
      .then((res) => setTopCompradores(res.data.compradores || []))
      .catch((err) => console.error('Erro ao carregar top compradores:', err))
      .finally(() => setLoadingTop(false))
  }, [aba, produtoSel, periodo])

  return (
    <div className="max-w-7xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-end">
        <div>
          <p className="section-label mb-1">Análise comercial · {periodo} dias</p>
          <h2 className="headline text-4xl tracking-editorial">Clientes</h2>
          <p className="text-[color:var(--claude-stone)] mt-1 text-sm">
            Ranking de compradores com segmentação RFM (Recency / Frequency / Monetary).
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={periodo}
            onChange={(e) => setPeriodo(Number(e.target.value))}
            className="px-3 py-2 text-sm border border-[color:var(--border)] rounded-lg bg-white"
          >
            <option value={7}>7 dias</option>
            <option value={30}>30 dias</option>
            <option value={60}>60 dias</option>
            <option value={90}>90 dias</option>
            <option value={180}>180 dias</option>
            <option value={365}>1 ano</option>
          </select>
        </div>
      </header>

      {/* Cards-resumo do periodo */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="claude-card p-4">
          <p className="section-label">Clientes ativos</p>
          <p className="mt-2"><MetricValue value={resumo ? String(resumo.total_clientes) : '—'} size="2xl" /></p>
          <p className="text-[11px] text-[color:var(--claude-stone)] mt-1">com pelo menos 1 compra no período</p>
        </div>
        <div className="claude-card p-4">
          <p className="section-label">Faturamento</p>
          <p className="mt-2"><MetricValue value={resumo ? formatCurrency(resumo.faturamento_total) : '—'} size="2xl" /></p>
          <p className="text-[11px] text-[color:var(--claude-stone)] mt-1">{resumo?.transacoes ?? '—'} transações</p>
        </div>
        <div className="claude-card p-4">
          <p className="section-label">Ticket médio</p>
          <p className="mt-2"><MetricValue value={resumo ? formatCurrency(resumo.ticket_medio) : '—'} size="2xl" /></p>
          <p className="text-[11px] text-[color:var(--claude-stone)] mt-1">por transação</p>
        </div>
        <div className="claude-card p-4">
          <p className="section-label">Clientes novos</p>
          <p className="mt-2"><MetricValue value={resumo ? String(resumo.clientes_novos) : '—'} size="2xl" toneClass="text-[color:var(--claude-sage)]" /></p>
          <p className="text-[11px] text-[color:var(--claude-stone)] mt-1">primeira compra no período</p>
        </div>
      </div>

      <div className="flex gap-2 border-b border-[color:var(--border)]">
        {(['ranking', 'por_produto'] as const).map((a) => (
          <button
            key={a}
            onClick={() => setAba(a)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
              aba === a
                ? 'border-[color:var(--claude-coral)] text-[color:var(--claude-ink)]'
                : 'border-transparent text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)]'
            }`}
          >
            {a === 'ranking' ? 'Ranking de clientes' : 'Top compradores por produto'}
          </button>
        ))}
      </div>

      {aba === 'ranking' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 text-xs">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={incluirCF}
                onChange={(e) => setIncluirCF(e.target.checked)}
                className="w-3.5 h-3.5"
              />
              <span className="text-[color:var(--claude-stone)]">Incluir CONSUMIDOR FINAL (balcão anônimo)</span>
            </label>
          </div>

          <div className="claude-card overflow-hidden">
            {loadingRanking ? (
              <EmptyState variant="loading" title="Calculando RFM…" />
            ) : ranking.length === 0 ? (
              <EmptyState
                variant="empty"
                icon={<User size={32} />}
                title="Nenhum cliente com vendas no período."
                description="Importe um CSV de fechamento para popular o ranking."
              />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[color:var(--claude-cream-deep)]/40 text-[10px] uppercase tracking-widest text-[color:var(--claude-stone)]">
                    <th className="px-4 py-3 text-left">Cliente</th>
                    <th className="px-4 py-3 text-right">Valor ({periodo}d)</th>
                    <th className="px-4 py-3 text-right">Compras</th>
                    <th className="px-4 py-3 text-right">Ticket méd.</th>
                    <th className="px-4 py-3 text-right">Última</th>
                    <th className="px-4 py-3 text-center">R / F / M</th>
                    <th className="px-4 py-3 text-left">Segmento</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--border)]">
                  {ranking.map((c) => (
                    <tr
                      key={c.cliente_id}
                      onClick={() => setClienteDetalheId(c.cliente_id)}
                      className="hover:bg-[color:var(--claude-cream-deep)]/30 cursor-pointer transition-colors"
                      title="Ver detalhes do cliente">
                      <td className="px-4 py-2.5">
                        <div className="font-medium text-[color:var(--claude-ink)]">{c.nome}</div>
                        {c.is_consumidor_final && (
                          <div className="text-[10px] text-[color:var(--claude-stone)] uppercase">balcão anônimo</div>
                        )}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <MetricValue value={formatCurrency(c.valor_periodo)} size="sm" />
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">{c.total_compras_periodo}</td>
                      <td className="px-4 py-2.5 text-right">
                        <MetricValue value={formatCurrency(c.ticket_medio)} size="sm" />
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums text-[color:var(--claude-stone)]">
                        {c.dias_desde_ultima === null
                          ? '—'
                          : c.dias_desde_ultima === 0
                            ? 'hoje'
                            : `${c.dias_desde_ultima}d`}
                      </td>
                      <td className="px-4 py-2.5 text-center font-mono tabular-nums text-xs">
                        <span className="inline-flex gap-1">
                          <span className="px-1.5 py-0.5 rounded bg-[color:var(--claude-cream-deep)]">{c.score_r}</span>
                          <span className="px-1.5 py-0.5 rounded bg-[color:var(--claude-cream-deep)]">{c.score_f}</span>
                          <span className="px-1.5 py-0.5 rounded bg-[color:var(--claude-cream-deep)]">{c.score_m}</span>
                        </span>
                      </td>
                      <td className="px-4 py-2.5">
                        <span className={`pill ${SEGMENTO_TONE[c.segmento] || 'pill-muted'}`}>
                          {c.segmento_label}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="text-[11px] text-[color:var(--claude-stone)]">
            <strong>RFM:</strong> Recency (R, dias desde última compra) · Frequency (F, nº de transações) ·
            Monetary (M, R$ acumulado). Score 1–5 por dimensão; 5 é melhor.
          </div>
        </div>
      )}

      {aba === 'por_produto' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <label className="text-xs text-[color:var(--claude-stone)] uppercase tracking-wide">Produto:</label>
            <select
              value={produtoSel ?? ''}
              onChange={(e) => setProdutoSel(Number(e.target.value))}
              className="flex-1 px-3 py-2 text-sm border border-[color:var(--border)] rounded-lg bg-white"
            >
              {produtos.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.nome} ({p.sku})
                </option>
              ))}
            </select>
          </div>

          <div className="claude-card overflow-hidden">
            {loadingTop ? (
              <EmptyState variant="loading" title="Carregando…" />
            ) : topCompradores.length === 0 ? (
              <EmptyState variant="empty" compact title="Nenhum comprador no período." />
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-[color:var(--claude-cream-deep)]/40 text-[10px] uppercase tracking-widest text-[color:var(--claude-stone)]">
                    <th className="px-4 py-3 text-left">Cliente</th>
                    <th className="px-4 py-3 text-right">Quantidade</th>
                    <th className="px-4 py-3 text-right">Valor</th>
                    <th className="px-4 py-3 text-right">Transações</th>
                    <th className="px-4 py-3 text-right">Última</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--border)]">
                  {topCompradores.map((c, idx) => (
                    <tr key={c.cliente_id} className="hover:bg-[color:var(--claude-cream-deep)]/20">
                      <td className="px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          <span className="text-[color:var(--claude-stone)] font-mono tabular-nums w-6">
                            {idx + 1}.
                          </span>
                          <span className="font-medium text-[color:var(--claude-ink)]">{c.nome}</span>
                          {c.is_consumidor_final && (
                            <span className="text-[10px] text-[color:var(--claude-stone)] uppercase">balcão</span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">
                        {formatNumber(c.quantidade, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </td>
                      <td className="px-4 py-2.5 text-right">
                        <MetricValue value={formatCurrency(c.valor)} size="sm" />
                      </td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums">{c.transacoes}</td>
                      <td className="px-4 py-2.5 text-right font-mono tabular-nums text-[color:var(--claude-stone)]">
                        {c.ultima_compra || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {clienteDetalheId !== null && (
        <ClienteDetalheModal
          clienteId={clienteDetalheId}
          onClose={() => setClienteDetalheId(null)}
        />
      )}
    </div>
  )
}

// ============================================================================
// ClienteDetalheModal — drill-down do cliente (overlay, sem expandir nivel
// de navegacao; pode ser aberto da ClientesPage e do widget Dashboard).
// ============================================================================

function ClienteDetalheModal({ clienteId, onClose }: { clienteId: number; onClose: () => void }) {
  const [detalhe, setDetalhe] = useState<any | null>(null)
  const [evolucao, setEvolucao] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState<string | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const titleId = 'cliente-detalhe-title'

  useEffect(() => {
    setLoading(true)
    setErro(null)
    Promise.all([
      axios.get(`${API_URL}/clientes/${clienteId}`, { params: { periodo_dias: 90, top_skus_n: 10 } }),
      axios.get(`${API_URL}/clientes/${clienteId}/evolucao`, { params: { meses: 6 } }),
    ])
      .then(([d, e]) => {
        setDetalhe(d.data)
        setEvolucao(e.data?.meses || [])
      })
      .catch((err) => {
        console.error(err)
        setErro(err?.response?.data?.detail || 'Erro ao carregar detalhes do cliente.')
      })
      .finally(() => setLoading(false))
  }, [clienteId])

  // Fecha com ESC — mesmo padrao usado em ProdutoEditModal e ImportCSVModal
  useEscapeKey(onClose)
  useModalA11y(containerRef)

  // Helpers da timeline (escala dinamica + min height pra meses zerados)
  const evolMaxValor = Math.max(1, ...evolucao.map((m) => m.valor))
  const evolHasData = evolucao.some((m) => m.valor > 0)

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-slate-900/50 backdrop-blur-sm p-6 overflow-y-auto"
      onClick={onClose}
    >
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="bg-white rounded-3xl border border-slate-200 shadow-2xl w-full max-w-3xl my-8 flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-[color:var(--border)] flex items-start justify-between gap-4">
          <div className="min-w-0">
            <button
              onClick={onClose}
              className="text-[11px] font-bold uppercase tracking-widest text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)] mb-1 flex items-center gap-1"
            >
              ← Voltar para Clientes
            </button>
            <h3 id={titleId} className="headline text-3xl tracking-editorial truncate">
              {detalhe?.nome || (loading ? 'Carregando…' : 'Cliente')}
            </h3>
            {detalhe?.is_consumidor_final && (
              <p className="text-xs text-[color:var(--claude-stone)] uppercase tracking-widest mt-1">
                balcão · cliente coletivo de vendas anônimas
              </p>
            )}
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1 shrink-0" aria-label="Fechar">
            <X size={22} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {loading && <EmptyState variant="loading" title="Carregando detalhes…" />}
          {erro && (
            <EmptyState
              variant="error"
              icon={<AlertCircle size={32} />}
              title="Não consegui carregar este cliente."
              description={erro}
            />
          )}

          {!loading && !erro && detalhe && (
            <>
              {/* Cards-resumo do cliente */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="claude-card p-3">
                  <p className="section-label">Total comprado</p>
                  <p className="mt-1.5"><MetricValue value={formatCurrency(detalhe.total_compras_valor || 0)} size="lg" /></p>
                  <p className="text-[10px] text-[color:var(--claude-stone)] mt-0.5 uppercase tracking-widest">desde o cadastro</p>
                </div>
                <div className="claude-card p-3">
                  <p className="section-label">Compras totais</p>
                  <p className="mt-1.5"><MetricValue value={String(detalhe.total_compras_count || 0)} size="lg" /></p>
                  <p className="text-[10px] text-[color:var(--claude-stone)] mt-0.5 uppercase tracking-widest">transações</p>
                </div>
                <div className="claude-card p-3">
                  <p className="section-label">Ticket médio</p>
                  <p className="mt-1.5">
                    <MetricValue
                      value={formatCurrency(
                        (detalhe.total_compras_count || 0) > 0
                          ? (detalhe.total_compras_valor || 0) / detalhe.total_compras_count
                          : 0
                      )}
                      size="lg"
                    />
                  </p>
                  <p className="text-[10px] text-[color:var(--claude-stone)] mt-0.5 uppercase tracking-widest">por compra</p>
                </div>
                <div className="claude-card p-3">
                  <p className="section-label">Última compra</p>
                  <p className="kpi-value text-lg leading-none mt-1.5 text-[color:var(--claude-ink)]">
                    {detalhe.ultima_compra || '—'}
                  </p>
                  <p className="text-[10px] text-[color:var(--claude-stone)] mt-0.5 uppercase tracking-widest">
                    primeira: {detalhe.primeira_compra || '—'}
                  </p>
                </div>
              </div>

              {/* Evolução mensal — barras simples sem libs */}
              <div className="claude-card p-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="section-label">Evolução mensal · 6 meses</p>
                  <p className="text-[10px] text-[color:var(--claude-stone)]">valor por mês</p>
                </div>
                {evolHasData ? (
                  <div className="flex items-end gap-1.5 h-24">
                    {evolucao.map((m) => {
                      const altura = m.valor > 0 ? Math.max(6, (m.valor / evolMaxValor) * 88) : 2
                      const mesLabel = m.mes.slice(5, 7) + '/' + m.mes.slice(2, 4)
                      const tone = m.valor > 0 ? 'var(--claude-coral)' : 'var(--claude-stone)'
                      return (
                        <div key={m.mes} className="flex-1 flex flex-col items-center justify-end gap-1" title={`${mesLabel}: ${formatCurrency(m.valor)} · ${m.transacoes} compra(s)`}>
                          <div
                            className="w-full rounded-t-sm transition-all"
                            style={{ height: `${altura}px`, background: tone, opacity: m.valor > 0 ? 0.85 : 0.2 }}
                          />
                          <span className="text-[9px] text-[color:var(--claude-stone)] font-mono tabular-nums">{mesLabel}</span>
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <p className="text-xs text-[color:var(--claude-stone)] italic py-4 text-center">
                    Sem compras nos últimos 6 meses.
                  </p>
                )}
              </div>

              {/* Top SKUs */}
              <div className="claude-card overflow-hidden">
                <div className="px-4 py-3 border-b border-[color:var(--border)]">
                  <p className="section-label">Top SKUs comprados (90 dias)</p>
                </div>
                {(detalhe.top_skus || []).length === 0 ? (
                  <EmptyState variant="empty" compact title="Nenhuma compra na janela." />
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-[color:var(--claude-cream-deep)]/40 text-[10px] uppercase tracking-widest text-[color:var(--claude-stone)]">
                        <th className="px-4 py-2 text-left">Produto</th>
                        <th className="px-4 py-2 text-right">Qtd</th>
                        <th className="px-4 py-2 text-right">Valor</th>
                        <th className="px-4 py-2 text-right">Compras</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[color:var(--border)]">
                      {detalhe.top_skus.map((s: any) => (
                        <tr key={s.produto_id}>
                          <td className="px-4 py-2">
                            <div className="font-medium text-[color:var(--claude-ink)] truncate max-w-md">{s.nome}</div>
                            <div className="text-[10px] text-[color:var(--claude-stone)]">SKU {s.sku}</div>
                          </td>
                          <td className="px-4 py-2 text-right font-mono tabular-nums">
                            {formatNumber(s.quantidade, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                          </td>
                          <td className="px-4 py-2 text-right">
                            <MetricValue value={formatCurrency(s.valor)} size="sm" />
                          </td>
                          <td className="px-4 py-2 text-right font-mono tabular-nums">{s.transacoes}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </>
          )}
        </div>

        <div className="p-4 border-t border-[color:var(--border)] bg-[color:var(--claude-cream-deep)]/30 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 text-sm font-semibold text-[color:var(--claude-ink)] hover:bg-white rounded-lg transition-colors"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  )
}

function HistoricoPage() {
  const [movs, setMovs] = useState<Movimentacao[]>([])
  const [loading, setLoading] = useState(true)
  const [dias, setDias] = useState(30)
  const [filtroTipo, setFiltroTipo] = useState<'' | 'ENTRADA' | 'SAIDA' | 'QUEBRA'>('')
  const [confirmando, setConfirmando] = useState<Movimentacao | null>(null)
  const [excluindo, setExcluindo] = useState(false)
  const [reconciliando, setReconciliando] = useState(false)
  const [confirmReconciliar, setConfirmReconciliar] = useState(false)
  const [toast, setToast] = useState<{ tipo: 'ok' | 'erro'; msg: string } | null>(null)

  const executarReconciliacao = async () => {
    setConfirmReconciliar(false)
    if (reconciliando) return
    setReconciliando(true)
    try {
      const res = await axios.post(`${API_URL}/admin/reconciliar-estoques`)
      const d = res.data?.detalhe
      setToast({
        tipo: 'ok',
        msg: `Reconciliação ok: ${d?.produtos_verificados ?? 0} verificados, ${d?.produtos_ajustados ?? 0} ajustados, ${d?.produtos_desativados ?? 0} desativados.`
      })
      await carregar()
    } catch (e: any) {
      setToast({ tipo: 'erro', msg: e?.response?.data?.detail || e.message || 'Erro ao reconciliar.' })
    } finally {
      setReconciliando(false)
      setTimeout(() => setToast(null), 6000)
    }
  }

  const reconciliar = () => {
    if (reconciliando) return
    setConfirmReconciliar(true)
  }

  const carregar = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ dias: String(dias) })
      if (filtroTipo) params.append('tipo', filtroTipo)
      const res = await axios.get(`${API_URL}/historico/movimentacoes?${params}`)
      setMovs(res.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { carregar() }, [dias, filtroTipo])

  const confirmarExclusao = async () => {
    if (!confirmando) return
    setExcluindo(true)
    try {
      if (confirmando.tipo === 'ENTRADA') {
        await axios.delete(`${API_URL}/entradas/${confirmando.movimentacao_id}`)
      } else if (confirmando.tipo === 'QUEBRA') {
        await axios.delete(`${API_URL}/quebras/${confirmando.movimentacao_id}`)
      } else if (confirmando.venda_id) {
        await axios.delete(`${API_URL}/vendas/${confirmando.venda_id}`)
      } else {
        throw new Error('Venda órfã — sem venda_id para deletar.')
      }
      const labelTipo = confirmando.tipo === 'ENTRADA' ? 'Entrada' : confirmando.tipo === 'QUEBRA' ? 'Quebra' : 'Venda'
      setToast({ tipo: 'ok', msg: `${labelTipo} de ${confirmando.produto_nome} excluída. Estoque revertido.` })
      setConfirmando(null)
      await carregar()
    } catch (e: any) {
      setToast({ tipo: 'erro', msg: e?.response?.data?.detail || e.message || 'Erro ao excluir.' })
    } finally {
      setExcluindo(false)
      setTimeout(() => setToast(null), 4500)
    }
  }

  const totais = {
    entradas: movs.filter(m => m.tipo === 'ENTRADA').length,
    saidas: movs.filter(m => m.tipo === 'SAIDA').length,
    quebras: movs.filter(m => m.tipo === 'QUEBRA').length,
    valorEntradas: movs.filter(m => m.tipo === 'ENTRADA').reduce((s, m) => s + m.valor_total, 0),
    valorSaidas: movs.filter(m => m.tipo === 'SAIDA').reduce((s, m) => s + m.valor_total, 0),
    valorQuebras: movs.filter(m => m.tipo === 'QUEBRA').reduce((s, m) => s + m.valor_total, 0),
  }

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-end">
        <div>
          <p className="section-label mb-1">Auditoria · últimos {dias} dias</p>
          <h2 className="headline text-4xl tracking-editorial">Histórico de Movimentações</h2>
          <p className="text-[color:var(--claude-stone)] mt-1">
            Revise entradas e saídas lançadas. Excluir reverte o estoque automaticamente.
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <button
            onClick={reconciliar}
            disabled={reconciliando}
            title="Recalcula estoque e custo de todos os produtos a partir do log de movimentações"
            className="px-3 py-2 text-sm rounded-lg border border-[color:var(--border)] text-[color:var(--claude-ink)] hover:bg-[color:var(--claude-cream-deep)] disabled:opacity-50 flex items-center gap-1.5"
          >
            {reconciliando ? 'Reconciliando…' : 'Reconciliar estoques'}
          </button>
          <select
            value={filtroTipo}
            onChange={(e) => setFiltroTipo(e.target.value as any)}
            className="px-3 py-2 text-sm border border-[color:var(--border)] rounded-lg bg-white"
          >
            <option value="">Todos os tipos</option>
            <option value="ENTRADA">Apenas entradas</option>
            <option value="SAIDA">Apenas saídas</option>
            <option value="QUEBRA">Apenas quebras</option>
          </select>
          <select
            value={dias}
            onChange={(e) => setDias(Number(e.target.value))}
            className="px-3 py-2 text-sm border border-[color:var(--border)] rounded-lg bg-white"
          >
            <option value={7}>7 dias</option>
            <option value={30}>30 dias</option>
            <option value={90}>90 dias</option>
            <option value={365}>1 ano</option>
          </select>
        </div>
      </header>

      {/* Sumário */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="claude-card p-4">
          <p className="section-label">Entradas</p>
          <p className="mt-1">
            <MetricValue value={totais.entradas} size="2xl" toneClass="text-[color:var(--claude-sage)]" />
          </p>
          <p className="text-xs text-[color:var(--claude-stone)] mt-1 mono">{formatCurrency(totais.valorEntradas)}</p>
        </div>
        <div className="claude-card p-4">
          <p className="section-label">Saídas</p>
          <p className="mt-1">
            <MetricValue value={totais.saidas} size="2xl" toneClass="text-[color:var(--claude-coral)]" />
          </p>
          <p className="text-xs text-[color:var(--claude-stone)] mt-1 mono">{formatCurrency(totais.valorSaidas)}</p>
        </div>
        <div className="claude-card p-4">
          <p className="section-label">Quebras</p>
          <p className="mt-1">
            <MetricValue value={totais.quebras} size="2xl" toneClass="text-[color:var(--claude-amber)]" />
          </p>
          <p className="text-xs text-[color:var(--claude-stone)] mt-1 mono">{formatCurrency(totais.valorQuebras)}</p>
        </div>
        <div className="claude-card p-4">
          <p className="section-label">Fluxo líquido</p>
          <p className="mt-1">
            <MetricValue
              value={formatCurrency(totais.valorSaidas - totais.valorEntradas - totais.valorQuebras, { signed: true })}
              size="2xl"
              toneClass={totais.valorSaidas - totais.valorEntradas - totais.valorQuebras >= 0 ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]'}
            />
          </p>
          <p className="text-xs text-[color:var(--claude-stone)] mt-1">Receita − Custo entradas − Quebras</p>
        </div>
      </div>

      {/* Tabela */}
      <div className="claude-card overflow-hidden">
        {loading ? (
          <EmptyState variant="loading" title="Carregando…" />
        ) : movs.length === 0 ? (
          <EmptyState
            variant="empty"
            icon={<FileText size={32} />}
            title="Nenhuma movimentação no período."
            description="Lance entradas e vendas pra começar o histórico."
          />
        ) : (
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-[color:var(--border)] bg-[color:var(--claude-cream-deep)]/40">
                <th className="px-4 py-3 section-label">Tipo</th>
                <th className="px-4 py-3 section-label">Produto</th>
                <th className="px-4 py-3 section-label text-right">Qtd</th>
                <th className="px-4 py-3 section-label text-right">Peso</th>
                <th className="px-4 py-3 section-label text-right">Preço/Custo</th>
                <th className="px-4 py-3 section-label text-right">Valor total</th>
                <th className="px-4 py-3 section-label">Cidade</th>
                <th className="px-4 py-3 section-label">Data</th>
                <th className="px-4 py-3 section-label text-center">Ação</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[color:var(--border)]">
              {movs.map(m => {
                const isEntrada = m.tipo === 'ENTRADA'
                const isQuebra = m.tipo === 'QUEBRA'
                const acentColor = isEntrada ? 'var(--claude-sage)' : isQuebra ? 'var(--claude-amber)' : 'var(--claude-coral)'
                const Icon = isEntrada ? ArrowDownCircle : isQuebra ? Skull : ArrowUpCircle
                const dataFmt = formatDateTime(m.data)
                const podeExcluir = isEntrada || isQuebra || m.venda_id !== null
                return (
                  <tr key={`${m.tipo}-${m.movimentacao_id}`} className="hover:bg-[color:var(--claude-cream-deep)]/30 transition-colors">
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide"
                            style={{ color: acentColor }}>
                        <Icon size={14} /> {m.tipo}
                      </span>
                      {isQuebra && m.motivo && (
                        <p className="text-[10px] text-[color:var(--claude-stone)] mt-0.5 capitalize">{m.motivo}</p>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-[color:var(--claude-ink)] truncate max-w-[220px]">{m.produto_nome}</p>
                      {m.produto_sku && <p className="text-[10px] text-[color:var(--claude-stone)] mono">{m.produto_sku}</p>}
                    </td>
                    <td className="px-4 py-3 text-right mono text-sm text-[color:var(--claude-ink)]">{formatNumber(m.quantidade, { maximumFractionDigits: 2 })}</td>
                    <td className="px-4 py-3 text-right mono text-sm text-[color:var(--claude-stone)]">{m.peso > 0 ? formatNumber(m.peso, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—'}</td>
                    <td className="px-4 py-3 text-right mono text-sm text-[color:var(--claude-ink)]">{formatCurrency(m.custo_unitario)}</td>
                    <td className="px-4 py-3 text-right mono text-sm font-semibold" style={{ color: acentColor }}>
                      {formatCurrency(m.valor_total)}
                    </td>
                    <td className="px-4 py-3 text-xs text-[color:var(--claude-stone)]">{m.cidade || '—'}</td>
                    <td className="px-4 py-3 text-xs text-[color:var(--claude-stone)] mono">{dataFmt}</td>
                    <td className="px-4 py-3 text-center">
                      <button
                        onClick={() => setConfirmando(m)}
                        disabled={!podeExcluir}
                        title={podeExcluir ? 'Excluir e reverter estoque' : 'Sem vínculo com venda — não é possível excluir por aqui'}
                        className="p-1.5 rounded-lg text-[color:var(--claude-stone)] hover:text-[color:var(--claude-coral)] hover:bg-[color:var(--claude-coral)]/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Modal confirmação */}
      {confirmando && (
        <div className="fixed inset-0 bg-[color:var(--claude-ink)]/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
             onClick={() => !excluindo && setConfirmando(null)}>
          <div className="claude-card p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full flex items-center justify-center"
                     style={{ background: 'color-mix(in srgb, var(--claude-coral) 15%, transparent)' }}>
                  <AlertTriangle size={20} className="text-[color:var(--claude-coral)]" />
                </div>
                <div>
                  <p className="section-label">Confirmar exclusão</p>
                  <h3 className="headline text-xl">Reverter {confirmando.tipo === 'ENTRADA' ? 'entrada' : confirmando.tipo === 'QUEBRA' ? 'quebra' : 'venda'}?</h3>
                </div>
              </div>
              <button onClick={() => !excluindo && setConfirmando(null)}
                      className="p-1 text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)]">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-2 text-sm text-[color:var(--claude-ink)] mb-5">
              <p><span className="text-[color:var(--claude-stone)]">Produto:</span> <span className="font-medium">{confirmando.produto_nome}</span></p>
              <p><span className="text-[color:var(--claude-stone)]">Quantidade:</span> <span className="mono">{formatNumber(confirmando.quantidade, { maximumFractionDigits: 2 })}</span></p>
              <p><span className="text-[color:var(--claude-stone)]">Valor:</span> <span className="mono">{formatCurrency(confirmando.valor_total)}</span></p>
              <div className="mt-3 p-3 rounded-lg text-xs"
                   style={{ background: 'color-mix(in srgb, var(--claude-amber) 10%, transparent)', color: 'var(--claude-ink)' }}>
                {confirmando.tipo === 'ENTRADA' && (
                  <>⚠ Estoque cairá {confirmando.quantidade} un. Custo médio será recalculado a partir das entradas restantes.</>
                )}
                {confirmando.tipo === 'QUEBRA' && (
                  <>↩ Estoque voltará +{confirmando.quantidade} un. Quebra do mês ({confirmando.data?.slice(0, 7)}) será decrementada do DRE (linha 4.2).</>
                )}
                {confirmando.tipo === 'SAIDA' && (
                  <>↩ Estoque voltará +{confirmando.quantidade} un. Faturamento e margem do dia {confirmando.data?.slice(0, 10)} serão decrementados.</>
                )}
              </div>
            </div>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmando(null)}
                disabled={excluindo}
                className="px-4 py-2 text-sm rounded-lg border border-[color:var(--border)] text-[color:var(--claude-ink)] hover:bg-[color:var(--claude-cream-deep)] disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={confirmarExclusao}
                disabled={excluindo}
                className="px-4 py-2 text-sm rounded-lg font-medium text-white hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                style={{ background: 'var(--claude-coral)' }}
              >
                {excluindo ? 'Excluindo…' : <><Trash2 size={14} /> Confirmar exclusão</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 claude-card px-4 py-3 flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2"
             style={{
               borderLeftWidth: '4px',
               borderLeftColor: toast.tipo === 'ok' ? 'var(--claude-sage)' : 'var(--claude-coral)'
             }}>
          {toast.tipo === 'ok' ? <Check size={16} className="text-[color:var(--claude-sage)]" /> : <AlertCircle size={16} className="text-[color:var(--claude-coral)]" />}
          <p className="text-sm text-[color:var(--claude-ink)]">{toast.msg}</p>
        </div>
      )}

      {/* Confirmar reconciliação global (substitui window.confirm) */}
      <Confirm
        open={confirmReconciliar}
        title="Reconciliar estoques?"
        body={
          <p>
            Recalcula <strong>estoque e custo de TODOS os produtos</strong> a partir
            do log de movimentações. Corrige estado inconsistente e desativa produtos
            sem movimentação. Esta operação pode demorar segundos em bancos grandes.
          </p>
        }
        confirmLabel="Reconciliar"
        loading={reconciliando}
        onConfirm={executarReconciliacao}
        onCancel={() => setConfirmReconciliar(false)}
      />
    </div>
  )
}

// ============================================================================
// QUEBRAS / PERDAS
// ============================================================================

const MOTIVOS_QUEBRA = [
  { value: 'vencimento', label: 'Vencimento', desc: 'Produto venceu e não pode ser vendido' },
  { value: 'avaria', label: 'Avaria', desc: 'Quebra física, embalagem danificada' },
  { value: 'desvio', label: 'Desvio', desc: 'Furto, perda, sumiço inexplicado' },
  { value: 'doacao', label: 'Doação', desc: 'Doado / dado de cortesia' },
] as const

type QuebraOut = {
  movimentacao_id: number
  produto_id: number
  produto_nome: string
  produto_sku: string | null
  quantidade: number
  peso: number
  custo_unitario: number
  valor_total: number
  motivo: string
  cidade: string | null
  observacao: string | null
  data: string | null
}

type QuebraResumo = {
  mes: string
  valor_total: number
  quantidade_total: number
  eventos: number
  pct_faturamento: number
  por_motivo: Array<{ motivo: string; quantidade: number; valor: number; eventos: number }>
  top_produtos: Array<{ produto_id: number; produto_nome: string; produto_sku: string | null; quantidade: number; valor: number; eventos: number }>
}

function QuebrasPage() {
  const [tab, setTab] = useState<'registrar' | 'historico'>('registrar')
  const [produtos, setProdutos] = useState<Produto[]>([])
  const [quebras, setQuebras] = useState<QuebraOut[]>([])
  const [resumo, setResumo] = useState<QuebraResumo | null>(null)
  const [loading, setLoading] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [toast, setToast] = useState<{ tipo: 'ok' | 'erro'; msg: string } | null>(null)
  const [confirmando, setConfirmando] = useState<QuebraOut | null>(null)
  const [excluindo, setExcluindo] = useState(false)

  // form state
  const [busca, setBusca] = useState('')
  const [produtoSelecionado, setProdutoSelecionado] = useState<any>(null)
  const [quantidade, setQuantidade] = useState('')
  const [peso, setPeso] = useState('')
  const [motivo, setMotivo] = useState('vencimento')
  const [cidade, setCidade] = useState<string>('')
  const [filtroMotivo, setFiltroMotivo] = useState<string>('')
  const [dias, setDias] = useState(30)

  const carregar = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ dias: String(dias) })
      if (filtroMotivo) params.append('motivo', filtroMotivo)
      const [a, b] = await Promise.all([
        axios.get(`${API_URL}/quebras?${params}`),
        axios.get(`${API_URL}/quebras/resumo`),
      ])
      setQuebras(a.data)
      setResumo(b.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    axios.get(`${API_URL}/produtos`).then(res => setProdutos(res.data.filter((p: any) => p.ativo)))
  }, [])

  useEffect(() => { carregar() }, [dias, filtroMotivo])

  const candidatos = busca.length >= 2
    ? produtos.filter(p =>
        p.nome?.toLowerCase().includes(busca.toLowerCase()) ||
        p.sku?.toLowerCase().includes(busca.toLowerCase()) ||
        p.codigo?.toLowerCase().includes(busca.toLowerCase())
      ).slice(0, 6)
    : []

  const salvar = async () => {
    if (!produtoSelecionado) {
      setToast({ tipo: 'erro', msg: 'Selecione um produto.' })
      return
    }
    const q = parseFloat(quantidade.replace(',', '.'))
    if (!q || q <= 0) {
      setToast({ tipo: 'erro', msg: 'Quantidade inválida.' })
      return
    }
    if (q > produtoSelecionado.estoque_qtd) {
      setToast({ tipo: 'erro', msg: `Estoque insuficiente. Disponível: ${produtoSelecionado.estoque_qtd}` })
      return
    }
    const p = peso ? parseFloat(peso.replace(',', '.')) : null
    setSalvando(true)
    try {
      const payload: any = {
        produto_id: produtoSelecionado.id,
        quantidade: q,
        motivo,
      }
      if (p !== null && !Number.isNaN(p)) payload.peso = p
      if (cidade) payload.cidade = cidade
      const res = await axios.post(`${API_URL}/quebras`, payload)
      setToast({
        tipo: 'ok',
        msg: `Quebra registrada: ${formatNumber(q, { maximumFractionDigits: 2 })} un. de ${produtoSelecionado.nome} (${formatCurrency(res.data.valor_total)}).`,
      })
      // limpa formulário
      setProdutoSelecionado(null)
      setBusca('')
      setQuantidade('')
      setPeso('')
      // refresca produtos pra mostrar estoque atualizado
      const r = await axios.get(`${API_URL}/produtos`)
      setProdutos(r.data.filter((p: any) => p.ativo))
      await carregar()
    } catch (e: any) {
      setToast({ tipo: 'erro', msg: e?.response?.data?.detail || e.message || 'Erro ao registrar quebra.' })
    } finally {
      setSalvando(false)
      setTimeout(() => setToast(null), 5000)
    }
  }

  const confirmarExclusao = async () => {
    if (!confirmando) return
    setExcluindo(true)
    try {
      await axios.delete(`${API_URL}/quebras/${confirmando.movimentacao_id}`)
      setToast({ tipo: 'ok', msg: `Quebra de ${confirmando.produto_nome} revertida.` })
      setConfirmando(null)
      const r = await axios.get(`${API_URL}/produtos`)
      setProdutos(r.data.filter((p: any) => p.ativo))
      await carregar()
    } catch (e: any) {
      setToast({ tipo: 'erro', msg: e?.response?.data?.detail || e.message || 'Erro ao excluir.' })
    } finally {
      setExcluindo(false)
      setTimeout(() => setToast(null), 4500)
    }
  }

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-6">
      <header>
        <p className="section-label mb-1">Controle · perdas de estoque</p>
        <h2 className="headline text-4xl tracking-editorial">Quebras e Perdas</h2>
        <p className="text-[color:var(--claude-stone)] mt-1">
          Registre vencimentos, avarias, desvios e doações. Reduz estoque sem contar como demanda; impacta a linha 4.2 do DRE.
        </p>
      </header>

      {/* KPIs do mês */}
      {resumo && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="claude-card p-4">
            <p className="section-label">Valor perdido · {resumo.mes}</p>
            <p className="kpi-value text-2xl text-[color:var(--claude-coral)] mt-1">
              {formatCurrency(resumo.valor_total)}
            </p>
            <p className="text-xs text-[color:var(--claude-stone)] mt-1">{resumo.eventos} evento(s)</p>
          </div>
          <div className="claude-card p-4">
            <p className="section-label">Quantidade total</p>
            <p className="kpi-value text-2xl text-[color:var(--claude-ink)] mt-1 mono">
              {formatNumber(resumo.quantidade_total, { maximumFractionDigits: 2 })}
            </p>
            <p className="text-xs text-[color:var(--claude-stone)] mt-1">unidades baixadas</p>
          </div>
          <div className="claude-card p-4">
            <p className="section-label">% do faturamento</p>
            <p className={`kpi-value text-2xl mt-1 ${resumo.pct_faturamento > 0.02 ? 'text-[color:var(--claude-coral)]' : 'text-[color:var(--claude-amber)]'}`}>
              {formatPercent(resumo.pct_faturamento, { maximumFractionDigits: 2 })}
            </p>
            <p className="text-xs text-[color:var(--claude-stone)] mt-1">benchmark ABRAS: 1,5–2%</p>
          </div>
          <div className="claude-card p-4">
            <p className="section-label">Motivo dominante</p>
            <p className="kpi-value text-xl text-[color:var(--claude-ink)] mt-1 capitalize">
              {resumo.por_motivo[0]?.motivo || '—'}
            </p>
            <p className="text-xs text-[color:var(--claude-stone)] mt-1 mono">
              {resumo.por_motivo[0]
                ? formatCurrency(resumo.por_motivo[0].valor)
                : 'sem registros'}
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[color:var(--border)]">
        {(['registrar', 'historico'] as const).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${
              tab === t
                ? 'border-[color:var(--claude-coral)] text-[color:var(--claude-ink)]'
                : 'border-transparent text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)]'
            }`}
          >
            {t === 'registrar' ? 'Registrar' : 'Histórico'}
          </button>
        ))}
      </div>

      {tab === 'registrar' && (
        <div className="claude-card p-6 space-y-4">
          {/* Produto */}
          <div>
            <label className="section-label">Produto</label>
            {produtoSelecionado ? (
              <div className="mt-1 flex items-center justify-between p-3 rounded-lg bg-[color:var(--claude-cream-deep)]/40 border border-[color:var(--border)]">
                <div>
                  <p className="text-sm font-medium text-[color:var(--claude-ink)]">{produtoSelecionado.nome}</p>
                  <p className="text-xs text-[color:var(--claude-stone)] mono mt-0.5">
                    {produtoSelecionado.sku} · estoque: {formatNumber(produtoSelecionado.estoque_qtd, { maximumFractionDigits: 2 })} un. · custo: {formatCurrency(produtoSelecionado.custo)}
                  </p>
                </div>
                <button
                  onClick={() => { setProdutoSelecionado(null); setBusca('') }}
                  className="p-1 text-[color:var(--claude-stone)] hover:text-[color:var(--claude-coral)]"
                >
                  <X size={18} />
                </button>
              </div>
            ) : (
              <div className="relative mt-1">
                <input
                  type="text"
                  value={busca}
                  onChange={e => setBusca(e.target.value)}
                  placeholder="Busque por nome, SKU ou código..."
                  className="w-full px-3 py-2 border border-[color:var(--border)] rounded-lg bg-white text-sm"
                />
                {candidatos.length > 0 && (
                  <div className="absolute z-10 left-0 right-0 mt-1 claude-card max-h-72 overflow-y-auto">
                    {candidatos.map(p => (
                      <button
                        key={p.id}
                        onClick={() => { setProdutoSelecionado(p); setBusca(p.nome) }}
                        className="w-full text-left px-3 py-2 hover:bg-[color:var(--claude-cream-deep)]/40 border-b border-[color:var(--border)] last:border-0"
                      >
                        <p className="text-sm font-medium text-[color:var(--claude-ink)]">{p.nome}</p>
                        <p className="text-xs text-[color:var(--claude-stone)] mono">
                          {p.sku} · estoque: {formatNumber(p.estoque_qtd, { maximumFractionDigits: 2 })} · custo: {formatCurrency(p.custo)}
                        </p>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Qtd + Peso */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="section-label">Quantidade</label>
              <input
                type="text"
                value={quantidade}
                onChange={e => setQuantidade(e.target.value)}
                placeholder="ex: 5"
                className="w-full mt-1 px-3 py-2 border border-[color:var(--border)] rounded-lg bg-white text-sm mono"
              />
              {produtoSelecionado && quantidade && parseFloat(quantidade.replace(',', '.')) > 0 && (
                <p className="text-xs text-[color:var(--claude-stone)] mt-1 mono">
                  Valor: {formatCurrency(parseFloat(quantidade.replace(',', '.')) * (produtoSelecionado.custo || 0))}
                </p>
              )}
            </div>
            <div>
              <label className="section-label">Peso (opcional)</label>
              <input
                type="text"
                value={peso}
                onChange={e => setPeso(e.target.value)}
                placeholder="kg (deixe vazio para usar peso médio)"
                className="w-full mt-1 px-3 py-2 border border-[color:var(--border)] rounded-lg bg-white text-sm mono"
              />
            </div>
          </div>

          {/* Motivo */}
          <div>
            <label className="section-label">Motivo</label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-1">
              {MOTIVOS_QUEBRA.map(m => (
                <button
                  key={m.value}
                  onClick={() => setMotivo(m.value)}
                  className={`p-3 rounded-lg border text-left transition-colors ${
                    motivo === m.value
                      ? 'border-[color:var(--claude-coral)] bg-[color:var(--claude-coral)]/5'
                      : 'border-[color:var(--border)] hover:bg-[color:var(--claude-cream-deep)]/40'
                  }`}
                >
                  <p className="text-sm font-medium text-[color:var(--claude-ink)]">{m.label}</p>
                  <p className="text-[10px] text-[color:var(--claude-stone)] mt-0.5 leading-tight">{m.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Cidade */}
          <div>
            <label className="section-label">Cidade (opcional)</label>
            <select
              value={cidade}
              onChange={e => setCidade(e.target.value)}
              className="w-full mt-1 px-3 py-2 border border-[color:var(--border)] rounded-lg bg-white text-sm"
            >
              <option value="">—</option>
              {CIDADES.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* Botão */}
          <div className="flex justify-end pt-2">
            <button
              onClick={salvar}
              disabled={salvando || !produtoSelecionado || !quantidade}
              className="px-5 py-2.5 text-sm rounded-lg font-medium text-white hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
              style={{ background: 'var(--claude-coral)' }}
            >
              {salvando ? 'Registrando…' : <><Skull size={14} /> Registrar quebra</>}
            </button>
          </div>
        </div>
      )}

      {tab === 'historico' && (
        <>
          {/* Filtros */}
          <div className="flex gap-2 items-center justify-end">
            <select
              value={filtroMotivo}
              onChange={(e) => setFiltroMotivo(e.target.value)}
              className="px-3 py-2 text-sm border border-[color:var(--border)] rounded-lg bg-white"
            >
              <option value="">Todos os motivos</option>
              {MOTIVOS_QUEBRA.map(m => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
            <select
              value={dias}
              onChange={(e) => setDias(Number(e.target.value))}
              className="px-3 py-2 text-sm border border-[color:var(--border)] rounded-lg bg-white"
            >
              <option value={7}>7 dias</option>
              <option value={30}>30 dias</option>
              <option value={90}>90 dias</option>
              <option value={365}>1 ano</option>
            </select>
          </div>

          {/* Tabela */}
          <div className="claude-card overflow-hidden">
            {loading ? (
              <EmptyState variant="loading" title="Carregando…" />
            ) : quebras.length === 0 ? (
              <EmptyState
                variant="empty"
                icon={<Skull size={32} />}
                title="Nenhuma quebra no período."
                description="Bom sinal! Continue de olho no estoque."
              />
            ) : (
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-[color:var(--border)] bg-[color:var(--claude-cream-deep)]/40">
                    <th className="px-4 py-3 section-label">Data</th>
                    <th className="px-4 py-3 section-label">Produto</th>
                    <th className="px-4 py-3 section-label">Motivo</th>
                    <th className="px-4 py-3 section-label text-right">Qtd</th>
                    <th className="px-4 py-3 section-label text-right">Custo unit.</th>
                    <th className="px-4 py-3 section-label text-right">Valor perdido</th>
                    <th className="px-4 py-3 section-label">Cidade</th>
                    <th className="px-4 py-3 section-label text-center">Ação</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--border)]">
                  {quebras.map(q => {
                    const dataFmt = formatDateTime(q.data)
                    return (
                      <tr key={q.movimentacao_id} className="hover:bg-[color:var(--claude-cream-deep)]/30 transition-colors">
                        <td className="px-4 py-3 text-xs text-[color:var(--claude-stone)] mono">{dataFmt}</td>
                        <td className="px-4 py-3">
                          <p className="text-sm font-medium text-[color:var(--claude-ink)] truncate max-w-[220px]">{q.produto_nome}</p>
                          {q.produto_sku && <p className="text-[10px] text-[color:var(--claude-stone)] mono">{q.produto_sku}</p>}
                        </td>
                        <td className="px-4 py-3">
                          <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wide capitalize"
                                style={{
                                  background: 'color-mix(in srgb, var(--claude-amber) 18%, transparent)',
                                  color: 'var(--claude-ink)',
                                }}>
                            {q.motivo}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-right mono text-sm text-[color:var(--claude-ink)]">{formatNumber(q.quantidade, { maximumFractionDigits: 2 })}</td>
                        <td className="px-4 py-3 text-right mono text-sm text-[color:var(--claude-stone)]">{formatCurrency(q.custo_unitario)}</td>
                        <td className="px-4 py-3 text-right mono text-sm font-semibold text-[color:var(--claude-coral)]">
                          {formatCurrency(q.valor_total)}
                        </td>
                        <td className="px-4 py-3 text-xs text-[color:var(--claude-stone)]">{q.cidade || '—'}</td>
                        <td className="px-4 py-3 text-center">
                          <button
                            onClick={() => setConfirmando(q)}
                            title="Reverter quebra (devolve estoque)"
                            className="p-1.5 rounded-lg text-[color:var(--claude-stone)] hover:text-[color:var(--claude-coral)] hover:bg-[color:var(--claude-coral)]/10 transition-colors"
                          >
                            <Trash2 size={16} />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* Top produtos perdidos */}
          {resumo && resumo.top_produtos.length > 0 && (
            <div className="claude-card p-6">
              <p className="section-label mb-3">Top produtos com mais perda · {resumo.mes}</p>
              <div className="space-y-2">
                {resumo.top_produtos.slice(0, 5).map((p, i) => (
                  <div key={p.produto_id} className="flex items-center justify-between py-2 border-b border-[color:var(--border)] last:border-0">
                    <div className="flex items-center gap-3">
                      <span className="w-6 h-6 rounded-full bg-[color:var(--claude-cream-deep)] text-xs font-bold flex items-center justify-center">{i + 1}</span>
                      <div>
                        <p className="text-sm font-medium text-[color:var(--claude-ink)]">{p.produto_nome}</p>
                        <p className="text-[10px] text-[color:var(--claude-stone)] mono">{p.produto_sku || '—'} · {p.eventos} evento(s)</p>
                      </div>
                    </div>
                    <p className="mono text-sm font-semibold text-[color:var(--claude-coral)]">
                      {formatCurrency(p.valor)}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Modal confirmação */}
      {confirmando && (
        <div className="fixed inset-0 bg-[color:var(--claude-ink)]/40 backdrop-blur-sm flex items-center justify-center z-50 p-4"
             onClick={() => !excluindo && setConfirmando(null)}>
          <div className="claude-card p-6 max-w-md w-full" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full flex items-center justify-center"
                     style={{ background: 'color-mix(in srgb, var(--claude-coral) 15%, transparent)' }}>
                  <AlertTriangle size={20} className="text-[color:var(--claude-coral)]" />
                </div>
                <div>
                  <p className="section-label">Confirmar exclusão</p>
                  <h3 className="headline text-xl">Reverter quebra?</h3>
                </div>
              </div>
              <button onClick={() => !excluindo && setConfirmando(null)}
                      className="p-1 text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)]">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-2 text-sm text-[color:var(--claude-ink)] mb-5">
              <p><span className="text-[color:var(--claude-stone)]">Produto:</span> <span className="font-medium">{confirmando.produto_nome}</span></p>
              <p><span className="text-[color:var(--claude-stone)]">Motivo:</span> <span className="capitalize">{confirmando.motivo}</span></p>
              <p><span className="text-[color:var(--claude-stone)]">Quantidade:</span> <span className="mono">{formatNumber(confirmando.quantidade, { maximumFractionDigits: 2 })}</span></p>
              <p><span className="text-[color:var(--claude-stone)]">Valor:</span> <span className="mono">{formatCurrency(confirmando.valor_total)}</span></p>
              <div className="mt-3 p-3 rounded-lg text-xs"
                   style={{ background: 'color-mix(in srgb, var(--claude-amber) 10%, transparent)', color: 'var(--claude-ink)' }}>
                ↩ Estoque voltará +{confirmando.quantidade} un. CMP do produto será recalculado. Linha 4.2 do DRE será decrementada.
              </div>
            </div>

            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setConfirmando(null)}
                disabled={excluindo}
                className="px-4 py-2 text-sm rounded-lg border border-[color:var(--border)] text-[color:var(--claude-ink)] hover:bg-[color:var(--claude-cream-deep)] disabled:opacity-50"
              >
                Cancelar
              </button>
              <button
                onClick={confirmarExclusao}
                disabled={excluindo}
                className="px-4 py-2 text-sm rounded-lg font-medium text-white hover:opacity-90 disabled:opacity-50 flex items-center gap-2"
                style={{ background: 'var(--claude-coral)' }}
              >
                {excluindo ? 'Excluindo…' : <><Trash2 size={14} /> Confirmar exclusão</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 claude-card px-4 py-3 flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2"
             style={{
               borderLeftWidth: '4px',
               borderLeftColor: toast.tipo === 'ok' ? 'var(--claude-sage)' : 'var(--claude-coral)'
             }}>
          {toast.tipo === 'ok' ? <Check size={16} className="text-[color:var(--claude-sage)]" /> : <AlertCircle size={16} className="text-[color:var(--claude-coral)]" />}
          <p className="text-sm text-[color:var(--claude-ink)]">{toast.msg}</p>
        </div>
      )}
    </div>
  )
}

// ============================================================================
// DRE — Demonstração do Resultado do Exercício
// ============================================================================

type DRELinha = {
  codigo: string
  label: string
  valor: number
  pct_receita: number
  tipo: string // receita | subtotal | deducao | despesa | resultado
  nivel: number
}

type DREMensal = {
  mes: string
  regime: string | null
  receita_bruta: number
  impostos_venda: number
  devolucoes: number
  receita_liquida: number
  cmv: number
  quebras: number
  lucro_bruto: number
  margem_bruta_pct: number
  despesas_vendas: number
  despesas_admin: number
  ebitda: number
  ebitda_pct: number
  depreciacao: number
  ebit: number
  resultado_financeiro: number
  lair: number
  ir_csll: number
  lucro_liquido: number
  margem_liquida_pct: number
  linhas: DRELinha[]
}

type DRECompPonto = {
  mes: string
  receita_bruta: number
  receita_liquida: number
  cmv: number
  quebras: number
  lucro_bruto: number
  ebitda: number
  lucro_liquido: number
  margem_bruta_pct: number
  ebitda_pct: number
  margem_liquida_pct: number
}

type ContaContabil = {
  id: number
  codigo: string
  nome: string
  tipo: string
  natureza: string
  ativa: boolean
}

type Lancamento = {
  id: number
  data: string
  mes_competencia: string
  conta_id: number
  conta_codigo: string
  conta_nome: string
  conta_tipo: string
  valor: number
  descricao: string | null
  fornecedor: string | null
  documento: string | null
  recorrente: boolean
}

type ConfigTributaria = {
  id?: number
  regime: string
  aliquota_simples: number
  aliquota_icms: number
  aliquota_pis: number
  aliquota_cofins: number
  aliquota_irpj: number
  aliquota_csll: number
  presuncao_lucro_pct: number
  vigencia_inicio: string
  vigencia_fim?: string | null
}

function mesHojeString(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function DREPage() {
  const [tab, setTab] = useState<'cascata' | 'despesas' | 'tributario'>('cascata')
  const [mes, setMes] = useState(mesHojeString())
  const [dre, setDre] = useState<DREMensal | null>(null)
  const [comparativo, setComparativo] = useState<DRECompPonto[]>([])
  const [loading, setLoading] = useState(false)
  // Feedback inline compartilhado entre as 3 abas — substitui alert() nativo.
  const [feedback, setFeedback] = useState<FeedbackMessage | null>(null)

  useEffect(() => {
    if (tab !== 'cascata') return
    const fetch = async () => {
      setLoading(true)
      try {
        const [a, b] = await Promise.all([
          axios.get(`${API_URL}/dre?mes=${mes}`),
          axios.get(`${API_URL}/dre/comparativo?ate=${mes}&meses=6`),
        ])
        setDre(a.data)
        setComparativo(b.data)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [tab, mes])

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <div className="flex items-baseline justify-between mb-6">
        <div>
          <h1 className="headline text-[40px] leading-none tracking-editorial">DRE</h1>
          <p className="text-sm text-[color:var(--claude-ink)]/60 mt-2">
            Demonstração do Resultado do Exercício. Receita → CMV → Despesas → Lucro Líquido.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[color:var(--claude-ink)]/10 mb-6">
        <DRETab active={tab === 'cascata'} onClick={() => { setTab('cascata'); setFeedback(null) }} icon={<PieChart size={16} />} label="Cascata" />
        <DRETab active={tab === 'despesas'} onClick={() => { setTab('despesas'); setFeedback(null) }} icon={<Receipt size={16} />} label="Lançamentos" />
        <DRETab active={tab === 'tributario'} onClick={() => { setTab('tributario'); setFeedback(null) }} icon={<Percent size={16} />} label="Tributário" />
      </div>

      <div className="mb-4">
        <FeedbackBanner feedback={feedback} onDismiss={() => setFeedback(null)} />
      </div>

      {tab === 'cascata' && (
        <DRECascataView
          dre={dre}
          comparativo={comparativo}
          loading={loading}
          mes={mes}
          onMesChange={setMes}
          onFechamento={async () => {
            try {
              await axios.post(`${API_URL}/dre/fechar?mes=${mes}`)
              setFeedback({ tone: 'ok', mensagem: `Mês ${mes} fechado.` })
            } catch (e) {
              setFeedback({
                tone: 'alert',
                mensagem: 'Falha ao fechar mês: ' + ((e as any).message || 'erro desconhecido'),
              })
            }
          }}
        />
      )}
      {tab === 'despesas' && <DREDespesasView mes={mes} onMesChange={setMes} onFeedback={setFeedback} />}
      {tab === 'tributario' && <DRETributarioView onFeedback={setFeedback} />}
    </div>
  )
}

function DRETab({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-3 text-sm font-medium transition-all border-b-2 -mb-px ${
        active
          ? 'border-[color:var(--claude-coral)] text-[color:var(--claude-ink)]'
          : 'border-transparent text-[color:var(--claude-ink)]/50 hover:text-[color:var(--claude-ink)]/80'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}

function DRECascataView({ dre, comparativo, loading, mes, onMesChange, onFechamento }: {
  dre: DREMensal | null
  comparativo: DRECompPonto[]
  loading: boolean
  mes: string
  onMesChange: (m: string) => void
  onFechamento: () => void
}) {
  if (loading || !dre) {
    return <EmptyState variant="loading" title="Calculando…" />
  }

  // Sparkline data (6 meses)
  const sparkReceita = comparativo.map(p => p.receita_bruta)
  const sparkLiquido = comparativo.map(p => p.lucro_liquido)
  const margemBrutaHist = comparativo.map(p => p.margem_bruta_pct * 100)
  const ebitdaPctHist = comparativo.map(p => p.ebitda_pct * 100)

  // Delta: mês atual vs média dos 5 anteriores
  const prevReceita = comparativo.slice(0, -1).map(p => p.receita_bruta)
  const mediaPrevReceita = prevReceita.length > 0 ? prevReceita.reduce((a, b) => a + b, 0) / prevReceita.length : 0
  const deltaReceitaPct = mediaPrevReceita > 0 ? ((dre.receita_bruta - mediaPrevReceita) / mediaPrevReceita) * 100 : 0

  const prevMargemBruta = comparativo.slice(0, -1).map(p => p.margem_bruta_pct * 100)
  const mediaPrevMB = prevMargemBruta.length > 0 ? prevMargemBruta.reduce((a, b) => a + b, 0) / prevMargemBruta.length : 0
  const deltaMB = (dre.margem_bruta_pct * 100) - mediaPrevMB

  const prevEbitda = comparativo.slice(0, -1).map(p => p.ebitda_pct * 100)
  const mediaPrevEb = prevEbitda.length > 0 ? prevEbitda.reduce((a, b) => a + b, 0) / prevEbitda.length : 0
  const deltaEb = (dre.ebitda_pct * 100) - mediaPrevEb

  return (
    <div className="space-y-6">
      {/* Controles */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <label className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50">Mês</label>
          <input
            type="month"
            value={mes}
            onChange={e => onMesChange(e.target.value)}
            className="px-3 py-2 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm"
          />
          {dre.regime && (
            <span className="text-xs px-2 py-1 rounded-full bg-[color:var(--claude-sage)]/15 text-[color:var(--claude-sage)] font-medium">
              {dre.regime.replace('_', ' ')}
            </span>
          )}
        </div>
        <button
          onClick={onFechamento}
          className="px-4 py-2 rounded-lg bg-[color:var(--claude-ink)] text-[color:var(--claude-cream)] text-sm font-medium hover:opacity-90"
        >
          Fechar mês
        </button>
      </div>

      {/* KPIs de resultado */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Receita Bruta"
          value={formatCurrency(dre.receita_bruta)}
          subValue={`${comparativo.length} meses no gráfico`}
          status="neutral"
          delta={deltaReceitaPct}
          deltaFormat="pct"
          deltaLabel={mediaPrevReceita > 0 ? `vs média (${formatCurrency(mediaPrevReceita)})` : '1º mês registrado'}
          sparklineData={sparkReceita}
          sparklineTone="sage"
        />
        <KPICard
          title="Margem Bruta"
          value={formatPercent(dre.margem_bruta_pct, { maximumFractionDigits: 2 })}
          subValue={formatCurrency(dre.lucro_bruto)}
          status={dre.margem_bruta_pct >= 0.2 ? 'up' : dre.margem_bruta_pct >= 0.15 ? 'ok' : 'warn'}
          delta={deltaMB}
          deltaFormat="pp"
          deltaLabel={mediaPrevMB > 0 ? `vs média (${formatPercent(mediaPrevMB, { scale: 1 })})` : '1º mês registrado'}
          sparklineData={margemBrutaHist}
          sparklineTone="coral"
        />
        <KPICard
          title="EBITDA"
          value={formatCurrency(dre.ebitda)}
          subValue={`${formatPercent(dre.ebitda_pct, { maximumFractionDigits: 2 })} da receita`}
          status={dre.ebitda_pct >= 0.1 ? 'up' : dre.ebitda_pct >= 0.05 ? 'ok' : dre.ebitda >= 0 ? 'warn' : 'alert'}
          delta={deltaEb}
          deltaFormat="pp"
          deltaLabel={mediaPrevEb !== 0 ? `vs média (${formatPercent(mediaPrevEb, { scale: 1 })})` : '1º mês registrado'}
          sparklineData={ebitdaPctHist}
          sparklineTone="amber"
        />
        <KPICard
          title="Lucro Líquido"
          value={formatCurrency(dre.lucro_liquido)}
          subValue={formatPercent(dre.margem_liquida_pct, { maximumFractionDigits: 2 })}
          status={dre.lucro_liquido > 0 ? 'up' : dre.lucro_liquido === 0 ? 'ok' : 'alert'}
          sparklineData={sparkLiquido}
          sparklineTone={dre.lucro_liquido >= 0 ? 'sage' : 'coral'}
        />
      </div>

      {/* Tabela cascata */}
      <div className="bg-white rounded-xl border border-[color:var(--claude-ink)]/8 overflow-hidden">
        <div className="px-6 py-4 border-b border-[color:var(--claude-ink)]/8">
          <h3 className="headline text-[20px] tracking-editorial">Cascata do resultado</h3>
          <p className="text-xs text-[color:var(--claude-ink)]/50 mt-1">Todos os valores em R$. % sobre receita bruta.</p>
        </div>
        <table className="w-full">
          <thead>
            <tr className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50 border-b border-[color:var(--claude-ink)]/5">
              <th className="text-left px-6 py-3 font-medium">Linha</th>
              <th className="text-right px-6 py-3 font-medium">Valor</th>
              <th className="text-right px-6 py-3 font-medium w-24">% Rec.</th>
            </tr>
          </thead>
          <tbody>
            {dre.linhas.map((linha, i) => (
              <DRELinhaRow key={i} linha={linha} />
            ))}
          </tbody>
        </table>
      </div>

      {/* Série 6 meses em barra */}
      {comparativo.length > 1 && (
        <div className="bg-white rounded-xl border border-[color:var(--claude-ink)]/8 p-6">
          <h3 className="headline text-[20px] tracking-editorial mb-4">Tendência 6 meses</h3>
          <div className="space-y-2">
            {comparativo.map((p, i) => {
              const maxRec = Math.max(...comparativo.map(x => x.receita_bruta), 1)
              const wRec = (p.receita_bruta / maxRec) * 100
              const wEbi = Math.max(0, (p.ebitda / maxRec)) * 100
              const isNeg = p.ebitda < 0
              // Mes sem nenhum dado real (receita, ebitda e LL todos zerados):
              // dessatura visualmente para nao competir com meses preenchidos.
              const isVazio = p.receita_bruta === 0 && p.ebitda === 0 && p.lucro_liquido === 0
              return (
                <div key={i} className={`flex items-center gap-4 text-xs ${isVazio ? 'opacity-40' : ''}`}>
                  <span className="w-16 font-mono text-[color:var(--claude-ink)]/60">{p.mes}</span>
                  <div className="flex-1 h-6 bg-[color:var(--claude-ink)]/5 rounded relative overflow-hidden">
                    <div className="h-full bg-[color:var(--claude-sage)]/30" style={{ width: `${wRec}%` }} />
                    {!isNeg && (
                      <div className="h-full bg-[color:var(--claude-sage)] absolute top-0 left-0" style={{ width: `${wEbi}%` }} />
                    )}
                    {isNeg && <div className="absolute top-0 left-0 h-full bg-[color:var(--claude-coral)]/40" style={{ width: `${wRec}%` }} />}
                  </div>
                  <span className="w-24 text-right font-mono">{isVazio ? '—' : formatCurrency(p.receita_bruta)}</span>
                  <span className={`w-20 text-right font-mono text-xs ${isVazio ? 'text-[color:var(--claude-ink)]/40' : (p.lucro_liquido >= 0 ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]')}`}>
                    {isVazio ? '—' : formatCurrency(p.lucro_liquido)}
                  </span>
                </div>
              )
            })}
          </div>
          <div className="flex gap-4 text-[10px] uppercase tracking-wider mt-4 text-[color:var(--claude-ink)]/50">
            <span className="flex items-center gap-1.5"><span className="w-3 h-2 rounded bg-[color:var(--claude-sage)]/30" />Receita</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-2 rounded bg-[color:var(--claude-sage)]" />EBITDA</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-2 rounded bg-[color:var(--claude-coral)]/40" />Prejuízo</span>
          </div>
        </div>
      )}
    </div>
  )
}

function DRELinhaRow({ linha }: { linha: DRELinha }) {
  const isSubtotal = linha.tipo === 'subtotal' || linha.tipo === 'resultado'
  const isResultado = linha.tipo === 'resultado'
  const positivo = linha.valor >= 0
  const indent = linha.nivel === 1 ? 'pl-10' : 'pl-6'

  return (
    <tr
      className={`border-b border-[color:var(--claude-ink)]/5 ${
        isResultado ? 'bg-[color:var(--claude-sage)]/5' : isSubtotal ? 'bg-[color:var(--claude-ink)]/[0.02]' : ''
      }`}
    >
      <td className={`${indent} pr-6 py-2 text-sm ${isSubtotal ? 'font-semibold' : 'text-[color:var(--claude-ink)]/85'}`}>
        <span className="font-mono text-xs text-[color:var(--claude-ink)]/40 mr-3">{linha.codigo}</span>
        {linha.label}
      </td>
      <td className={`px-6 py-2 text-sm text-right font-mono tabular-nums ${
        isResultado ? 'font-bold text-base' : isSubtotal ? 'font-semibold' : ''
      } ${positivo ? 'text-[color:var(--claude-ink)]' : 'text-[color:var(--claude-coral)]'}`}>
        {formatCurrency(linha.valor)}
      </td>
      <td className="px-6 py-2 text-sm text-right font-mono tabular-nums text-[color:var(--claude-ink)]/50">
        {formatPercent(linha.pct_receita, { scale: 1 })}
      </td>
    </tr>
  )
}

function DREDespesasView({
  mes,
  onMesChange,
  onFeedback,
}: {
  mes: string
  onMesChange: (m: string) => void
  onFeedback: (f: FeedbackMessage | null) => void
}) {
  const [lancamentos, setLancamentos] = useState<Lancamento[]>([])
  const [contas, setContas] = useState<ContaContabil[]>([])
  const [loading, setLoading] = useState(false)
  const [mostrarForm, setMostrarForm] = useState(false)
  const [form, setForm] = useState({
    data: `${mes}-01`,
    conta_id: 0,
    valor: 0,
    descricao: '',
    fornecedor: '',
    recorrente: false,
  })

  const fetchData = async () => {
    setLoading(true)
    try {
      const [a, b] = await Promise.all([
        axios.get(`${API_URL}/despesas?mes=${mes}`),
        axios.get(`${API_URL}/contas`),
      ])
      setLancamentos(a.data)
      setContas(b.data)
      if (form.conta_id === 0 && b.data.length > 0) {
        // default: primeira conta de despesa
        const despConta = b.data.find((c: ContaContabil) => c.tipo === 'DESP_ADMIN') || b.data[0]
        setForm(f => ({ ...f, conta_id: despConta.id }))
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [mes])

  const handleCriar = async () => {
    if (!form.conta_id || form.valor <= 0) {
      onFeedback({ tone: 'warn', mensagem: 'Preencha conta e valor antes de lançar.' })
      return
    }
    try {
      await axios.post(`${API_URL}/despesas`, {
        data: form.data,
        mes_competencia: `${mes}-01`,
        conta_id: form.conta_id,
        valor: form.valor,
        descricao: form.descricao || null,
        fornecedor: form.fornecedor || null,
        recorrente: form.recorrente,
      })
      setMostrarForm(false)
      setForm(f => ({ ...f, valor: 0, descricao: '', fornecedor: '' }))
      onFeedback({ tone: 'ok', mensagem: 'Lançamento registrado.' })
      fetchData()
    } catch (e) {
      onFeedback({
        tone: 'alert',
        mensagem: 'Falha ao salvar lançamento: ' + ((e as any).message || 'erro desconhecido'),
      })
    }
  }

  const [confirmExcluirId, setConfirmExcluirId] = useState<number | null>(null)
  const [excluindoLanc, setExcluindoLanc] = useState(false)

  const handleExcluir = (id: number) => {
    setConfirmExcluirId(id)
  }

  const executarExcluirLancamento = async () => {
    if (confirmExcluirId == null || excluindoLanc) return
    setExcluindoLanc(true)
    try {
      await axios.delete(`${API_URL}/despesas/${confirmExcluirId}`)
      setConfirmExcluirId(null)
      onFeedback({ tone: 'ok', mensagem: 'Lançamento excluído.' })
      fetchData()
    } catch (e: any) {
      onFeedback({
        tone: 'alert',
        mensagem: 'Falha ao excluir: ' + (e?.response?.data?.detail || e.message),
      })
    } finally {
      setExcluindoLanc(false)
    }
  }

  const totalPorTipo = lancamentos.reduce<Record<string, number>>((acc, l) => {
    acc[l.conta_tipo] = (acc[l.conta_tipo] || 0) + l.valor
    return acc
  }, {})

  const contasAgrupadas = contas.reduce<Record<string, ContaContabil[]>>((acc, c) => {
    if (c.tipo === 'RECEITA' || c.tipo === 'CMV') return acc // essas não lançam manualmente
    acc[c.tipo] = acc[c.tipo] || []
    acc[c.tipo].push(c)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <label className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50">Mês</label>
          <input
            type="month"
            value={mes}
            onChange={e => onMesChange(e.target.value)}
            className="px-3 py-2 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm"
          />
        </div>
        <button
          onClick={() => setMostrarForm(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[color:var(--claude-coral)] text-white text-sm font-medium hover:opacity-90"
        >
          <Plus size={16} />
          Novo lançamento
        </button>
      </div>

      {/* Resumo por tipo */}
      {Object.keys(totalPorTipo).length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {Object.entries(totalPorTipo).map(([tipo, total]) => (
            <div key={tipo} className="bg-white rounded-lg border border-[color:var(--claude-ink)]/8 p-4">
              <p className="text-[10px] uppercase tracking-wider text-[color:var(--claude-ink)]/50">{tipo.replace('_', ' ')}</p>
              <p className="text-lg font-semibold mt-1 font-mono tabular-nums">{formatCurrency(total)}</p>
            </div>
          ))}
        </div>
      )}

      {/* Form modal */}
      {mostrarForm && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4" onClick={() => setMostrarForm(false)}>
          <div className="bg-white rounded-xl p-6 max-w-md w-full" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="headline text-xl tracking-editorial">Novo lançamento</h3>
              <button onClick={() => setMostrarForm(false)} className="p-1 hover:bg-[color:var(--claude-ink)]/5 rounded"><X size={18} /></button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50 mb-1 block">Conta</label>
                <select
                  value={form.conta_id}
                  onChange={e => setForm(f => ({ ...f, conta_id: Number(e.target.value) }))}
                  className="w-full px-3 py-2 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm"
                >
                  {Object.entries(contasAgrupadas).map(([tipo, lista]) => (
                    <optgroup key={tipo} label={tipo.replace('_', ' ')}>
                      {lista.map(c => (
                        <option key={c.id} value={c.id}>{c.codigo} — {c.nome}</option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50 mb-1 block">Data</label>
                  <input type="date" value={form.data} onChange={e => setForm(f => ({ ...f, data: e.target.value }))}
                    className="w-full px-3 py-2 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm" />
                </div>
                <div>
                  <label className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50 mb-1 block">Valor</label>
                  <input type="number" step="0.01" value={form.valor || ''} onChange={e => setForm(f => ({ ...f, valor: Number(e.target.value) }))}
                    className="w-full px-3 py-2 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm font-mono" />
                </div>
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50 mb-1 block">Descrição</label>
                <input type="text" value={form.descricao} onChange={e => setForm(f => ({ ...f, descricao: e.target.value }))}
                  placeholder="Ex: Aluguel abril/26"
                  className="w-full px-3 py-2 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm" />
              </div>
              <div>
                <label className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50 mb-1 block">Fornecedor</label>
                <input type="text" value={form.fornecedor} onChange={e => setForm(f => ({ ...f, fornecedor: e.target.value }))}
                  placeholder="Opcional"
                  className="w-full px-3 py-2 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm" />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.recorrente} onChange={e => setForm(f => ({ ...f, recorrente: e.target.checked }))} />
                Recorrente (mensal fixo)
              </label>
              <div className="flex gap-2 justify-end pt-2">
                <button onClick={() => setMostrarForm(false)} className="px-4 py-2 rounded-lg text-sm hover:bg-[color:var(--claude-ink)]/5">Cancelar</button>
                <button onClick={handleCriar} className="px-4 py-2 rounded-lg bg-[color:var(--claude-ink)] text-[color:var(--claude-cream)] text-sm font-medium">Salvar</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Lista */}
      <div className="bg-white rounded-xl border border-[color:var(--claude-ink)]/8 overflow-hidden">
        {loading ? (
          <EmptyState variant="loading" title="Carregando…" />
        ) : lancamentos.length === 0 ? (
          <EmptyState variant="empty" title={`Nenhum lançamento em ${mes}. Clique em "Novo lançamento" pra começar.`} />
        ) : (
          <table className="w-full">
            <thead>
              <tr className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50 border-b border-[color:var(--claude-ink)]/5">
                <th className="text-left px-6 py-3 font-medium">Data</th>
                <th className="text-left px-6 py-3 font-medium">Conta</th>
                <th className="text-left px-6 py-3 font-medium">Descrição</th>
                <th className="text-right px-6 py-3 font-medium">Valor</th>
                <th className="text-center px-6 py-3 font-medium w-12"></th>
              </tr>
            </thead>
            <tbody>
              {lancamentos.map(l => (
                <tr key={l.id} className="border-b border-[color:var(--claude-ink)]/5 hover:bg-[color:var(--claude-ink)]/[0.02]">
                  <td className="px-6 py-3 text-sm font-mono text-[color:var(--claude-ink)]/70">{l.data}</td>
                  <td className="px-6 py-3 text-sm">
                    <span className="font-mono text-xs text-[color:var(--claude-ink)]/40 mr-2">{l.conta_codigo}</span>
                    {l.conta_nome}
                  </td>
                  <td className="px-6 py-3 text-sm text-[color:var(--claude-ink)]/70">{l.descricao || '—'}</td>
                  <td className="px-6 py-3 text-sm text-right font-mono tabular-nums">{formatCurrency(l.valor)}</td>
                  <td className="px-6 py-3 text-center">
                    <button onClick={() => handleExcluir(l.id)} className="p-1 hover:bg-[color:var(--claude-coral)]/10 rounded text-[color:var(--claude-ink)]/40 hover:text-[color:var(--claude-coral)]">
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Confirmar exclusão de lançamento (substitui window.confirm) */}
      <Confirm
        open={confirmExcluirId !== null}
        title="Excluir lançamento?"
        body={<p>Esta operação remove o lançamento financeiro permanentemente. Os totais do DRE do mês serão recalculados.</p>}
        confirmLabel="Excluir"
        danger
        loading={excluindoLanc}
        onConfirm={executarExcluirLancamento}
        onCancel={() => setConfirmExcluirId(null)}
      />
    </div>
  )
}

function DRETributarioView({ onFeedback }: { onFeedback: (f: FeedbackMessage | null) => void }) {
  const [config, setConfig] = useState<ConfigTributaria | null>(null)
  const [editando, setEditando] = useState(false)
  const [form, setForm] = useState<ConfigTributaria | null>(null)

  useEffect(() => {
    axios.get(`${API_URL}/tributario`).then(r => setConfig(r.data)).catch(console.error)
  }, [])

  const handleEditar = () => {
    if (config) {
      setForm({ ...config })
      setEditando(true)
    }
  }

  const handleSalvar = async () => {
    if (!form) return
    try {
      await axios.put(`${API_URL}/tributario`, {
        regime: form.regime,
        aliquota_simples: form.aliquota_simples,
        aliquota_icms: form.aliquota_icms,
        aliquota_pis: form.aliquota_pis,
        aliquota_cofins: form.aliquota_cofins,
        aliquota_irpj: form.aliquota_irpj,
        aliquota_csll: form.aliquota_csll,
        presuncao_lucro_pct: form.presuncao_lucro_pct,
        vigencia_inicio: form.vigencia_inicio,
      })
      const r = await axios.get(`${API_URL}/tributario`)
      setConfig(r.data)
      setEditando(false)
      onFeedback({ tone: 'ok', mensagem: 'Configuração tributária atualizada.' })
    } catch (e) {
      onFeedback({
        tone: 'alert',
        mensagem: 'Falha ao salvar configuração: ' + ((e as any).message || 'erro desconhecido'),
      })
    }
  }

  if (!config) return <EmptyState variant="loading" title="Carregando…" />

  const display = editando && form ? form : config
  const isSimples = display.regime === 'SIMPLES_NACIONAL'

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="bg-white rounded-xl border border-[color:var(--claude-ink)]/8 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="headline text-xl tracking-editorial">Regime tributário</h3>
          {!editando && (
            <button onClick={handleEditar} className="text-sm px-3 py-1.5 rounded-lg border border-[color:var(--claude-ink)]/15 hover:bg-[color:var(--claude-ink)]/5">
              Editar
            </button>
          )}
        </div>

        <div className="space-y-4">
          <div>
            <label className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50 mb-1 block">Regime</label>
            {editando && form ? (
              <select
                value={form.regime}
                onChange={e => setForm({ ...form, regime: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm"
              >
                <option value="SIMPLES_NACIONAL">Simples Nacional</option>
                <option value="LUCRO_PRESUMIDO">Lucro Presumido</option>
                <option value="LUCRO_REAL">Lucro Real</option>
              </select>
            ) : (
              <p className="text-base font-medium">{display.regime.replace('_', ' ')}</p>
            )}
          </div>

          {isSimples ? (
            <AliquotaRow label="Alíquota Simples" valor={display.aliquota_simples} editando={editando} onChange={v => form && setForm({ ...form, aliquota_simples: v })} />
          ) : (
            <>
              <AliquotaRow label="ICMS" valor={display.aliquota_icms} editando={editando} onChange={v => form && setForm({ ...form, aliquota_icms: v })} />
              <AliquotaRow label="PIS" valor={display.aliquota_pis} editando={editando} onChange={v => form && setForm({ ...form, aliquota_pis: v })} />
              <AliquotaRow label="COFINS" valor={display.aliquota_cofins} editando={editando} onChange={v => form && setForm({ ...form, aliquota_cofins: v })} />
              <AliquotaRow label="IRPJ" valor={display.aliquota_irpj} editando={editando} onChange={v => form && setForm({ ...form, aliquota_irpj: v })} />
              <AliquotaRow label="CSLL" valor={display.aliquota_csll} editando={editando} onChange={v => form && setForm({ ...form, aliquota_csll: v })} />
              {display.regime === 'LUCRO_PRESUMIDO' && (
                <AliquotaRow label="Presunção Lucro" valor={display.presuncao_lucro_pct} editando={editando} onChange={v => form && setForm({ ...form, presuncao_lucro_pct: v })} />
              )}
            </>
          )}

          <div>
            <label className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50 mb-1 block">Vigência início</label>
            {editando && form ? (
              <input type="date" value={form.vigencia_inicio} onChange={e => setForm({ ...form, vigencia_inicio: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm" />
            ) : (
              <p className="text-sm font-mono">{display.vigencia_inicio}</p>
            )}
          </div>

          {editando && (
            <div className="flex gap-2 justify-end pt-2">
              <button onClick={() => setEditando(false)} className="px-4 py-2 rounded-lg text-sm hover:bg-[color:var(--claude-ink)]/5">Cancelar</button>
              <button onClick={handleSalvar} className="px-4 py-2 rounded-lg bg-[color:var(--claude-ink)] text-[color:var(--claude-cream)] text-sm font-medium">Salvar nova vigência</button>
            </div>
          )}
        </div>
      </div>

      <p className="text-xs text-[color:var(--claude-ink)]/50 leading-relaxed">
        <strong>Nota:</strong> alíquotas em decimal (ex: 0.08 = 8%). Simples Nacional consolida todos os impostos em uma alíquota única sobre a receita bruta. Presumido/Real separa ICMS+PIS+COFINS (sobre receita) de IRPJ+CSLL (sobre lucro presumido ou real).
      </p>
    </div>
  )
}

function AliquotaRow({ label, valor, editando, onChange }: { label: string; valor: number; editando: boolean; onChange: (v: number) => void }) {
  return (
    <div className="grid grid-cols-3 items-center gap-3">
      <label className="text-sm text-[color:var(--claude-ink)]/70">{label}</label>
      {editando ? (
        <input
          type="number"
          step="0.001"
          value={valor}
          onChange={e => onChange(Number(e.target.value))}
          className="col-span-2 px-3 py-2 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm font-mono"
        />
      ) : (
        <p className="col-span-2 text-sm font-mono tabular-nums">{formatPercent(valor, { maximumFractionDigits: 2 })} <span className="text-[color:var(--claude-ink)]/40">({formatNumber(valor, { minimumFractionDigits: 4, maximumFractionDigits: 4 })})</span></p>
      )}
    </div>
  )
}

// ============================================================================
// Balanço Patrimonial (BP)
// ============================================================================

type BPStatus = 'rascunho' | 'fechado' | 'auditado'

type BP = {
  id: number
  empresa_id: number | null
  competencia: string
  data_referencia: string
  status: BPStatus
  moeda: string
  observacoes: string | null

  // Ativo Circulante
  caixa_e_equivalentes: number
  bancos_conta_movimento: number
  aplicacoes_financeiras_curto_prazo: number
  clientes_contas_a_receber: number
  adiantamentos_a_fornecedores: number
  impostos_a_recuperar: number
  estoque: number
  despesas_antecipadas: number
  outros_ativos_circulantes: number
  total_ativo_circulante: number

  // Realizável LP
  clientes_longo_prazo: number
  depositos_judiciais: number
  impostos_a_recuperar_longo_prazo: number
  emprestimos_concedidos: number
  outros_realizaveis_longo_prazo: number
  total_realizavel_longo_prazo: number

  // Investimentos
  participacoes_societarias: number
  propriedades_para_investimento: number
  outros_investimentos: number
  total_investimentos: number

  // Imobilizado
  maquinas_e_equipamentos: number
  veiculos: number
  moveis_e_utensilios: number
  imoveis: number
  computadores_e_perifericos: number
  benfeitorias: number
  depreciacao_acumulada: number
  total_imobilizado: number

  // Intangível
  marcas_e_patentes: number
  softwares: number
  licencas: number
  goodwill: number
  amortizacao_acumulada: number
  total_intangivel: number

  total_ativo_nao_circulante: number
  total_ativo: number

  // Passivo Circulante
  fornecedores: number
  salarios_a_pagar: number
  encargos_sociais_a_pagar: number
  impostos_e_taxas_a_recolher: number
  emprestimos_financiamentos_curto_prazo: number
  parcelamentos_curto_prazo: number
  adiantamentos_de_clientes: number
  dividendos_a_pagar: number
  provisoes_curto_prazo: number
  outras_obrigacoes_circulantes: number
  total_passivo_circulante: number

  // Passivo Não Circulante
  emprestimos_financiamentos_longo_prazo: number
  debentures: number
  parcelamentos_longo_prazo: number
  provisoes_longo_prazo: number
  contingencias: number
  outras_obrigacoes_longo_prazo: number
  total_passivo_nao_circulante: number

  total_passivo: number

  // PL
  capital_social: number
  reservas_de_capital: number
  ajustes_de_avaliacao_patrimonial: number
  reservas_de_lucros: number
  lucros_acumulados: number
  prejuizos_acumulados: number
  acoes_ou_quotas_em_tesouraria: number
  total_patrimonio_liquido: number

  indicador_fechamento_ok: boolean
  diferenca_balanceamento: number

  criado_em?: string | null
  atualizado_em?: string | null
  fechado_em?: string | null
  auditado_em?: string | null
}

type BPIndicadores = {
  competencia: string
  liquidez_corrente: number
  liquidez_seca: number
  liquidez_imediata: number
  endividamento_geral: number
  composicao_endividamento: number
  imobilizacao_pl: number
  capital_giro_liquido: number
  equacao_fundamental_ok: boolean
}

type BPCompPonto = {
  competencia: string
  status: string
  total_ativo: number
  total_passivo: number
  total_patrimonio_liquido: number
  liquidez_corrente: number
  endividamento_geral: number
}

type BPListItem = {
  id: number
  competencia: string
  data_referencia: string
  status: BPStatus
  total_ativo: number
  total_passivo: number
  total_patrimonio_liquido: number
  indicador_fechamento_ok: boolean
  atualizado_em?: string | null
}

type BPTab = 'resumo' | 'ativo' | 'passivo' | 'pl' | 'indicadores' | 'historico'

// ============================================================================
// DFC — Demonstração dos Fluxos de Caixa (v0.13)
// ============================================================================

type DFCLinha = {
  codigo: string
  label: string
  valor: number
  tipo: string   // cabecalho | detalhe | subtotal | resultado
  nivel: number
}

type DFCMensal = {
  mes: string
  disponivel: boolean
  motivo_indisponivel?: string | null
  caixa_inicial: number
  caixa_final: number
  total_operacional: number
  total_investimento: number
  total_financiamento: number
  variacao_caixa_calculada: number
  variacao_caixa_real: number
  diferenca_reconciliacao: number
  reconciliacao_ok: boolean
  linhas: DFCLinha[]
}

type DFCComp = {
  mes: string
  disponivel: boolean
  total_operacional: number
  total_investimento: number
  total_financiamento: number
  variacao_caixa_real: number
  caixa_final: number
}

function DFCPage() {
  const [mes, setMes] = useState(mesHojeString())
  const [dfc, setDfc] = useState<DFCMensal | null>(null)
  const [comp, setComp] = useState<DFCComp[]>([])
  const [loading, setLoading] = useState(false)

  const fetchDFC = async () => {
    setLoading(true)
    try {
      const [a, b] = await Promise.all([
        axios.get(`${API_URL}/dfc?mes=${mes}`),
        axios.get(`${API_URL}/dfc/comparativo?ate=${mes}&meses=6`),
      ])
      setDfc(a.data)
      setComp(b.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { fetchDFC() }, [mes])

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-end">
        <div>
          <p className="section-label mb-1">Demonstração dos Fluxos de Caixa</p>
          <h2 className="headline text-4xl tracking-editorial">DFC — Método Indireto</h2>
          <p className="text-[color:var(--claude-stone)] mt-1 text-sm">
            Reconcilia o Lucro Líquido com a variação de caixa real entre dois Balanços Patrimoniais consecutivos.
          </p>
        </div>
        <input
          type="month"
          value={mes}
          onChange={(e) => setMes(e.target.value)}
          className="px-3 py-2 text-sm border border-[color:var(--border)] rounded-lg bg-white"
        />
      </header>

      {loading && <EmptyState variant="loading" className="claude-card" title="Carregando…" />}

      {!loading && dfc && !dfc.disponivel && (
        <div className="claude-card p-6" style={{ borderLeft: '4px solid var(--claude-amber)' }}>
          <p className="section-label">DFC indisponível</p>
          <p className="text-sm mt-2">{dfc.motivo_indisponivel}</p>
          <p className="text-xs text-[color:var(--claude-stone)] mt-3">
            Vá em <strong>Balanço Patrimonial</strong> e cadastre o BP do mês (e do mês anterior).
          </p>
        </div>
      )}

      {!loading && dfc && dfc.disponivel && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="claude-card p-4">
              <p className="section-label">Caixa inicial</p>
              <p className="kpi-value text-xl mt-1 mono">{formatCurrency(dfc.caixa_inicial)}</p>
            </div>
            <div className="claude-card p-4">
              <p className="section-label">Caixa final</p>
              <p className="kpi-value text-xl mt-1 mono text-[color:var(--claude-sage)]">{formatCurrency(dfc.caixa_final)}</p>
            </div>
            <div className="claude-card p-4">
              <p className="section-label">Variação líquida</p>
              <p className={`kpi-value text-xl mt-1 mono ${dfc.variacao_caixa_real >= 0 ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]'}`}>
                {formatCurrency(dfc.variacao_caixa_real, { signed: true })}
              </p>
            </div>
            <div className="claude-card p-4">
              <p className="section-label">Reconciliação</p>
              <p className={`kpi-value text-xl mt-1 ${dfc.reconciliacao_ok ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-amber)]'}`}>
                {dfc.reconciliacao_ok ? 'OK' : `Δ ${formatCurrency(dfc.diferenca_reconciliacao)}`}
              </p>
              <p className="text-[10px] text-[color:var(--claude-stone)] mt-1">|calc − real| &lt; 0,01</p>
            </div>
          </div>

          {/* Tabela cascata */}
          <div className="claude-card overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="bg-[color:var(--claude-cream-deep)]/40 border-b border-[color:var(--border)]">
                  <th className="px-4 py-3 section-label">Cód.</th>
                  <th className="px-4 py-3 section-label">Descrição</th>
                  <th className="px-4 py-3 section-label text-right">Valor (R$)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[color:var(--border)]">
                {dfc.linhas.map(l => {
                  const isCab = l.tipo === 'cabecalho'
                  const isSub = l.tipo === 'subtotal'
                  const isRes = l.tipo === 'resultado'
                  const negativo = l.valor < 0
                  return (
                    <tr key={l.codigo}
                        className={isCab ? 'bg-[color:var(--claude-cream-deep)]/60' : isSub ? 'bg-[color:var(--claude-cream-deep)]/20 font-semibold' : isRes ? 'bg-[color:var(--claude-sage)]/10 font-bold' : ''}>
                      <td className="px-4 py-2 mono text-xs text-[color:var(--claude-stone)]">{l.codigo}</td>
                      <td className={`px-4 py-2 ${isCab ? 'font-bold uppercase tracking-wide text-xs' : ''}`}
                          style={{ paddingLeft: `${16 + l.nivel * 12}px` }}>
                        {l.label}
                      </td>
                      <td className={`px-4 py-2 text-right mono ${negativo ? 'text-[color:var(--claude-coral)]' : isRes ? 'text-[color:var(--claude-sage)]' : ''}`}>
                        {isCab && l.valor === 0 ? '' : (
                          formatCurrency(l.valor, { negativeSign: '−' })
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Comparativo 6 meses */}
          {comp.length > 0 && (
            <div className="claude-card p-6">
              <p className="section-label mb-3">Histórico — últimos 6 meses</p>
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="text-[color:var(--claude-stone)]">
                    <th className="py-2">Mês</th>
                    <th className="py-2 text-right">Operacional</th>
                    <th className="py-2 text-right">Investimento</th>
                    <th className="py-2 text-right">Financiamento</th>
                    <th className="py-2 text-right">Δ Caixa</th>
                    <th className="py-2 text-right">Caixa final</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[color:var(--border)]">
                  {comp.map(c => (
                    <tr key={c.mes} className={!c.disponivel ? 'opacity-40' : ''}>
                      <td className="py-2 mono">{c.mes}</td>
                      {c.disponivel ? (
                        <>
                          <td className={`py-2 text-right mono ${c.total_operacional >= 0 ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]'}`}>{formatNumber(c.total_operacional, { maximumFractionDigits: 0 })}</td>
                          <td className={`py-2 text-right mono ${c.total_investimento >= 0 ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]'}`}>{formatNumber(c.total_investimento, { maximumFractionDigits: 0 })}</td>
                          <td className={`py-2 text-right mono ${c.total_financiamento >= 0 ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]'}`}>{formatNumber(c.total_financiamento, { maximumFractionDigits: 0 })}</td>
                          <td className="py-2 text-right mono font-semibold">{formatNumber(c.variacao_caixa_real, { maximumFractionDigits: 0, signed: true })}</td>
                          <td className="py-2 text-right mono">{formatNumber(c.caixa_final, { maximumFractionDigits: 0 })}</td>
                        </>
                      ) : (
                        <td colSpan={5} className="py-2 text-xs italic text-[color:var(--claude-stone)]">sem BP no mês</td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ============================================================================
// DMPL — Demonstração das Mutações do PL (v0.13)
// ============================================================================

type DMPLLinha = {
  componente: string
  saldo_inicial: number
  lucro_liquido: number
  outras_mov: number
  saldo_final: number
  redutora: boolean
}

type DMPLAviso = { codigo: string; severidade: string; mensagem: string }

type DMPLMensal = {
  mes: string
  disponivel: boolean
  motivo_indisponivel?: string | null
  componentes: DMPLLinha[]
  total: DMPLLinha
  fechamento_ok: boolean
  avisos?: DMPLAviso[]
}

function DMPLPage() {
  const [mes, setMes] = useState(mesHojeString())
  const [dmpl, setDmpl] = useState<DMPLMensal | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchDMPL = async () => {
    setLoading(true)
    try {
      const r = await axios.get(`${API_URL}/dmpl?mes=${mes}`)
      setDmpl(r.data)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { fetchDMPL() }, [mes])

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-end">
        <div>
          <p className="section-label mb-1">Mutações do Patrimônio Líquido</p>
          <h2 className="headline text-4xl tracking-editorial">DMPL</h2>
          <p className="text-[color:var(--claude-stone)] mt-1 text-sm">
            Como cada componente do PL mudou no mês: saldo inicial → lucro líquido → outras movimentações → saldo final.
          </p>
        </div>
        <input
          type="month"
          value={mes}
          onChange={(e) => setMes(e.target.value)}
          className="px-3 py-2 text-sm border border-[color:var(--border)] rounded-lg bg-white"
        />
      </header>

      {loading && <EmptyState variant="loading" className="claude-card" title="Carregando…" />}

      {!loading && dmpl && !dmpl.disponivel && (
        <div className="claude-card p-6" style={{ borderLeft: '4px solid var(--claude-amber)' }}>
          <p className="section-label">DMPL indisponível</p>
          <p className="text-sm mt-2">{dmpl.motivo_indisponivel}</p>
        </div>
      )}

      {!loading && dmpl && dmpl.disponivel && (() => {
        const avisos = dmpl.avisos || []
        const bpStale = avisos.some(a => a.codigo === 'bp_pl_nao_inicializado' || a.codigo === 'll_nao_propagado')

        const renderOutras = (v: number, isLucrosAcumulados: boolean) => {
          if (bpStale && isLucrosAcumulados && Math.abs(v) > 0.01) {
            return <span className="italic text-[color:var(--claude-stone)] text-xs">BP nao atualizado</span>
          }
          return v === 0 ? '—' : formatCurrency(v, { negativeSign: '−' })
        }

        return (
        <>
          {/* Status fechamento */}
          <div className="claude-card p-4 flex items-center justify-between"
               style={{ borderLeft: `4px solid ${dmpl.fechamento_ok && !bpStale ? 'var(--claude-sage)' : bpStale ? 'var(--claude-stone)' : 'var(--claude-coral)'}` }}>
            <div>
              <p className="section-label">Fechamento</p>
              <p className="text-sm mt-1">
                {bpStale && Math.abs(dmpl.total.saldo_final) < 0.01
                  ? <>Sem PL cadastrado - saldos zerados.</>
                  : dmpl.fechamento_ok
                  ? <>Total bate com o PL do BP. <strong>{formatCurrency(dmpl.total.saldo_final)}</strong></>
                  : <>Total NÃO bate com o PL do BP — verifique o Balanço.</>
                }
              </p>
            </div>
            <span className={`px-3 py-1 rounded-full text-[11px] uppercase tracking-wider font-bold ${
              bpStale ? 'bg-[color:var(--claude-stone)]/20 text-[color:var(--claude-stone)]'
              : dmpl.fechamento_ok ? 'bg-[color:var(--claude-sage)]/20 text-[color:var(--claude-sage)]'
              : 'bg-[color:var(--claude-coral)]/20 text-[color:var(--claude-coral)]'}`}>
              {bpStale ? 'BP VAZIO' : dmpl.fechamento_ok ? 'OK' : 'ATENÇÃO'}
            </span>
          </div>

          {avisos.length > 0 && (
            <div className="claude-card p-4" style={{ borderLeft: '4px solid var(--claude-amber)' }}>
              <p className="section-label">Avisos</p>
              <ul className="mt-2 space-y-2 text-sm text-[color:var(--claude-ink)]">
                {avisos.map((a, i) => (
                  <li key={i} className="flex gap-2 items-start">
                    <span className="inline-block px-1.5 py-0.5 rounded bg-[color:var(--claude-amber)]/15 text-[color:var(--claude-amber)] text-[10px] font-mono uppercase tracking-wider mt-0.5 shrink-0">{a.codigo}</span>
                    <span>{a.mensagem}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Matriz */}
          <div className="claude-card overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="bg-[color:var(--claude-cream-deep)]/40 border-b border-[color:var(--border)]">
                  <th className="px-4 py-3 section-label">Componente</th>
                  <th className="px-4 py-3 section-label text-right">Saldo Inicial</th>
                  <th className="px-4 py-3 section-label text-right">+ Lucro Líquido</th>
                  <th className="px-4 py-3 section-label text-right">+ Outras Movim.</th>
                  <th className="px-4 py-3 section-label text-right">= Saldo Final</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[color:var(--border)]">
                {dmpl.componentes.map(c => {
                  const isLA = c.componente === 'Lucros Acumulados'
                  return (
                    <tr key={c.componente} className={isLA ? 'bg-[color:var(--claude-cream-deep)]/30' : ''}>
                      <td className={`px-4 py-2 ${isLA ? 'font-semibold text-[color:var(--claude-ink)]' : (c.redutora ? 'text-[color:var(--claude-stone)] italic' : '')}`}>{c.componente}</td>
                      <td className="px-4 py-2 text-right mono">{formatCurrency(c.saldo_inicial, { negativeSign: '−' })}</td>
                      <td className={`px-4 py-2 text-right mono ${c.lucro_liquido !== 0 ? (c.lucro_liquido > 0 ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]') : 'text-[color:var(--claude-stone)]/50'}`}>{c.lucro_liquido === 0 ? '—' : formatCurrency(c.lucro_liquido, { negativeSign: '−' })}</td>
                      <td className={`px-4 py-2 text-right mono ${(bpStale && isLA) ? '' : (c.outras_mov !== 0 ? (c.outras_mov > 0 ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]') : 'text-[color:var(--claude-stone)]/50')}`}>{renderOutras(c.outras_mov, isLA)}</td>
                      <td className={`px-4 py-2 text-right mono ${isLA ? 'font-bold' : 'font-semibold'}`}>{formatCurrency(c.saldo_final, { negativeSign: '−' })}</td>
                    </tr>
                  )
                })}
                <tr className="bg-[color:var(--claude-cream-deep)]/60 font-bold">
                  <td className="px-4 py-3">{dmpl.total.componente}</td>
                  <td className="px-4 py-3 text-right mono">{formatCurrency(dmpl.total.saldo_inicial, { negativeSign: '−' })}</td>
                  <td className="px-4 py-3 text-right mono">{formatCurrency(dmpl.total.lucro_liquido, { negativeSign: '−' })}</td>
                  <td className="px-4 py-3 text-right mono">{bpStale && Math.abs(dmpl.total.outras_mov) > 0.01 ? <span className="italic text-[color:var(--claude-stone)] text-xs">BP nao atualizado</span> : (dmpl.total.outras_mov === 0 ? '—' : formatCurrency(dmpl.total.outras_mov, { negativeSign: '−' }))}</td>
                  <td className="px-4 py-3 text-right mono text-[color:var(--claude-sage)]">{formatCurrency(dmpl.total.saldo_final, { negativeSign: '−' })}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p className="text-xs text-[color:var(--claude-stone)] italic">
            Lucro liquido vai automatico para "Lucros Acumulados". "Outras Movimentacoes" captura o resto (aumentos de capital, dividendos, transferencias para reservas, acoes em tesouraria); quando o BP do mes nao esta inicializado, esse campo e apenas residual matematico e fica rotulado como "BP nao atualizado".
          </p>
        </>
        )
      })()}
    </div>
  )
}

function BPPage() {
  const [tab, setTab] = useState<BPTab>('resumo')
  const [mes, setMes] = useState(mesHojeString())
  const [bp, setBp] = useState<BP | null>(null)
  const [comparativo, setComparativo] = useState<BPCompPonto[]>([])
  const [indicadores, setIndicadores] = useState<BPIndicadores | null>(null)
  const [loading, setLoading] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [dirty, setDirty] = useState(false)
  // Feedback inline — substitui alert() em salvar/fechar/auditar/reabrir.
  const [feedback, setFeedback] = useState<FeedbackMessage | null>(null)
  // Confirms internos (substituem window.confirm em auditar e reabrir).
  const [confirmAuditar, setConfirmAuditar] = useState(false)
  const [confirmReabrir, setConfirmReabrir] = useState(false)
  const [auditando, setAuditando] = useState(false)
  const [reabrindo, setReabrindo] = useState(false)

  const fetchBP = async () => {
    setLoading(true)
    try {
      const [a, b] = await Promise.all([
        axios.get(`${API_URL}/bp?mes=${mes}`),
        axios.get(`${API_URL}/bp/comparativo?ate=${mes}&meses=12`),
      ])
      setBp(a.data)
      setComparativo(b.data)
      // Indicadores só se existir BP
      try {
        const ind = await axios.get(`${API_URL}/bp/indicadores?mes=${mes}`)
        setIndicadores(ind.data)
      } catch {
        setIndicadores(null)
      }
      setDirty(false)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchBP() }, [mes])

  const editavel = bp?.status === 'rascunho'

  const atualizarCampo = (campo: keyof BP, valor: number) => {
    if (!bp || !editavel) return
    setBp({ ...bp, [campo]: valor })
    setDirty(true)
  }

  const salvarRascunho = async () => {
    if (!bp) return
    setSalvando(true)
    try {
      const payload: any = {
        empresa_id: bp.empresa_id,
        competencia: `${mes}-01`,
        data_referencia: bp.data_referencia,
        moeda: bp.moeda,
        observacoes: bp.observacoes,
      }
      const camposNumericos: (keyof BP)[] = [
        'caixa_e_equivalentes','bancos_conta_movimento','aplicacoes_financeiras_curto_prazo',
        'clientes_contas_a_receber','adiantamentos_a_fornecedores','impostos_a_recuperar',
        'estoque','despesas_antecipadas','outros_ativos_circulantes',
        'clientes_longo_prazo','depositos_judiciais','impostos_a_recuperar_longo_prazo',
        'emprestimos_concedidos','outros_realizaveis_longo_prazo',
        'participacoes_societarias','propriedades_para_investimento','outros_investimentos',
        'maquinas_e_equipamentos','veiculos','moveis_e_utensilios','imoveis',
        'computadores_e_perifericos','benfeitorias','depreciacao_acumulada',
        'marcas_e_patentes','softwares','licencas','goodwill','amortizacao_acumulada',
        'fornecedores','salarios_a_pagar','encargos_sociais_a_pagar',
        'impostos_e_taxas_a_recolher','emprestimos_financiamentos_curto_prazo',
        'parcelamentos_curto_prazo','adiantamentos_de_clientes','dividendos_a_pagar',
        'provisoes_curto_prazo','outras_obrigacoes_circulantes',
        'emprestimos_financiamentos_longo_prazo','debentures','parcelamentos_longo_prazo',
        'provisoes_longo_prazo','contingencias','outras_obrigacoes_longo_prazo',
        'capital_social','reservas_de_capital','ajustes_de_avaliacao_patrimonial',
        'reservas_de_lucros','lucros_acumulados','prejuizos_acumulados',
        'acoes_ou_quotas_em_tesouraria',
      ]
      camposNumericos.forEach(c => { payload[c] = Number(bp[c] ?? 0) })
      const res = await axios.post(`${API_URL}/bp`, payload)
      setBp(res.data)
      setDirty(false)
      setFeedback({ tone: 'ok', mensagem: 'Rascunho salvo.' })
    } catch (e: any) {
      setFeedback({
        tone: 'alert',
        mensagem: 'Falha ao salvar: ' + (e.response?.data?.detail || e.message),
      })
    } finally {
      setSalvando(false)
    }
  }

  const [confirmFecharSalvar, setConfirmFecharSalvar] = useState(false)
  const [fechandoBP, setFechandoBP] = useState(false)

  const executarFechamento = async () => {
    setFechandoBP(true)
    try {
      const res = await axios.post(`${API_URL}/bp/fechar?mes=${mes}`)
      setBp(res.data)
      setFeedback({ tone: 'ok', mensagem: 'BP fechado com sucesso.' })
      fetchBP()
    } catch (e: any) {
      const d = e.response?.data?.detail
      if (d && typeof d === 'object' && d.diferenca !== undefined) {
        setFeedback({
          tone: 'alert',
          mensagem: `BP não balanceia. Ativo ${formatCurrency(d.total_ativo)} · Passivo + PL ${formatCurrency(d.total_passivo + d.total_patrimonio_liquido)} · Diferença ${formatCurrency(d.diferenca)}.`,
        })
      } else {
        setFeedback({
          tone: 'alert',
          mensagem: 'Falha ao fechar: ' + (d || e.message),
        })
      }
    } finally {
      setFechandoBP(false)
    }
  }

  const fecharBP = async () => {
    if (dirty) {
      // dispara modal: usuário decide se salva antes ou cancela
      setConfirmFecharSalvar(true)
      return
    }
    await executarFechamento()
  }

  const confirmarSalvarEFechar = async () => {
    setConfirmFecharSalvar(false)
    await salvarRascunho()
    await executarFechamento()
  }

  // auditarBP / reabrirBP migrados pra <Confirm> (renderizado mais abaixo).
  // O confirm() nativo bloqueia thread, ignora style do app e nao da feedback
  // estruturado de erro.
  const auditarBP = () => setConfirmAuditar(true)
  const reabrirBP = () => setConfirmReabrir(true)

  const executarAuditar = async () => {
    setAuditando(true)
    try {
      const res = await axios.post(`${API_URL}/bp/auditar?mes=${mes}`)
      setBp(res.data)
      setConfirmAuditar(false)
      setFeedback({ tone: 'ok', mensagem: 'BP auditado.' })
    } catch (e: any) {
      setFeedback({
        tone: 'alert',
        mensagem: 'Falha ao auditar: ' + (e.response?.data?.detail || e.message),
      })
    } finally {
      setAuditando(false)
    }
  }

  const executarReabrir = async () => {
    setReabrindo(true)
    try {
      const res = await axios.post(`${API_URL}/bp/reabrir?mes=${mes}`)
      setBp(res.data)
      setConfirmReabrir(false)
      setFeedback({ tone: 'ok', mensagem: 'BP reaberto para rascunho.' })
      fetchBP()
    } catch (e: any) {
      setFeedback({
        tone: 'alert',
        mensagem: 'Falha ao reabrir: ' + (e.response?.data?.detail || e.message),
      })
    } finally {
      setReabrindo(false)
    }
  }

  return (
    <div className="p-8 max-w-[1400px] mx-auto">
      <div className="flex items-baseline justify-between mb-6">
        <div>
          <h1 className="headline text-[40px] leading-none tracking-editorial">Balanço Patrimonial</h1>
          <p className="text-sm text-[color:var(--claude-ink)]/60 mt-2">
            Posição patrimonial em uma data. Estrutura Lei 6.404/76 + CPC 26. Ativo = Passivo + PL.
          </p>
        </div>
      </div>

      <div className="mb-4">
        <FeedbackBanner feedback={feedback} onDismiss={() => setFeedback(null)} />
      </div>

      {/* Topbar: seletor + status + ações */}
      <div className="flex items-center justify-between gap-4 mb-6">
        <div className="flex items-center gap-3">
          <label className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50">Competência</label>
          <input
            type="month"
            value={mes}
            onChange={e => setMes(e.target.value)}
            className="px-3 py-2 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm"
          />
          {bp && <BPStatusBadge status={bp.status} />}
          {bp && !bp.indicador_fechamento_ok && (
            <span className="text-xs px-2 py-1 rounded-full bg-[color:var(--claude-coral)]/15 text-[color:var(--claude-coral)] font-medium flex items-center gap-1">
              <AlertCircle size={12} /> Não balanceia
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {editavel && (
            <button
              onClick={salvarRascunho}
              disabled={salvando || !dirty}
              className="px-4 py-2 rounded-lg bg-white border border-[color:var(--claude-ink)]/15 text-sm font-medium hover:bg-[color:var(--claude-ink)]/5 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Save size={14} /> {salvando ? 'Salvando…' : dirty ? 'Salvar rascunho' : 'Salvo'}
            </button>
          )}
          {editavel && (
            <button
              onClick={fecharBP}
              className="px-4 py-2 rounded-lg bg-[color:var(--claude-ink)] text-[color:var(--claude-cream)] text-sm font-medium hover:opacity-90 flex items-center gap-2"
            >
              <Check size={14} /> Fechar BP
            </button>
          )}
          {bp?.status === 'fechado' && (
            <>
              <button onClick={reabrirBP} className="px-4 py-2 rounded-lg bg-white border border-[color:var(--claude-ink)]/15 text-sm font-medium hover:bg-[color:var(--claude-ink)]/5">
                Reabrir
              </button>
              <button onClick={auditarBP} className="px-4 py-2 rounded-lg bg-[color:var(--claude-sage)] text-white text-sm font-medium hover:opacity-90 flex items-center gap-2">
                <Lock size={14} /> Auditar
              </button>
            </>
          )}
          {bp?.status === 'auditado' && (
            <span className="px-4 py-2 text-xs text-[color:var(--claude-ink)]/50 flex items-center gap-2">
              <Lock size={14} /> Imutável
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[color:var(--claude-ink)]/10 mb-6">
        <DRETab active={tab === 'resumo'} onClick={() => setTab('resumo')} icon={<PieChart size={16} />} label="Resumo" />
        <DRETab active={tab === 'ativo'} onClick={() => setTab('ativo')} icon={<Wallet size={16} />} label="Ativo" />
        <DRETab active={tab === 'passivo'} onClick={() => setTab('passivo')} icon={<Receipt size={16} />} label="Passivo" />
        <DRETab active={tab === 'pl'} onClick={() => setTab('pl')} icon={<Building2 size={16} />} label="Patrimônio Líquido" />
        <DRETab active={tab === 'indicadores'} onClick={() => setTab('indicadores')} icon={<BarChart3 size={16} />} label="Indicadores" />
        <DRETab active={tab === 'historico'} onClick={() => setTab('historico')} icon={<History size={16} />} label="Histórico" />
      </div>

      {loading || !bp ? (
        <EmptyState variant="loading" title="Carregando…" />
      ) : (
        <>
          {tab === 'resumo' && <BPResumoView bp={bp} comparativo={comparativo} />}
          {tab === 'ativo' && <BPAtivoView bp={bp} editavel={editavel} onChange={atualizarCampo} />}
          {tab === 'passivo' && <BPPassivoView bp={bp} editavel={editavel} onChange={atualizarCampo} />}
          {tab === 'pl' && <BPPLView bp={bp} editavel={editavel} onChange={atualizarCampo} />}
          {tab === 'indicadores' && <BPIndicadoresView bp={bp} indicadores={indicadores} />}
          {tab === 'historico' && <BPHistoricoView onSelect={(m) => { setMes(m); setTab('resumo') }} />}
        </>
      )}

      {/* Confirmar salvar antes de fechar (substitui window.confirm) */}
      <Confirm
        open={confirmFecharSalvar}
        title="Salvar antes de fechar?"
        body={
          <p>
            Há <strong>alterações não salvas</strong> no rascunho. O fechamento valida
            a equação fundamental usando os valores persistidos. Salvar agora antes
            de tentar fechar?
          </p>
        }
        confirmLabel="Salvar e fechar"
        loading={fechandoBP}
        onConfirm={confirmarSalvarEFechar}
        onCancel={() => setConfirmFecharSalvar(false)}
      />

      {/* Auditar BP — torna imutavel; danger=true (rosa) pra deixar serio */}
      <Confirm
        open={confirmAuditar}
        title="Auditar BP?"
        body={
          <p>
            Auditar marca este BP como <strong>imutável</strong>. Depois desta ação
            ele não pode mais ser editado nem reaberto sem trilha de auditoria.
            Continuar?
          </p>
        }
        confirmLabel="Auditar"
        danger
        loading={auditando}
        onConfirm={executarAuditar}
        onCancel={() => setConfirmAuditar(false)}
      />

      {/* Reabrir BP — destrava pra rascunho editavel */}
      <Confirm
        open={confirmReabrir}
        title="Reabrir BP?"
        body={
          <p>
            Reabrir volta o BP para <strong>rascunho editável</strong>. Os valores
            ficam disponíveis pra ajuste e o status muda. Continuar?
          </p>
        }
        confirmLabel="Reabrir"
        loading={reabrindo}
        onConfirm={executarReabrir}
        onCancel={() => setConfirmReabrir(false)}
      />
    </div>
  )
}

function BPStatusBadge({ status }: { status: BPStatus }) {
  const map: Record<BPStatus, { label: string; cls: string }> = {
    rascunho: { label: 'Rascunho', cls: 'bg-[color:var(--claude-ink)]/10 text-[color:var(--claude-ink)]/60' },
    fechado: { label: 'Fechado', cls: 'bg-[color:var(--claude-amber)]/20 text-[color:var(--claude-amber)]' },
    auditado: { label: 'Auditado', cls: 'bg-[color:var(--claude-sage)]/20 text-[color:var(--claude-sage)]' },
  }
  const { label, cls } = map[status]
  return <span className={`text-xs px-2 py-1 rounded-full font-medium ${cls}`}>{label}</span>
}

function BPResumoView({ bp, comparativo }: { bp: BP; comparativo: BPCompPonto[] }) {
  const sparkAtivo = comparativo.map(p => p.total_ativo)
  const sparkPL = comparativo.map(p => p.total_patrimonio_liquido)
  const sparkPassivo = comparativo.map(p => p.total_passivo)
  const plRatio = bp.total_ativo > 0 ? bp.total_patrimonio_liquido / bp.total_ativo : 0

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          title="Total Ativo"
          value={formatCurrency(bp.total_ativo)}
          subValue={`AC ${formatCurrency(bp.total_ativo_circulante)} · ANC ${formatCurrency(bp.total_ativo_nao_circulante)}`}
          status="neutral"
          sparklineData={sparkAtivo}
          sparklineTone="sage"
        />
        <KPICard
          title="Total Passivo"
          value={formatCurrency(bp.total_passivo)}
          subValue={`PC ${formatCurrency(bp.total_passivo_circulante)} · PNC ${formatCurrency(bp.total_passivo_nao_circulante)}`}
          status="neutral"
          sparklineData={sparkPassivo}
          sparklineTone="coral"
        />
        <KPICard
          title="Patrimônio Líquido"
          value={formatCurrency(bp.total_patrimonio_liquido)}
          subValue={`${formatPercent(plRatio)} do ativo`}
          status={bp.total_patrimonio_liquido > 0 ? 'up' : 'alert'}
          sparklineData={sparkPL}
          sparklineTone={bp.total_patrimonio_liquido >= 0 ? 'sage' : 'coral'}
        />
        <KPICard
          title="Equação Fundamental"
          value={bp.indicador_fechamento_ok ? 'OK' : `Δ ${formatCurrency(bp.diferenca_balanceamento)}`}
          subValue={bp.indicador_fechamento_ok ? 'Ativo = Passivo + PL' : 'Ativo ≠ Passivo + PL'}
          status={bp.indicador_fechamento_ok ? 'up' : 'alert'}
        />
      </div>

      {/* Tabela Ativo vs Passivo+PL */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl border border-[color:var(--claude-ink)]/8 overflow-hidden">
          <div className="px-6 py-3 bg-[color:var(--claude-sage)]/5 border-b border-[color:var(--claude-ink)]/8">
            <h3 className="headline text-[18px] tracking-editorial">Ativo</h3>
          </div>
          <table className="w-full">
            <tbody>
              <BPResumoRow label="Circulante" valor={bp.total_ativo_circulante} />
              <BPResumoRow label="Realizável a Longo Prazo" valor={bp.total_realizavel_longo_prazo} indent />
              <BPResumoRow label="Investimentos" valor={bp.total_investimentos} indent />
              <BPResumoRow label="Imobilizado" valor={bp.total_imobilizado} indent />
              <BPResumoRow label="Intangível" valor={bp.total_intangivel} indent />
              <BPResumoRow label="Não Circulante" valor={bp.total_ativo_nao_circulante} />
              <BPResumoRow label="Total Ativo" valor={bp.total_ativo} bold />
            </tbody>
          </table>
        </div>
        <div className="bg-white rounded-xl border border-[color:var(--claude-ink)]/8 overflow-hidden">
          <div className="px-6 py-3 bg-[color:var(--claude-coral)]/5 border-b border-[color:var(--claude-ink)]/8">
            <h3 className="headline text-[18px] tracking-editorial">Passivo + Patrimônio Líquido</h3>
          </div>
          <table className="w-full">
            <tbody>
              <BPResumoRow label="Passivo Circulante" valor={bp.total_passivo_circulante} />
              <BPResumoRow label="Passivo Não Circulante" valor={bp.total_passivo_nao_circulante} />
              <BPResumoRow label="Total Passivo" valor={bp.total_passivo} bold />
              <BPResumoRow label="Patrimônio Líquido" valor={bp.total_patrimonio_liquido} />
              <BPResumoRow label="Total Passivo + PL" valor={bp.total_passivo + bp.total_patrimonio_liquido} bold />
            </tbody>
          </table>
        </div>
      </div>

      {/* Série 12 meses */}
      {comparativo.length > 1 && (
        <div className="bg-white rounded-xl border border-[color:var(--claude-ink)]/8 p-6">
          <h3 className="headline text-[20px] tracking-editorial mb-4">Evolução patrimonial — 12 meses</h3>
          <div className="space-y-2">
            {comparativo.map((p, i) => {
              const max = Math.max(...comparativo.map(x => x.total_ativo), 1)
              const wAtivo = (p.total_ativo / max) * 100
              const wPL = Math.max(0, (p.total_patrimonio_liquido / max)) * 100
              return (
                <div key={i} className="flex items-center gap-4 text-xs">
                  <span className="w-16 font-mono text-[color:var(--claude-ink)]/60">{p.competencia}</span>
                  <div className="flex-1 h-6 bg-[color:var(--claude-ink)]/5 rounded relative overflow-hidden">
                    <div className="h-full bg-[color:var(--claude-sage)]/30" style={{ width: `${wAtivo}%` }} />
                    <div className="h-full bg-[color:var(--claude-sage)] absolute top-0 left-0" style={{ width: `${wPL}%` }} />
                  </div>
                  <span className="w-28 text-right font-mono">{formatCurrency(p.total_ativo)}</span>
                  <span className={`w-28 text-right font-mono text-xs ${p.total_patrimonio_liquido >= 0 ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]'}`}>
                    PL {formatCurrency(p.total_patrimonio_liquido)}
                  </span>
                </div>
              )
            })}
          </div>
          <div className="flex gap-4 text-[10px] uppercase tracking-wider mt-4 text-[color:var(--claude-ink)]/50">
            <span className="flex items-center gap-1.5"><span className="w-3 h-2 rounded bg-[color:var(--claude-sage)]/30" />Ativo Total</span>
            <span className="flex items-center gap-1.5"><span className="w-3 h-2 rounded bg-[color:var(--claude-sage)]" />Patrimônio Líquido</span>
          </div>
        </div>
      )}
    </div>
  )
}

function BPResumoRow({ label, valor, bold, indent }: { label: string; valor: number; bold?: boolean; indent?: boolean }) {
  return (
    <tr className={`border-b border-[color:var(--claude-ink)]/5 ${bold ? 'bg-[color:var(--claude-ink)]/[0.03]' : ''}`}>
      <td className={`py-2 text-sm ${indent ? 'pl-10' : 'pl-6'} pr-6 ${bold ? 'font-semibold' : 'text-[color:var(--claude-ink)]/75'}`}>{label}</td>
      <td className={`px-6 py-2 text-sm text-right font-mono tabular-nums ${bold ? 'font-semibold' : ''} ${valor < 0 ? 'text-[color:var(--claude-coral)]' : ''}`}>
        {formatCurrency(valor)}
      </td>
    </tr>
  )
}

function BPAtivoView({ bp, editavel, onChange }: { bp: BP; editavel: boolean; onChange: (c: keyof BP, v: number) => void }) {
  return (
    <div className="space-y-5">
      <BPGrupo titulo="Ativo Circulante" total={bp.total_ativo_circulante}>
        <BPField label="Caixa e Equivalentes" valor={bp.caixa_e_equivalentes} onChange={v => onChange('caixa_e_equivalentes', v)} editavel={editavel} />
        <BPField label="Bancos Conta Movimento" valor={bp.bancos_conta_movimento} onChange={v => onChange('bancos_conta_movimento', v)} editavel={editavel} />
        <BPField label="Aplicações Financeiras (CP)" valor={bp.aplicacoes_financeiras_curto_prazo} onChange={v => onChange('aplicacoes_financeiras_curto_prazo', v)} editavel={editavel} />
        <BPField label="Clientes / Contas a Receber" valor={bp.clientes_contas_a_receber} onChange={v => onChange('clientes_contas_a_receber', v)} editavel={editavel} />
        <BPField label="Adiantamentos a Fornecedores" valor={bp.adiantamentos_a_fornecedores} onChange={v => onChange('adiantamentos_a_fornecedores', v)} editavel={editavel} />
        <BPField label="Impostos a Recuperar" valor={bp.impostos_a_recuperar} onChange={v => onChange('impostos_a_recuperar', v)} editavel={editavel} />
        <BPField label="Estoque" valor={bp.estoque} onChange={v => onChange('estoque', v)} editavel={editavel} />
        <BPField label="Despesas Antecipadas" valor={bp.despesas_antecipadas} onChange={v => onChange('despesas_antecipadas', v)} editavel={editavel} />
        <BPField label="Outros Ativos Circulantes" valor={bp.outros_ativos_circulantes} onChange={v => onChange('outros_ativos_circulantes', v)} editavel={editavel} />
      </BPGrupo>

      <BPGrupo titulo="Realizável a Longo Prazo" total={bp.total_realizavel_longo_prazo}>
        <BPField label="Clientes Longo Prazo" valor={bp.clientes_longo_prazo} onChange={v => onChange('clientes_longo_prazo', v)} editavel={editavel} />
        <BPField label="Depósitos Judiciais" valor={bp.depositos_judiciais} onChange={v => onChange('depositos_judiciais', v)} editavel={editavel} />
        <BPField label="Impostos a Recuperar (LP)" valor={bp.impostos_a_recuperar_longo_prazo} onChange={v => onChange('impostos_a_recuperar_longo_prazo', v)} editavel={editavel} />
        <BPField label="Empréstimos Concedidos" valor={bp.emprestimos_concedidos} onChange={v => onChange('emprestimos_concedidos', v)} editavel={editavel} />
        <BPField label="Outros Realizáveis (LP)" valor={bp.outros_realizaveis_longo_prazo} onChange={v => onChange('outros_realizaveis_longo_prazo', v)} editavel={editavel} />
      </BPGrupo>

      <BPGrupo titulo="Investimentos" total={bp.total_investimentos}>
        <BPField label="Participações Societárias" valor={bp.participacoes_societarias} onChange={v => onChange('participacoes_societarias', v)} editavel={editavel} />
        <BPField label="Propriedades para Investimento" valor={bp.propriedades_para_investimento} onChange={v => onChange('propriedades_para_investimento', v)} editavel={editavel} />
        <BPField label="Outros Investimentos" valor={bp.outros_investimentos} onChange={v => onChange('outros_investimentos', v)} editavel={editavel} />
      </BPGrupo>

      <BPGrupo titulo="Imobilizado" total={bp.total_imobilizado}>
        <BPField label="Máquinas e Equipamentos" valor={bp.maquinas_e_equipamentos} onChange={v => onChange('maquinas_e_equipamentos', v)} editavel={editavel} />
        <BPField label="Veículos" valor={bp.veiculos} onChange={v => onChange('veiculos', v)} editavel={editavel} />
        <BPField label="Móveis e Utensílios" valor={bp.moveis_e_utensilios} onChange={v => onChange('moveis_e_utensilios', v)} editavel={editavel} />
        <BPField label="Imóveis" valor={bp.imoveis} onChange={v => onChange('imoveis', v)} editavel={editavel} />
        <BPField label="Computadores e Periféricos" valor={bp.computadores_e_perifericos} onChange={v => onChange('computadores_e_perifericos', v)} editavel={editavel} />
        <BPField label="Benfeitorias" valor={bp.benfeitorias} onChange={v => onChange('benfeitorias', v)} editavel={editavel} />
        <BPField label="Depreciação Acumulada" valor={bp.depreciacao_acumulada} onChange={v => onChange('depreciacao_acumulada', v)} editavel={editavel} redutora />
      </BPGrupo>

      <BPGrupo titulo="Intangível" total={bp.total_intangivel}>
        <BPField label="Marcas e Patentes" valor={bp.marcas_e_patentes} onChange={v => onChange('marcas_e_patentes', v)} editavel={editavel} />
        <BPField label="Softwares" valor={bp.softwares} onChange={v => onChange('softwares', v)} editavel={editavel} />
        <BPField label="Licenças" valor={bp.licencas} onChange={v => onChange('licencas', v)} editavel={editavel} />
        <BPField label="Goodwill" valor={bp.goodwill} onChange={v => onChange('goodwill', v)} editavel={editavel} />
        <BPField label="Amortização Acumulada" valor={bp.amortizacao_acumulada} onChange={v => onChange('amortizacao_acumulada', v)} editavel={editavel} redutora />
      </BPGrupo>

      <div className="bg-[color:var(--claude-sage)]/5 rounded-xl border border-[color:var(--claude-sage)]/20 px-6 py-4 flex items-center justify-between">
        <span className="headline text-[18px] tracking-editorial">Total Ativo</span>
        <span className="text-[22px] font-mono tabular-nums font-semibold">{formatCurrency(bp.total_ativo)}</span>
      </div>
    </div>
  )
}

function BPPassivoView({ bp, editavel, onChange }: { bp: BP; editavel: boolean; onChange: (c: keyof BP, v: number) => void }) {
  return (
    <div className="space-y-5">
      <BPGrupo titulo="Passivo Circulante" total={bp.total_passivo_circulante}>
        <BPField label="Fornecedores" valor={bp.fornecedores} onChange={v => onChange('fornecedores', v)} editavel={editavel} />
        <BPField label="Salários a Pagar" valor={bp.salarios_a_pagar} onChange={v => onChange('salarios_a_pagar', v)} editavel={editavel} />
        <BPField label="Encargos Sociais a Pagar" valor={bp.encargos_sociais_a_pagar} onChange={v => onChange('encargos_sociais_a_pagar', v)} editavel={editavel} />
        <BPField label="Impostos e Taxas a Recolher" valor={bp.impostos_e_taxas_a_recolher} onChange={v => onChange('impostos_e_taxas_a_recolher', v)} editavel={editavel} />
        <BPField label="Empréstimos/Financiamentos (CP)" valor={bp.emprestimos_financiamentos_curto_prazo} onChange={v => onChange('emprestimos_financiamentos_curto_prazo', v)} editavel={editavel} />
        <BPField label="Parcelamentos (CP)" valor={bp.parcelamentos_curto_prazo} onChange={v => onChange('parcelamentos_curto_prazo', v)} editavel={editavel} />
        <BPField label="Adiantamentos de Clientes" valor={bp.adiantamentos_de_clientes} onChange={v => onChange('adiantamentos_de_clientes', v)} editavel={editavel} />
        <BPField label="Dividendos a Pagar" valor={bp.dividendos_a_pagar} onChange={v => onChange('dividendos_a_pagar', v)} editavel={editavel} />
        <BPField label="Provisões (CP)" valor={bp.provisoes_curto_prazo} onChange={v => onChange('provisoes_curto_prazo', v)} editavel={editavel} />
        <BPField label="Outras Obrigações Circulantes" valor={bp.outras_obrigacoes_circulantes} onChange={v => onChange('outras_obrigacoes_circulantes', v)} editavel={editavel} />
      </BPGrupo>

      <BPGrupo titulo="Passivo Não Circulante" total={bp.total_passivo_nao_circulante}>
        <BPField label="Empréstimos/Financiamentos (LP)" valor={bp.emprestimos_financiamentos_longo_prazo} onChange={v => onChange('emprestimos_financiamentos_longo_prazo', v)} editavel={editavel} />
        <BPField label="Debêntures" valor={bp.debentures} onChange={v => onChange('debentures', v)} editavel={editavel} />
        <BPField label="Parcelamentos (LP)" valor={bp.parcelamentos_longo_prazo} onChange={v => onChange('parcelamentos_longo_prazo', v)} editavel={editavel} />
        <BPField label="Provisões (LP)" valor={bp.provisoes_longo_prazo} onChange={v => onChange('provisoes_longo_prazo', v)} editavel={editavel} />
        <BPField label="Contingências" valor={bp.contingencias} onChange={v => onChange('contingencias', v)} editavel={editavel} />
        <BPField label="Outras Obrigações (LP)" valor={bp.outras_obrigacoes_longo_prazo} onChange={v => onChange('outras_obrigacoes_longo_prazo', v)} editavel={editavel} />
      </BPGrupo>

      <div className="bg-[color:var(--claude-coral)]/5 rounded-xl border border-[color:var(--claude-coral)]/20 px-6 py-4 flex items-center justify-between">
        <span className="headline text-[18px] tracking-editorial">Total Passivo</span>
        <span className="text-[22px] font-mono tabular-nums font-semibold">{formatCurrency(bp.total_passivo)}</span>
      </div>
    </div>
  )
}

function BPPLView({ bp, editavel, onChange }: { bp: BP; editavel: boolean; onChange: (c: keyof BP, v: number) => void }) {
  return (
    <div className="space-y-5">
      <BPGrupo titulo="Patrimônio Líquido" total={bp.total_patrimonio_liquido}>
        <BPField label="Capital Social" valor={bp.capital_social} onChange={v => onChange('capital_social', v)} editavel={editavel} />
        <BPField label="Reservas de Capital" valor={bp.reservas_de_capital} onChange={v => onChange('reservas_de_capital', v)} editavel={editavel} />
        <BPField label="Ajustes de Avaliação Patrimonial" valor={bp.ajustes_de_avaliacao_patrimonial} onChange={v => onChange('ajustes_de_avaliacao_patrimonial', v)} editavel={editavel} />
        <BPField label="Reservas de Lucros" valor={bp.reservas_de_lucros} onChange={v => onChange('reservas_de_lucros', v)} editavel={editavel} />
        <BPField label="Lucros Acumulados" valor={bp.lucros_acumulados} onChange={v => onChange('lucros_acumulados', v)} editavel={editavel} />
        <BPField label="Prejuízos Acumulados" valor={bp.prejuizos_acumulados} onChange={v => onChange('prejuizos_acumulados', v)} editavel={editavel} redutora />
        <BPField label="Ações/Quotas em Tesouraria" valor={bp.acoes_ou_quotas_em_tesouraria} onChange={v => onChange('acoes_ou_quotas_em_tesouraria', v)} editavel={editavel} redutora />
      </BPGrupo>

      <div className="bg-[color:var(--claude-ink)]/5 rounded-xl border border-[color:var(--claude-ink)]/15 px-6 py-4 flex items-center justify-between">
        <span className="headline text-[18px] tracking-editorial">Total Patrimônio Líquido</span>
        <span className={`text-[22px] font-mono tabular-nums font-semibold ${bp.total_patrimonio_liquido < 0 ? 'text-[color:var(--claude-coral)]' : ''}`}>
          {formatCurrency(bp.total_patrimonio_liquido)}
        </span>
      </div>
    </div>
  )
}

function BPGrupo({ titulo, total, children }: { titulo: string; total: number; children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-[color:var(--claude-ink)]/8 overflow-hidden">
      <div className="px-6 py-3 border-b border-[color:var(--claude-ink)]/8 flex items-center justify-between">
        <h3 className="headline text-[16px] tracking-editorial">{titulo}</h3>
        <span className="text-sm font-mono tabular-nums font-semibold">{formatCurrency(total)}</span>
      </div>
      <div className="p-4 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
        {children}
      </div>
    </div>
  )
}

function BPField({ label, valor, onChange, editavel, redutora }: { label: string; valor: number; onChange: (v: number) => void; editavel: boolean; redutora?: boolean }) {
  return (
    <div className="grid grid-cols-[1fr,auto] items-center gap-3 py-1">
      <label className="text-sm text-[color:var(--claude-ink)]/75">
        {redutora && <span className="text-[color:var(--claude-coral)] mr-1">(−)</span>}
        {label}
      </label>
      {editavel ? (
        <input
          type="number"
          step="0.01"
          value={valor}
          onChange={e => onChange(Number(e.target.value) || 0)}
          className={`w-40 px-3 py-1.5 rounded-lg border border-[color:var(--claude-ink)]/15 bg-white text-sm font-mono text-right tabular-nums ${redutora ? 'text-[color:var(--claude-coral)]' : ''}`}
        />
      ) : (
        <span className={`w-40 text-sm font-mono tabular-nums text-right px-3 ${redutora ? 'text-[color:var(--claude-coral)]' : ''}`}>
          {formatCurrency(valor)}
        </span>
      )}
    </div>
  )
}

function BPIndicadoresView({ bp, indicadores }: { bp: BP; indicadores: BPIndicadores | null }) {
  if (!indicadores) return <EmptyState variant="empty" title="Sem dados suficientes para calcular indicadores." />

  const tone = (v: number, bom: number, ruim: number, invertido = false) => {
    if (invertido) return v <= bom ? 'sage' : v <= ruim ? 'amber' : 'coral'
    return v >= bom ? 'sage' : v >= ruim ? 'amber' : 'coral'
  }

  const indicadoresList = [
    {
      grupo: 'Liquidez',
      itens: [
        { label: 'Liquidez Corrente', valor: indicadores.liquidez_corrente, formato: 'ratio', formula: 'AC / PC', interp: 'Capacidade de pagar dívidas de curto prazo', color: tone(indicadores.liquidez_corrente, 1.5, 1.0) },
        { label: 'Liquidez Seca', valor: indicadores.liquidez_seca, formato: 'ratio', formula: '(AC − Estoque) / PC', interp: 'Liquidez sem depender do estoque', color: tone(indicadores.liquidez_seca, 1.0, 0.7) },
        { label: 'Liquidez Imediata', valor: indicadores.liquidez_imediata, formato: 'ratio', formula: '(Caixa + Bancos + AplicCP) / PC', interp: 'Capital disponível imediatamente', color: tone(indicadores.liquidez_imediata, 0.3, 0.15) },
      ],
    },
    {
      grupo: 'Estrutura de Capital',
      itens: [
        { label: 'Endividamento Geral', valor: indicadores.endividamento_geral, formato: 'pct', formula: '(PC + PNC) / Ativo', interp: '% do ativo financiado por terceiros', color: tone(indicadores.endividamento_geral, 0.5, 0.7, true) },
        { label: 'Composição Endividamento', valor: indicadores.composicao_endividamento, formato: 'pct', formula: 'PC / (PC + PNC)', interp: '% da dívida que vence no curto prazo', color: tone(indicadores.composicao_endividamento, 0.4, 0.6, true) },
        { label: 'Imobilização do PL', valor: indicadores.imobilizacao_pl, formato: 'pct', formula: 'Imobilizado / PL', interp: '% do capital próprio aplicado em ativo fixo', color: tone(indicadores.imobilizacao_pl, 0.5, 0.8, true) },
      ],
    },
    {
      grupo: 'Operacional',
      itens: [
        { label: 'Capital de Giro Líquido', valor: indicadores.capital_giro_liquido, formato: 'brl', formula: 'AC − PC', interp: 'Folga operacional disponível', color: indicadores.capital_giro_liquido >= 0 ? 'sage' : 'coral' },
      ],
    },
  ]

  return (
    <div className="space-y-6">
      {indicadoresList.map(grupo => (
        <div key={grupo.grupo}>
          <h3 className="headline text-[20px] tracking-editorial mb-3">{grupo.grupo}</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {grupo.itens.map(item => {
              const valorFmt = item.formato === 'brl'
                ? formatCurrency(item.valor)
                : item.formato === 'pct'
                  ? formatPercent(item.valor)
                  : formatNumber(item.valor, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
              const bgMap: Record<string, string> = {
                sage: 'var(--claude-sage)',
                amber: 'var(--claude-amber)',
                coral: 'var(--claude-coral)',
              }
              return (
                <div key={item.label} className="bg-white rounded-xl border border-[color:var(--claude-ink)]/8 p-5">
                  <div className="flex items-center justify-between mb-2">
                    <p className="section-label">{item.label}</p>
                    <span className="w-2 h-2 rounded-full" style={{ background: bgMap[item.color] }} />
                  </div>
                  <p className="text-[28px] leading-none font-mono tabular-nums font-semibold">{valorFmt}</p>
                  <p className="text-[11px] text-[color:var(--claude-ink)]/50 mt-2 font-mono">{item.formula}</p>
                  <p className="text-xs text-[color:var(--claude-ink)]/60 mt-1">{item.interp}</p>
                </div>
              )
            })}
          </div>
        </div>
      ))}

      <div className={`rounded-xl border px-6 py-4 ${bp.indicador_fechamento_ok ? 'bg-[color:var(--claude-sage)]/5 border-[color:var(--claude-sage)]/20' : 'bg-[color:var(--claude-coral)]/5 border-[color:var(--claude-coral)]/20'}`}>
        <div className="flex items-center justify-between">
          <div>
            <p className="headline text-[18px] tracking-editorial flex items-center gap-2">
              {bp.indicador_fechamento_ok ? <Check size={18} /> : <AlertCircle size={18} />}
              Equação Fundamental
            </p>
            <p className="text-sm text-[color:var(--claude-ink)]/70 mt-1">Ativo = Passivo + Patrimônio Líquido</p>
          </div>
          <div className="text-right font-mono tabular-nums text-sm">
            <div>Ativo: <span className="font-semibold">{formatCurrency(bp.total_ativo)}</span></div>
            <div>Passivo + PL: <span className="font-semibold">{formatCurrency(bp.total_passivo + bp.total_patrimonio_liquido)}</span></div>
            {!bp.indicador_fechamento_ok && (
              <div className="text-[color:var(--claude-coral)]">Diferença: {formatCurrency(bp.diferenca_balanceamento)}</div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function BPHistoricoView({ onSelect }: { onSelect: (mes: string) => void }) {
  const [itens, setItens] = useState<BPListItem[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const res = await axios.get(`${API_URL}/bp/listar`)
        setItens(res.data)
      } catch (e) {
        console.error(e)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  if (loading) return <EmptyState variant="loading" title="Carregando…" />
  if (itens.length === 0) return <EmptyState variant="empty" title="Nenhum BP cadastrado ainda." />

  return (
    <div className="bg-white rounded-xl border border-[color:var(--claude-ink)]/8 overflow-hidden">
      <table className="w-full">
        <thead>
          <tr className="text-xs uppercase tracking-wider text-[color:var(--claude-ink)]/50 border-b border-[color:var(--claude-ink)]/5">
            <th className="text-left px-6 py-3 font-medium">Competência</th>
            <th className="text-left px-6 py-3 font-medium">Status</th>
            <th className="text-right px-6 py-3 font-medium">Ativo</th>
            <th className="text-right px-6 py-3 font-medium">Passivo</th>
            <th className="text-right px-6 py-3 font-medium">PL</th>
            <th className="text-center px-6 py-3 font-medium">Balanceia</th>
            <th className="px-6 py-3" />
          </tr>
        </thead>
        <tbody>
          {itens.map(item => (
            <tr key={item.id} className="border-b border-[color:var(--claude-ink)]/5 hover:bg-[color:var(--claude-ink)]/[0.02]">
              <td className="px-6 py-3 text-sm font-mono">{item.competencia}</td>
              <td className="px-6 py-3"><BPStatusBadge status={item.status} /></td>
              <td className="px-6 py-3 text-sm text-right font-mono tabular-nums">{formatCurrency(item.total_ativo)}</td>
              <td className="px-6 py-3 text-sm text-right font-mono tabular-nums">{formatCurrency(item.total_passivo)}</td>
              <td className="px-6 py-3 text-sm text-right font-mono tabular-nums">{formatCurrency(item.total_patrimonio_liquido)}</td>
              <td className="px-6 py-3 text-center">
                {item.indicador_fechamento_ok ? (
                  <Check size={16} className="inline text-[color:var(--claude-sage)]" />
                ) : (
                  <X size={16} className="inline text-[color:var(--claude-coral)]" />
                )}
              </td>
              <td className="px-6 py-3 text-right">
                <button
                  onClick={() => onSelect(item.competencia)}
                  className="text-xs px-3 py-1 rounded border border-[color:var(--claude-ink)]/15 hover:bg-[color:var(--claude-ink)]/5"
                >
                  Abrir
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default App
