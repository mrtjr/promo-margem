import { useState, useEffect, useRef } from 'react'
import { LayoutDashboard, Package, Calculator, TrendingUp, AlertTriangle, Sparkles, ArrowRight, Gauge, ShoppingBag, FileText, Save, Copy, Check, Send, Bot, User, Trash2, Clipboard, AlertCircle, Target, History, ArrowDownCircle, ArrowUpCircle, X, ArrowUpRight, ArrowDownRight, Minus, PieChart, Receipt, Percent, Plus } from 'lucide-react'
import axios from 'axios'

// API base URL
const API_URL = '/api'

const CIDADES = ["TEIXEIRA DE FREITAS", "ITAMARAJU"]

function App() {
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchStats()
  }, [currentPage])

  const fetchStats = async () => {
    try {
      const res = await axios.get(`${API_URL}/stats`)
      setStats(res.data)
      setLoading(false)
    } catch (err) {
      console.error("Failed to fetch stats", err)
      setLoading(false)
    }
  }

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
          <div className="pt-4 pb-2 px-4 section-label text-[color:var(--claude-cream)]/40">Operações</div>
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
            isActive={currentPage === 'historico'}
            onClick={() => setCurrentPage('historico')}
            icon={<History size={20} />}
            label="Histórico"
          />
          <div className="pt-4 pb-2 px-4 section-label text-[color:var(--claude-cream)]/40">Financeiro</div>
          <NavItem
            isActive={currentPage === 'dre'}
            onClick={() => setCurrentPage('dre')}
            icon={<PieChart size={20} />}
            label="DRE"
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
        {loading && !['chat', 'compras', 'produtos', 'dashboard'].includes(currentPage) ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[color:var(--claude-coral)]"></div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            {currentPage === 'dashboard' && <DashboardPage stats={stats} onNavigate={setCurrentPage} />}
            {currentPage === 'chat' && <ChatPage />}
            {currentPage === 'produtos' && <ProdutosPage />}
            {currentPage === 'compras' && <ComprasPage onComplete={() => setCurrentPage('produtos')} />}
            {currentPage === 'relatorios' && <RelatoriosPage />}
            {currentPage === 'briefing' && <BriefingPage />}
            {currentPage === 'projecao' && <ProjecaoPage />}
            {currentPage === 'simulador' && <SimuladorPage />}
            {currentPage === 'historico' && <HistoricoPage />}
            {currentPage === 'dre' && <DREPage />}
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

function ComprasPage({ onComplete }: any) {
  const [produtos, setProdutos] = useState<any[]>([])
  const [grupos, setGrupos] = useState<any[]>([])
  const [rows, setRows] = useState<any[]>([
    { id: Date.now(), matchedId: null, name: '', cidade: '', qtd: '', peso: '', vl_fp: '', grupo_id: null }
  ])
  const [submitting, setSubmitting] = useState(false)

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
      // Expected: Prod | Cid | Qtd | Peso | Valor | Categoria (Texto)
      const [name, cidade, qtd, peso, vl_fp, cat_text] = parts
      
      // Auto-match product
      const matched = produtos.find(p => 
        p.nome.toLowerCase().includes((name || '').toLowerCase()) || 
        (name || '').toLowerCase().includes(p.nome.toLowerCase())
      )

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
        quantidade: parseInt(String(r.qtd).replace(/\D/g, '')) || 0,
        peso: parseFloat(String(r.peso).replace(',', '.')),
        custo_unitario: parseFloat(String(r.vl_fp).replace(',', '.')),
        cidade: r.cidade,
        grupo_id: r.grupo_id
      }))

    if (validEntradas.length === 0) return alert("Erro: Toda linha deve ter Produto, Cidade, Peso, Valor e Categoria selecionados!")

    setSubmitting(true)
    try {
      await axios.post(`${API_URL}/entradas/bulk`, { entradas: validEntradas })
      alert(`${validEntradas.length} lançamentos realizados!`)
      onComplete()
    } catch (err) {
      alert("Erro ao salvar lançamentos no servidor. Verifique os dados.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto p-8 space-y-8">
      <header className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold tracking-tight mb-2 flex items-center gap-3">
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
            <Save size={20} /> {submitting ? 'Salvando...' : 'Finalizar Cadastro'}
          </button>
        </div>
      </header>

      <div 
        onPaste={handlePaste}
        className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden"
      >
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Status</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Produto (Excel)</th>
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
                  <select 
                    className="w-full bg-slate-100/50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs outline-none focus:ring-2 focus:ring-blue-500"
                    value={row.matchedId || ''}
                    onChange={(e) => updateRow(row.id, 'matchedId', parseInt(e.target.value))}
                  >
                    <option value="">-- NOVO ITEM --</option>
                    {produtos.map(p => (
                      <option key={p.id} value={p.id}>{p.nome}</option>
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
              onClick={() => setRows([...rows, { id: Math.random(), matchedId: null, name: '', cidade: '', qtd: '', peso: '', vl_fp: '', grupo_id: null }])}
              className="text-[10px] font-black text-slate-400 hover:text-blue-600 uppercase tracking-widest"
            >
              + Adicionar Linha Manual
            </button>
        </div>
      </div>
    </div>
  )
}

function ProdutosPage() {
  const [produtos, setProdutos] = useState<any[]>([])
  const [grupos, setGrupos] = useState<any[]>([])
  const [editando, setEditando] = useState<any | null>(null)

  const carregar = () => {
    axios.get(`${API_URL}/produtos`).then(res => setProdutos(res.data))
  }

  useEffect(() => {
    carregar()
    axios.get(`${API_URL}/grupos`).then(res => setGrupos(res.data))
  }, [])

  return (
    <div className="max-w-6xl mx-auto p-8">
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-3xl font-bold tracking-tight">Gestão de SKUs</h2>
        <p className="text-xs text-slate-500">
          Clique em <span className="font-semibold text-blue-600">Editar</span> para definir o <span className="font-semibold">código ERP</span> usado no matching do CSV.
        </p>
      </div>
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Produto</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Código</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Custo Médio</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Margem</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Estoque (Vol)</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Peso Total (Kg/L)</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {produtos.length > 0 ? produtos.map(p => (
              <tr key={p.id} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4 text-sm font-bold text-slate-900">{p.nome}</td>
                <td className="px-6 py-4 text-xs font-mono">
                  {p.codigo
                    ? <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700 font-bold tracking-wider">{p.codigo}</span>
                    : <span className="text-slate-300 italic">—</span>}
                </td>
                <td className="px-6 py-4 text-sm text-slate-600 text-center">R$ {p.custo.toFixed(2)}</td>
                <td className="px-6 py-4 text-center">
                  <span className={`px-2 py-1 rounded-full text-[10px] font-black ${
                    p.margem >= 0.17 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                  }`}>{(p.margem * 100).toFixed(1)}%</span>
                </td>
                <td className="px-6 py-4 text-sm text-center font-extrabold text-slate-500">{(p.estoque_qtd || 0).toFixed(0)} <span className="text-[10px] text-slate-400">UN</span></td>
                <td className="px-6 py-4 text-sm text-center font-black text-blue-600">{(p.estoque_peso || 0).toFixed(1)} <span className="text-[10px] text-slate-400">Kg/L</span></td>
                <td className="px-6 py-4 text-right">
                  <button
                    onClick={() => setEditando(p)}
                    className="text-xs font-bold text-blue-600 hover:text-blue-700 hover:underline"
                  >
                    Editar
                  </button>
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-slate-400 italic font-medium">Nenhum item em estoque. Comece fazendo uma Entrada de Compra.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {editando && (
        <ProdutoEditModal
          produto={editando}
          grupos={grupos}
          onClose={() => setEditando(null)}
          onSaved={() => { setEditando(null); carregar(); }}
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
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 backdrop-blur-sm p-6">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">SKU {produto.sku}</p>
            <h3 className="text-xl font-bold tracking-tight">Editar produto</h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1">
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
            {salvando ? 'Salvando...' : 'Salvar'}
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
            x={padL - 8} y={yToPx(t) + 3}
            textAnchor="end"
            fontSize="10"
            fill="var(--claude-stone)"
            fontFamily="JetBrains Mono, monospace"
          >
            {(t * 100).toFixed(0)}%
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
            x={W - padR - 2} y={yToPx(media) - 4}
            textAnchor="end" fontSize="9"
            fill="var(--claude-stone)"
            fontFamily="JetBrains Mono, monospace"
          >
            média {(media * 100).toFixed(1)}%
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
              <title>{`${p.data} (${p.dia_semana}) · ${isSemVendas ? 'sem vendas' : `${(p.margem * 100).toFixed(1)}%`} · R$ ${p.faturamento.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`}</title>
            </circle>
          </g>
        )
      })}

      {/* Callout último ponto */}
      {lastValid.status !== 'sem_vendas' && (
        <g>
          <circle cx={lastX} cy={lastY} r="5" fill="var(--claude-coral)" fillOpacity="0.15" />
          <text
            x={Math.min(lastX + 8, W - padR - 46)}
            y={lastY - 8}
            fontSize="11"
            fontFamily="JetBrains Mono, monospace"
            fontWeight="600"
            fill="var(--claude-ink)"
          >
            {(lastValid.margem * 100).toFixed(1)}%
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
            x={xToPx(i)} y={H - 12}
            textAnchor={i === 0 ? 'start' : i === serie.length - 1 ? 'end' : 'middle'}
            fontSize="10"
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

function DashboardPage({ stats, onNavigate }: any) {
  const [saudeCategorias, setSaudeCategorias] = useState<any[]>([])
  const [projecao, setProjecao] = useState<any>(null)
  const [serie, setSerie] = useState<PontoSerie[]>([])

  useEffect(() => {
    axios.get(`${API_URL}/categorias/saude`).then(res => setSaudeCategorias(res.data)).catch(() => {})
    axios.get(`${API_URL}/projecao/amanha?top_n=0`).then(res => setProjecao(res.data)).catch(() => {})
    axios.get(`${API_URL}/margem/serie?dias=30`).then(res => setSerie(res.data)).catch(() => {})
  }, [])

  const marginPct = stats?.margem_semana ? (stats.margem_semana * 100).toFixed(1) : "0.0"
  const isHealthy = stats?.margem_semana >= 0.17 && stats?.margem_semana <= 0.19
  const projecaoPct = projecao?.margem_prevista ? (projecao.margem_prevista * 100).toFixed(1) : "—"
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

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <header className="flex justify-between items-end">
        <div>
          <p className="section-label mb-2">Visão Geral · {new Date().toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'long' })}</p>
          <h2 className="headline text-4xl tracking-editorial">Painel de Decisão</h2>
          <p className="text-[color:var(--claude-stone)] mt-1">Inteligência aplicada para garantir seus lucros.</p>
        </div>
        <div className="claude-card p-3 flex items-center gap-4">
          <div className="text-right">
            <p className="section-label leading-none mb-1">Margem Semana</p>
            <p className={`kpi-value text-2xl leading-none ${isHealthy ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]'}`}>{marginPct}%</p>
          </div>
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isHealthy ? 'bg-[color:var(--claude-sage)]/12 text-[color:var(--claude-sage)]' : 'bg-[color:var(--claude-coral)]/12 text-[color:var(--claude-coral)]'}`}>
            <Gauge size={22} />
          </div>
        </div>
      </header>

      {/* Stats Grid — Tremor-style: valor + delta + sparkline */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <KPICard
          title="Margem (dia)"
          value={ultMargem != null ? `${ultMargem.toFixed(1)}%` : '—'}
          status={ultMargem == null ? 'neutral' : ultMargem >= 17 && ultMargem <= 19 ? 'ok' : ultMargem < 17 ? 'alert' : 'warn'}
          delta={deltaMargem}
          deltaFormat="pp"
          deltaLabel={mediaPrev7Margem != null ? `vs média 7d (${mediaPrev7Margem.toFixed(1)}%)` : 'Meta 17–19%'}
          sparklineData={spark14Margem}
        />
        <KPICard
          title="Vendas (hoje)"
          value={`R$ ${faturamentoHoje.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          status={faturamentoHoje > 0 ? 'up' : 'neutral'}
          delta={deltaFatPct}
          deltaFormat="pct"
          deltaLabel={mediaPrev7Fat > 0 ? `vs média 7d (R$ ${mediaPrev7Fat.toLocaleString('pt-BR', { maximumFractionDigits: 0 })})` : 'Faturamento do dia'}
          sparklineData={spark14Fat}
        />
        <KPICard
          title="Projeção D+1"
          value={projecaoPct === "—" ? "—" : `${projecaoPct}%`}
          subValue={`Confiança: ${projecaoConfianca}`}
          status={projecaoConfianca === "sem_dados" ? "neutral" : (projecao?.margem_prevista >= 0.17 && projecao?.margem_prevista <= 0.19 ? "ok" : "warn")}
        />
        <KPICard
          title="Rupturas"
          value={stats?.rupturas || 0}
          subValue={stats?.rupturas > 0 ? `${stats.rupturas}/${stats?.total_skus} zerados · repor` : `${stats?.total_skus || 0} SKUs · 0 zerados`}
          status={stats?.rupturas > 0 ? "alert" : "ok"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="claude-card p-6 relative overflow-hidden">
            <div className="flex items-start justify-between mb-4">
              <div>
                <p className="section-label mb-1">Últimos 30 dias</p>
                <h3 className="headline text-2xl">Tendência de Margem</h3>
                <p className="text-xs text-[color:var(--claude-stone)] mt-1">
                  Faixa verde = meta 17–19%. Dots coral = dia em promoção acima da meta. Âmbar = abaixo. Cinza = sem venda.
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

          <div className="rounded-2xl p-6 text-white shadow-lg overflow-hidden relative"
               style={{ background: 'linear-gradient(135deg, #1C1B17 0%, #2A2620 60%, #CC785C 180%)' }}>
            <div className="flex justify-between items-start mb-6">
              <div>
                <h3 className="headline text-2xl mb-1 flex items-center gap-2 text-white">
                  <Sparkles className="text-[color:var(--claude-coral-soft)]" size={20} /> Copiloto IA
                </h3>
                <p className="text-white/60 text-sm">Motor pronto para responder qualquer dúvida sobre o dia.</p>
              </div>
              <button
                onClick={() => onNavigate('chat')}
                className="bg-white/10 hover:bg-white/20 text-white text-xs font-medium py-2 px-4 rounded-lg transition-colors flex items-center gap-2"
              >
                Abrir Chat <ArrowRight size={14} />
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button onClick={() => onNavigate('chat')} className="bg-white/8 hover:bg-white/15 transition-colors p-4 rounded-xl border border-white/10 text-left">
                <p className="section-label text-[color:var(--claude-coral-soft)] mb-2">Comando Sugerido</p>
                <p className="serif text-lg leading-tight mb-1">Como está meu lucro hoje?</p>
                <p className="text-[10px] text-white/50 uppercase tracking-widest">Toque para perguntar</p>
              </button>
              <button onClick={() => onNavigate('chat')} className="bg-white/8 hover:bg-white/15 transition-colors p-4 rounded-xl border border-white/10 text-left">
                <p className="section-label text-[color:var(--claude-coral-soft)] mb-2">Comando Sugerido</p>
                <p className="serif text-lg leading-tight mb-1">Análise de rupturas.</p>
                <p className="text-[10px] text-white/50 uppercase tracking-widest">Toque para perguntar</p>
              </button>
            </div>
          </div>
        </div>

        <div className="claude-card p-6 flex flex-col">
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
              <p className="text-[color:var(--claude-stone)] text-sm italic serif">Nenhum grupo cadastrado.</p>
            )}
          </div>
          <div className="mt-6 p-4 bg-[color:var(--claude-cream-deep)]/50 rounded-xl border border-dashed border-[color:var(--border)] flex flex-col items-center text-center">
             <ShoppingBag className="text-[color:var(--claude-stone)]/40 mb-2" size={20} />
             <p className="text-[10px] text-[color:var(--claude-stone)] leading-snug">Barra = margem real na escala. Marcas verticais = faixa da meta do grupo.</p>
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
    format === 'pp' ? `${isPositive ? '+' : ''}${value.toFixed(1)}pp`
    : format === 'pct' ? `${isPositive ? '+' : ''}${value.toFixed(1)}%`
    : `${isPositive ? '+' : '-'}R$ ${Math.abs(value).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`

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

  return (
    <div className="claude-card p-5 transition-all hover:shadow-[0_4px_16px_-8px_rgba(28,27,23,0.16)]">
      <div className="flex items-start justify-between gap-2">
        <p className="section-label">{title}</p>
        {delta !== undefined && <BadgeDelta value={delta} format={deltaFormat} invertColor={deltaInvertColor} />}
      </div>
      <p className="kpi-value text-[28px] leading-none text-[color:var(--claude-ink)] mt-2">{value}</p>
      {hasSpark ? (
        <div className="mt-3 -mx-1" aria-hidden="true">
          <Sparkline data={sparklineData!} tone={sparkTone} height={28} />
        </div>
      ) : (
        <div className="mt-3 h-[28px]" />
      )}
      <div className="mt-1 flex items-center justify-between">
        <p className="text-[10px] font-medium text-[color:var(--claude-stone)] uppercase tracking-wide">
          {deltaLabel || effectiveSub}
        </p>
        <span className={`w-2 h-2 rounded-full ${dotColor[effectiveStatus]}`}></span>
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

  const margemLabel = status === 'sem_vendas' ? '—' : `${(margemReal * 100).toFixed(1)}%`
  const metaLabel = `meta ${(metaMin * 100).toFixed(0)}–${(metaMax * 100).toFixed(0)}%`

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
            ? `${skusNoGrupo} SKUs · sem vendas`
            : `${skusVendidos}/${skusNoGrupo} · R$ ${Number(faturamento).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`
          }
        </span>
      </div>
    </div>
  )
}

function RelatoriosPage() {
  const [produtos, setProdutos] = useState<any[]>([])
  const [grupos, setGrupos] = useState<any[]>([])
  const [salesItems, setSalesItems] = useState<any>({})
  const [salesPrices, setSalesPrices] = useState<any>({})
  const [submitting, setSubmitting] = useState(false)
  const [summary, setSummary] = useState<any>(null)
  const [copied, setCopied] = useState(false)
  const [importOpen, setImportOpen] = useState(false)

  const carregarProdutos = () => {
    axios.get(`${API_URL}/produtos`).then(res => setProdutos(res.data))
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
      alert('Importação concluída, mas não consegui carregar a análise. Verifique na aba Histórico.')
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
        const price = salesPrices[id] || prod.preco_venda
        return {
          produto_id: id,
          quantidade: qty,
          preco_venda: price
        }
      })

    if (items.length === 0) return alert("Lance pelo menos uma venda!")

    setSubmitting(true)
    try {
      const res = await axios.post(`${API_URL}/fechamento`, { vendas: items })
      setSummary(res.data)
    } catch (err) {
      console.error(err)
      alert("Erro ao salvar vendas.")
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
      `• ${s.nome} [${s.classe_abc}${s.classe_xyz}] — ${s.quantidade.toFixed(2)}un / R$ ${s.receita.toFixed(2)}`
    ).join('\n')
    const anomaliaLines = (summary.anomalias || []).slice(0, 5).map((a: any) =>
      `• ${a.severidade === 'alta' ? '🔴' : '🟡'} ${a.descricao}`
    ).join('\n')

    const text =
      `📊 *Fechamento ${summary.data}*\n\n` +
      `Status: ${statusLabel}\n` +
      `💰 Faturamento: R$ ${summary.faturamento_dia.toFixed(2)}\n` +
      `🎯 Margem: ${(summary.margem_dia * 100).toFixed(1)}% (média 7d: ${(summary.margem_media_7d * 100).toFixed(1)}%)\n` +
      `📈 Variação vs 7d: ${summary.variacao_faturamento_7d_pct.toFixed(1)}%\n` +
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
          <h2 className="text-3xl font-bold tracking-tight mb-2">Fechamento de Vendas Diárias</h2>
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
                <td colSpan={3} className="px-6 py-12 text-center text-slate-400 italic">Nenhum produto cadastrado para venda.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}


// ============================================================================
// ImportCSVModal — upload + preview + resolução + commit
// Fluxo: estado 'upload' → 'preview' → 'feito'
// ============================================================================
function ImportCSVModal({ grupos, produtosExistentes, onClose, onCommitted }: any) {
  const hoje = new Date().toISOString().slice(0, 10)
  const [estado, setEstado] = useState<'upload' | 'preview'>('upload')
  const [arquivo, setArquivo] = useState<File | null>(null)
  const [dataAlvo, setDataAlvo] = useState<string>(hoje)
  const [preview, setPreview] = useState<any | null>(null)
  const [resolucoes, setResolucoes] = useState<Record<number, any>>({})
  const [submitting, setSubmitting] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  const enviarUpload = async () => {
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
      // Pre-inicializa resoluções: erro → ignorar, conflito/sem_match → 'associar' em branco
      const iniciais: Record<number, any> = {}
      for (const l of res.data.linhas) {
        if (l.status === 'erro') {
          iniciais[l.idx] = { idx: l.idx, acao: 'ignorar' }
        } else if (l.status !== 'ok') {
          iniciais[l.idx] = { idx: l.idx, acao: 'ignorar' }
        }
      }
      setResolucoes(iniciais)
      setEstado('preview')
    } catch (e: any) {
      setErro(e?.response?.data?.detail || 'Erro ao processar o arquivo.')
    } finally {
      setSubmitting(false)
    }
  }

  const atualizarResolucao = (idx: number, patch: any) => {
    setResolucoes((prev) => ({ ...prev, [idx]: { ...(prev[idx] || { idx }), ...patch } }))
  }

  const commitar = async () => {
    if (!preview) return
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
      onCommitted(dataAlvo)
    } catch (e: any) {
      setErro(e?.response?.data?.detail || 'Erro ao finalizar a importação.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-6">
      <div className="bg-white rounded-3xl border border-slate-200 shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-slate-200 flex items-center justify-between">
          <div>
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Fechamento via CSV · {estado === 'upload' ? '1 de 2' : '2 de 2'}</p>
            <h3 className="text-2xl font-bold tracking-tight">
              {estado === 'upload' ? 'Importar relatório de vendas' : 'Revisar e confirmar'}
            </h3>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700 p-1">
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
          {estado === 'preview' && preview && (
            <PreviewFase
              preview={preview}
              resolucoes={resolucoes}
              onResolucao={atualizarResolucao}
              produtosExistentes={produtosExistentes}
              grupos={grupos}
            />
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="text-sm">
            {erro && <span className="text-rose-600 font-semibold">{erro}</span>}
          </div>
          <div className="flex gap-2">
            {estado === 'preview' && (
              <button
                onClick={() => { setEstado('upload'); setPreview(null); setResolucoes({}) }}
                className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900"
              >
                Voltar
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-semibold text-slate-600 hover:text-slate-900"
            >
              Cancelar
            </button>
            {estado === 'upload' && (
              <button
                onClick={enviarUpload}
                disabled={submitting || !arquivo}
                className="bg-blue-600 text-white px-6 py-2.5 rounded-xl font-bold text-sm hover:bg-blue-700 disabled:opacity-50 transition-all"
              >
                {submitting ? 'Processando...' : 'Processar CSV'}
              </button>
            )}
            {estado === 'preview' && (
              <button
                onClick={commitar}
                disabled={submitting}
                className="bg-emerald-600 text-white px-6 py-2.5 rounded-xl font-bold text-sm hover:bg-emerald-700 disabled:opacity-50 transition-all"
              >
                {submitting ? 'Importando...' : (preview?.ja_existe_fechamento ? 'Substituir e importar' : 'Confirmar importação')}
              </button>
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
      <div className="p-4 bg-blue-50 border border-blue-200 rounded-xl text-sm text-slate-700">
        <p>
          <strong>Como funciona:</strong> o sistema lê o CSV do ERP (xRelVendaAnalitica),
          identifica cada item pelo <strong>código ERP</strong> e depois pelo nome
          (fallback), valida a aritmética e mostra um preview antes de gravar as
          vendas. Se já existir fechamento do dia, ele será substituído.
        </p>
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
            {arquivo.name} · {(arquivo.size / 1024).toFixed(1)} KB
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

function PreviewFase({ preview, resolucoes, onResolucao, produtosExistentes, grupos }: any) {
  const statusBadge = (status: string) => {
    const map: Record<string, string> = {
      ok: 'bg-emerald-100 text-emerald-700',
      conflito: 'bg-amber-100 text-amber-700',
      sem_match: 'bg-amber-100 text-amber-700',
      erro: 'bg-rose-100 text-rose-700',
    }
    return map[status] || 'bg-slate-100 text-slate-700'
  }
  const statusLabel = (status: string) => {
    const map: Record<string, string> = {
      ok: '✓ ok',
      conflito: 'conflito',
      sem_match: 'sem match',
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
        <MiniStat label="Receita" valor={`R$ ${preview.receita_total.toFixed(2)}`} cor="blue" />
        <MiniStat label="SKUs" valor={preview.skus_distintos} cor="slate" />
      </div>

      {preview.ja_existe_fechamento && (
        <div className="p-3 bg-amber-50 border border-amber-300 rounded-xl text-sm text-amber-900 flex items-start gap-2">
          <AlertTriangle size={18} className="shrink-0 mt-0.5" />
          <span>Já existe fechamento para <strong>{preview.data_alvo}</strong>. Ao confirmar, as vendas existentes serão apagadas e substituídas pelas do CSV.</span>
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
                <td className="px-3 py-2 text-right font-mono">{l.quantidade.toFixed(2)}</td>
                <td className="px-3 py-2 text-right font-mono">R$ {l.preco_unitario.toFixed(2)}</td>
                <td className="px-3 py-2 text-right font-mono font-bold">R$ {l.total.toFixed(2)}</td>
                <td className="px-3 py-2 text-center">
                  <span className={`inline-block px-2 py-0.5 rounded-md text-[10px] font-black ${statusBadge(l.status)}`}>
                    {statusLabel(l.status)}
                  </span>
                </td>
                <td className="px-3 py-2 min-w-[280px]">
                  {l.status === 'ok' ? (
                    <span className="text-[11px] text-emerald-700">→ {l.produto_nome}</span>
                  ) : (
                    <LinhaResolucao
                      linha={l}
                      resolucao={resolucoes[l.idx] || { idx: l.idx, acao: 'ignorar' }}
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

  return (
    <div className="space-y-1.5">
      <div className="flex gap-1.5">
        <BotaoAcao ativo={acao === 'associar'} onClick={() => onChange({ acao: 'associar' })} label="Associar" />
        <BotaoAcao ativo={acao === 'criar'} onClick={() => onChange({ acao: 'criar' })} label="Criar" />
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
              type="number" step="0.01"
              value={resolucao.novo_custo ?? ''}
              onChange={(e) => onChange({ novo_custo: parseFloat(e.target.value) || 0 })}
              placeholder="Custo"
              className="p-1.5 rounded border border-slate-300 text-xs bg-white"
            />
          </div>
          <p className="text-[10px] text-slate-500">Todos os campos são obrigatórios para criar.</p>
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
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (!proj) {
    return (
      <div className="max-w-4xl mx-auto p-8">
        <p className="text-slate-500 italic">Erro ao carregar projeção.</p>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-start">
        <div>
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Projeção para amanhã</p>
          <h2 className="text-3xl font-bold tracking-tight capitalize">{proj.dia_semana} · {new Date(proj.data_alvo + 'T12:00').toLocaleDateString('pt-BR')}</h2>
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
          <p className="text-2xl font-black leading-tight mt-1">R$ {proj.faturamento_previsto.toFixed(2)}</p>
          <p className="text-[10px] text-blue-200 mt-1">
            {proj.comparacao_media_7d_pct >= 0 ? '+' : ''}{proj.comparacao_media_7d_pct.toFixed(1)}% vs média 7d
          </p>
        </div>
        <div className="bg-white/10 p-4 rounded-xl border border-white/5">
          <p className="text-[10px] font-black text-blue-200 uppercase tracking-widest">Margem</p>
          <p className="text-2xl font-black leading-tight mt-1">{(proj.margem_prevista * 100).toFixed(1)}%</p>
          <p className="text-[10px] text-blue-200 mt-1">Meta 17–19%</p>
        </div>
        <div className="bg-white/10 p-4 rounded-xl border border-white/5">
          <p className="text-[10px] font-black text-blue-200 uppercase tracking-widest">Custo projetado</p>
          <p className="text-2xl font-black leading-tight mt-1">R$ {proj.custo_previsto.toFixed(2)}</p>
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
        <div className="p-6 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3">
          <AlertTriangle className="text-amber-600 shrink-0" size={18} />
          <div>
            <p className="text-sm font-bold text-amber-900">Sem histórico suficiente para projeção.</p>
            <p className="text-xs text-amber-700 mt-1">
              Registre ao menos 3 fechamentos diários para começar a gerar previsões. Confiança alta a partir de 21 dias.
            </p>
          </div>
        </div>
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
                <td className="py-2.5 text-right font-mono text-slate-600">{s.quantidade_prevista.toFixed(2)}</td>
                <td className="py-2.5 text-right font-mono font-bold text-slate-900">R$ {s.receita_prevista.toFixed(2)}</td>
                <td className="py-2.5 text-right">
                  <span className={`font-black ${s.margem_prevista >= 0.17 ? 'text-emerald-600' : 'text-rose-600'}`}>
                    {(s.margem_prevista * 100).toFixed(1)}%
                  </span>
                </td>
                <td className="py-2.5 text-right">
                  <span className={`text-xs font-bold ${s.dow_factor > 1.05 ? 'text-emerald-600' : s.dow_factor < 0.95 ? 'text-rose-600' : 'text-slate-500'}`}>
                    {s.dow_factor.toFixed(2)}×
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
    atencao:    { label: 'ATENÇÃO',    bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-500' },
    alerta:     { label: 'ALERTA',     bg: 'bg-rose-50',    text: 'text-rose-700',    border: 'border-rose-500' },
    sem_vendas: { label: 'SEM VENDAS', bg: 'bg-slate-50',   text: 'text-slate-600',   border: 'border-slate-400' },
  }
  const cfg = statusConfig[analise.status_meta] || statusConfig.sem_vendas

  const abc = analise.classificacao_abc || {}
  const xyz = analise.classificacao_xyz || {}
  const anomaliasOrdenadas = [...(analise.anomalias || [])].sort((a: any, b: any) => {
    const ord: Record<string, number> = { alta: 0, media: 1, baixa: 2 }
    return (ord[a.severidade] ?? 3) - (ord[b.severidade] ?? 3)
  })

  const sevIcon = (s: string) =>
    s === 'alta' ? <AlertTriangle size={14} className="text-rose-600" /> :
    s === 'media' ? <AlertCircle size={14} className="text-amber-600" /> :
    <Check size={14} className="text-slate-500" />

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-6">
      <header className="flex justify-between items-start">
        <div>
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Fechamento do dia</p>
          <h2 className="text-3xl font-bold tracking-tight">{new Date(analise.data + 'T12:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}</h2>
        </div>
        <div className={`${cfg.bg} ${cfg.text} ${cfg.border} border-2 px-6 py-3 rounded-2xl font-black uppercase text-sm tracking-widest shadow-sm`}>
          {cfg.label}
        </div>
      </header>

      {/* KPIs principais */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <KPICard title="Faturamento" value={`R$ ${analise.faturamento_dia.toFixed(2)}`} sub={`vs 7d: ${analise.variacao_faturamento_7d_pct >= 0 ? '+' : ''}${analise.variacao_faturamento_7d_pct.toFixed(1)}%`} tone={analise.variacao_faturamento_7d_pct >= -5 ? 'ok' : 'alert'} />
        <KPICard title="Margem do Dia" value={`${(analise.margem_dia * 100).toFixed(1)}%`} sub={`Meta: 17–19%`} tone={analise.status_meta === 'saudavel' ? 'ok' : analise.status_meta === 'alerta' ? 'alert' : 'warn'} />
        <KPICard title="Margem 7d / 30d" value={`${(analise.margem_media_7d * 100).toFixed(1)}%`} sub={`30d: ${(analise.margem_media_30d * 100).toFixed(1)}%`} tone="neutral" />
        <KPICard title="SKUs vendidos" value={`${analise.total_skus_vendidos}/${analise.total_skus_cadastrados}`} sub={`Rupturas: ${analise.rupturas}`} tone={analise.rupturas > 0 ? 'warn' : 'ok'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top SKUs */}
        <div className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
            <TrendingUp size={18} className="text-blue-500" /> Top SKUs do Dia
          </h3>
          {(analise.top_skus || []).length === 0 ? (
            <p className="text-sm text-slate-400 italic">Nenhuma venda registrada.</p>
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
                    <td className="py-2.5 text-right font-mono text-slate-600">{s.quantidade.toFixed(2)}</td>
                    <td className="py-2.5 text-right font-mono font-bold text-slate-900">R$ {s.receita.toFixed(2)}</td>
                    <td className="py-2.5 text-right">
                      <span className={`font-black ${s.margem_dia >= 0.17 ? 'text-emerald-600' : 'text-rose-600'}`}>
                        {(s.margem_dia * 100).toFixed(1)}%
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
          <p className="text-sm text-slate-400 italic flex items-center gap-2">
            <Check size={14} className="text-emerald-500" /> Nenhuma anomalia. Dia dentro do esperado.
          </p>
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
    return <div className="p-8 text-[color:var(--claude-stone)] serif italic">Gerando briefing…</div>
  }
  if (!briefing) {
    return <div className="p-8 text-[color:var(--claude-coral)]">Erro ao carregar briefing.</div>
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
            value={`${margemPct.toFixed(1)}%`}
            sub={`Meta 17-19% · ${analise.status_meta || '-'}`}
            tone={margemPct >= 17 && margemPct <= 19 ? 'ok' : margemPct < 17 ? 'alert' : 'warn'}
          />
          <KPICard
            title="Faturamento Hoje"
            value={`R$ ${(analise.faturamento_dia || 0).toFixed(2)}`}
            sub={`${(analise.variacao_faturamento_7d_pct || 0) > 0 ? '+' : ''}${(analise.variacao_faturamento_7d_pct || 0).toFixed(1)}% vs 7d`}
            tone={(analise.variacao_faturamento_7d_pct || 0) >= 0 ? 'ok' : 'warn'}
          />
          <KPICard
            title="Previsão Amanhã"
            value={`R$ ${(projecao.faturamento_previsto || 0).toFixed(2)}`}
            sub={`${projecao.dia_semana || '-'} · margem ${margemPrevPct.toFixed(1)}%`}
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
                <p className="kpi-value text-xl text-[color:var(--claude-ink)] mt-1">{(simCesta.margem_atual * 100).toFixed(2)}%</p>
              </div>
              <div className="bg-white rounded-lg p-3 border border-[color:var(--border)]">
                <p className="section-label">Margem pós</p>
                <p className={`kpi-value text-xl mt-1 ${simCesta.status === 'seguro' ? 'text-[color:var(--claude-sage)]' : simCesta.status === 'alerta' ? 'text-[color:var(--claude-amber)]' : 'text-[color:var(--claude-coral)]'}`}>
                  {(simCesta.nova_margem_estimada * 100).toFixed(2)}%
                </p>
              </div>
              <div className="bg-white rounded-lg p-3 border border-[color:var(--border)]">
                <p className="section-label">Impacto</p>
                <p className="kpi-value text-xl text-[color:var(--claude-ink)] mt-1">-{simCesta.impacto_pp.toFixed(2)}pp</p>
              </div>
              <div className="bg-white rounded-lg p-3 border border-[color:var(--border)]">
                <p className="section-label">SKUs afetados</p>
                <p className="kpi-value text-xl text-[color:var(--claude-ink)] mt-1">
                  {simCesta.skus_afetados} <span className="text-xs text-[color:var(--claude-stone)] font-normal">· {simCesta.desconto_medio_ponderado.toFixed(1)}% desc</span>
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
              <div className="claude-card p-8 text-center">
                <ShoppingBag className="mx-auto mb-3 text-[color:var(--claude-stone)]/40" size={28} />
                <p className="serif italic text-[color:var(--claude-stone)]">Nenhuma recomendação gerada para esta data.</p>
                <p className="text-xs text-[color:var(--claude-stone)]/70 mt-1">Registre vendas para o motor de inteligência começar a sugerir movimentos.</p>
              </div>
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
              <p className="kpi-value text-xl text-[color:var(--claude-coral)]">-{r.desconto_sugerido.toFixed(1)}%</p>
            </div>
          )}
          {r.preco_sugerido && (
            <div>
              <p className="section-label">Preço sug.</p>
              <p className="kpi-value text-sm text-[color:var(--claude-ink)]">R$ {r.preco_sugerido.toFixed(2)}</p>
            </div>
          )}
          <div>
            <p className="section-label">Margem</p>
            <p className="kpi-value text-sm text-[color:var(--claude-ink)]">
              {(r.margem_atual * 100).toFixed(1)}%
              {r.margem_pos_acao !== null && r.margem_pos_acao !== undefined && (
                <span className="text-[color:var(--claude-stone)]"> → {(r.margem_pos_acao * 100).toFixed(1)}%</span>
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

function SimuladorPage() {
  const [produtos, setProdutos] = useState<any[]>([])
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
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <h2 className="text-3xl font-bold tracking-tight">Simulador de Promoção</h2>
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
              <span className="text-xl font-black text-blue-600">{discount}%</span>
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
              <p className="text-5xl font-black text-slate-900 tracking-tighter">{(result.nova_margem_estimada * 100).toFixed(1)}%</p>
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
                  <span className="font-black text-slate-700">{(result.margem_atual * 100).toFixed(1)}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500 font-semibold">Impacto</span>
                  <span className={`font-black ${result.impacto_pp > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>
                    {result.impacto_pp > 0 ? '-' : '+'}{Math.abs(result.impacto_pp).toFixed(2)} pp
                  </span>
                </div>
              </div>
              <p className="text-xs text-slate-500 leading-relaxed italic">
                * Cálculo ponderado pelo estoque atual. Status bloqueado = margem &lt; 17%.
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400">
               <Sparkles className="mb-4 opacity-30" size={48} />
               <p className="text-sm italic font-medium">Selecione produtos para simular.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// HistoricoPage — inspeção e exclusão de entradas/saídas
// ============================================================================
type Movimentacao = {
  movimentacao_id: number
  venda_id: number | null
  tipo: 'ENTRADA' | 'SAIDA'
  produto_id: number | null
  produto_nome: string
  produto_sku: string | null
  quantidade: number
  peso: number
  custo_unitario: number
  valor_total: number
  cidade: string | null
  data: string | null
}

function HistoricoPage() {
  const [movs, setMovs] = useState<Movimentacao[]>([])
  const [loading, setLoading] = useState(true)
  const [dias, setDias] = useState(30)
  const [filtroTipo, setFiltroTipo] = useState<'' | 'ENTRADA' | 'SAIDA'>('')
  const [confirmando, setConfirmando] = useState<Movimentacao | null>(null)
  const [excluindo, setExcluindo] = useState(false)
  const [reconciliando, setReconciliando] = useState(false)
  const [toast, setToast] = useState<{ tipo: 'ok' | 'erro'; msg: string } | null>(null)

  const reconciliar = async () => {
    if (reconciliando) return
    if (!confirm('Reconciliar: recalcula estoque e custo de TODOS os produtos a partir do log de movimentações. Corrige estado inconsistente e desativa produtos sem movimentação. Continuar?')) return
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
      } else if (confirmando.venda_id) {
        await axios.delete(`${API_URL}/vendas/${confirmando.venda_id}`)
      } else {
        throw new Error('Venda órfã — sem venda_id para deletar.')
      }
      setToast({ tipo: 'ok', msg: `${confirmando.tipo === 'ENTRADA' ? 'Entrada' : 'Venda'} de ${confirmando.produto_nome} excluída. Estoque revertido.` })
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
    valorEntradas: movs.filter(m => m.tipo === 'ENTRADA').reduce((s, m) => s + m.valor_total, 0),
    valorSaidas: movs.filter(m => m.tipo === 'SAIDA').reduce((s, m) => s + m.valor_total, 0),
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
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="claude-card p-4">
          <p className="section-label">Entradas</p>
          <p className="kpi-value text-2xl text-[color:var(--claude-sage)] mt-1">{totais.entradas}</p>
          <p className="text-xs text-[color:var(--claude-stone)] mt-1 mono">R$ {totais.valorEntradas.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
        </div>
        <div className="claude-card p-4">
          <p className="section-label">Saídas</p>
          <p className="kpi-value text-2xl text-[color:var(--claude-coral)] mt-1">{totais.saidas}</p>
          <p className="text-xs text-[color:var(--claude-stone)] mt-1 mono">R$ {totais.valorSaidas.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
        </div>
        <div className="claude-card p-4 md:col-span-2">
          <p className="section-label">Fluxo líquido</p>
          <p className={`kpi-value text-2xl mt-1 ${totais.valorSaidas - totais.valorEntradas >= 0 ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]'}`}>
            {totais.valorSaidas - totais.valorEntradas >= 0 ? '+' : ''}R$ {(totais.valorSaidas - totais.valorEntradas).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
          </p>
          <p className="text-xs text-[color:var(--claude-stone)] mt-1">Receita − Custo de entradas na janela</p>
        </div>
      </div>

      {/* Tabela */}
      <div className="claude-card overflow-hidden">
        {loading ? (
          <div className="p-12 flex justify-center">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[color:var(--claude-coral)]"></div>
          </div>
        ) : movs.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="mx-auto mb-3 text-[color:var(--claude-stone)]/40" size={32} />
            <p className="serif italic text-[color:var(--claude-stone)]">Nenhuma movimentação no período.</p>
            <p className="text-xs text-[color:var(--claude-stone)]/70 mt-1">Lance entradas e vendas pra começar o histórico.</p>
          </div>
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
                const acentColor = isEntrada ? 'var(--claude-sage)' : 'var(--claude-coral)'
                const Icon = isEntrada ? ArrowDownCircle : ArrowUpCircle
                const dataFmt = m.data
                  ? new Date(m.data).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' })
                  : '—'
                const podeExcluir = isEntrada || m.venda_id !== null
                return (
                  <tr key={`${m.tipo}-${m.movimentacao_id}`} className="hover:bg-[color:var(--claude-cream-deep)]/30 transition-colors">
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide"
                            style={{ color: acentColor }}>
                        <Icon size={14} /> {m.tipo}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium text-[color:var(--claude-ink)] truncate max-w-[220px]">{m.produto_nome}</p>
                      {m.produto_sku && <p className="text-[10px] text-[color:var(--claude-stone)] mono">{m.produto_sku}</p>}
                    </td>
                    <td className="px-4 py-3 text-right mono text-sm text-[color:var(--claude-ink)]">{m.quantidade.toLocaleString('pt-BR', {maximumFractionDigits: 2})}</td>
                    <td className="px-4 py-3 text-right mono text-sm text-[color:var(--claude-stone)]">{m.peso > 0 ? m.peso.toFixed(2) : '—'}</td>
                    <td className="px-4 py-3 text-right mono text-sm text-[color:var(--claude-ink)]">R$ {m.custo_unitario.toFixed(2)}</td>
                    <td className="px-4 py-3 text-right mono text-sm font-semibold" style={{ color: acentColor }}>
                      R$ {m.valor_total.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
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
                  <h3 className="headline text-xl">Reverter {confirmando.tipo === 'ENTRADA' ? 'entrada' : 'venda'}?</h3>
                </div>
              </div>
              <button onClick={() => !excluindo && setConfirmando(null)}
                      className="p-1 text-[color:var(--claude-stone)] hover:text-[color:var(--claude-ink)]">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-2 text-sm text-[color:var(--claude-ink)] mb-5">
              <p><span className="text-[color:var(--claude-stone)]">Produto:</span> <span className="font-medium">{confirmando.produto_nome}</span></p>
              <p><span className="text-[color:var(--claude-stone)]">Quantidade:</span> <span className="mono">{confirmando.quantidade.toLocaleString('pt-BR', {maximumFractionDigits: 2})}</span></p>
              <p><span className="text-[color:var(--claude-stone)]">Valor:</span> <span className="mono">R$ {confirmando.valor_total.toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span></p>
              <div className="mt-3 p-3 rounded-lg text-xs"
                   style={{ background: 'color-mix(in srgb, var(--claude-amber) 10%, transparent)', color: 'var(--claude-ink)' }}>
                {confirmando.tipo === 'ENTRADA'
                  ? <>⚠ Estoque cairá {confirmando.quantidade} un. Custo médio será recalculado a partir das entradas restantes.</>
                  : <>↩ Estoque voltará +{confirmando.quantidade} un. Faturamento e margem do dia {confirmando.data?.slice(0, 10)} serão decrementados.</>
                }
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

function formatBRL(v: number): string {
  const sig = v < 0 ? '-' : ''
  return sig + 'R$ ' + Math.abs(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatPct(v: number): string {
  return (v * 100).toFixed(2) + '%'
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
        <DRETab active={tab === 'cascata'} onClick={() => setTab('cascata')} icon={<PieChart size={16} />} label="Cascata" />
        <DRETab active={tab === 'despesas'} onClick={() => setTab('despesas')} icon={<Receipt size={16} />} label="Lançamentos" />
        <DRETab active={tab === 'tributario'} onClick={() => setTab('tributario')} icon={<Percent size={16} />} label="Tributário" />
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
              alert('Mês fechado.')
            } catch (e) {
              alert('Falha ao fechar: ' + (e as any).message)
            }
          }}
        />
      )}
      {tab === 'despesas' && <DREDespesasView mes={mes} onMesChange={setMes} />}
      {tab === 'tributario' && <DRETributarioView />}
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
    return <div className="p-8 text-center text-[color:var(--claude-ink)]/50">Calculando…</div>
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
          value={formatBRL(dre.receita_bruta)}
          subValue={`${comparativo.length} meses no gráfico`}
          status="neutral"
          delta={deltaReceitaPct}
          deltaFormat="pct"
          deltaLabel={mediaPrevReceita > 0 ? `vs média (${formatBRL(mediaPrevReceita)})` : 'Sem histórico'}
          sparklineData={sparkReceita}
          sparklineTone="sage"
        />
        <KPICard
          title="Margem Bruta"
          value={formatPct(dre.margem_bruta_pct)}
          subValue={formatBRL(dre.lucro_bruto)}
          status={dre.margem_bruta_pct >= 0.2 ? 'up' : dre.margem_bruta_pct >= 0.15 ? 'ok' : 'warn'}
          delta={deltaMB}
          deltaFormat="pp"
          deltaLabel={mediaPrevMB > 0 ? `vs média (${mediaPrevMB.toFixed(1)}%)` : 'Sem histórico'}
          sparklineData={margemBrutaHist}
          sparklineTone="coral"
        />
        <KPICard
          title="EBITDA"
          value={formatBRL(dre.ebitda)}
          subValue={`${formatPct(dre.ebitda_pct)} da receita`}
          status={dre.ebitda_pct >= 0.1 ? 'up' : dre.ebitda_pct >= 0.05 ? 'ok' : dre.ebitda >= 0 ? 'warn' : 'alert'}
          delta={deltaEb}
          deltaFormat="pp"
          deltaLabel={mediaPrevEb !== 0 ? `vs média (${mediaPrevEb.toFixed(1)}%)` : 'Sem histórico'}
          sparklineData={ebitdaPctHist}
          sparklineTone="amber"
        />
        <KPICard
          title="Lucro Líquido"
          value={formatBRL(dre.lucro_liquido)}
          subValue={formatPct(dre.margem_liquida_pct)}
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
              return (
                <div key={i} className="flex items-center gap-4 text-xs">
                  <span className="w-16 font-mono text-[color:var(--claude-ink)]/60">{p.mes}</span>
                  <div className="flex-1 h-6 bg-[color:var(--claude-ink)]/5 rounded relative overflow-hidden">
                    <div className="h-full bg-[color:var(--claude-sage)]/30" style={{ width: `${wRec}%` }} />
                    {!isNeg && (
                      <div className="h-full bg-[color:var(--claude-sage)] absolute top-0 left-0" style={{ width: `${wEbi}%` }} />
                    )}
                    {isNeg && <div className="absolute top-0 left-0 h-full bg-[color:var(--claude-coral)]/40" style={{ width: `${wRec}%` }} />}
                  </div>
                  <span className="w-24 text-right font-mono">{formatBRL(p.receita_bruta)}</span>
                  <span className={`w-20 text-right font-mono text-xs ${p.lucro_liquido >= 0 ? 'text-[color:var(--claude-sage)]' : 'text-[color:var(--claude-coral)]'}`}>
                    {formatBRL(p.lucro_liquido)}
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
        {formatBRL(linha.valor)}
      </td>
      <td className="px-6 py-2 text-sm text-right font-mono tabular-nums text-[color:var(--claude-ink)]/50">
        {linha.pct_receita.toFixed(1)}%
      </td>
    </tr>
  )
}

function DREDespesasView({ mes, onMesChange }: { mes: string; onMesChange: (m: string) => void }) {
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
      alert('Preencha conta e valor.')
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
      fetchData()
    } catch (e) {
      alert('Falha: ' + (e as any).message)
    }
  }

  const handleExcluir = async (id: number) => {
    if (!confirm('Excluir lançamento?')) return
    await axios.delete(`${API_URL}/despesas/${id}`)
    fetchData()
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
              <p className="text-lg font-semibold mt-1 font-mono tabular-nums">{formatBRL(total)}</p>
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
          <div className="p-8 text-center text-[color:var(--claude-ink)]/50">Carregando…</div>
        ) : lancamentos.length === 0 ? (
          <div className="p-8 text-center text-[color:var(--claude-ink)]/50">
            Nenhum lançamento em {mes}. Clique em "Novo lançamento" pra começar.
          </div>
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
                  <td className="px-6 py-3 text-sm text-right font-mono tabular-nums">{formatBRL(l.valor)}</td>
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
    </div>
  )
}

function DRETributarioView() {
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
    } catch (e) {
      alert('Falha: ' + (e as any).message)
    }
  }

  if (!config) return <div className="p-8 text-center text-[color:var(--claude-ink)]/50">Carregando…</div>

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
        <p className="col-span-2 text-sm font-mono tabular-nums">{(valor * 100).toFixed(2)}% <span className="text-[color:var(--claude-ink)]/40">({valor.toFixed(4)})</span></p>
      )}
    </div>
  )
}

export default App
