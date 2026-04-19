import { useState, useEffect, useRef } from 'react'
import { LayoutDashboard, Package, Calculator, TrendingUp, AlertTriangle, Sparkles, ArrowRight, Gauge, ShoppingBag, FileText, Save, Copy, Check, Send, Bot, User, Trash2, Clipboard, AlertCircle } from 'lucide-react'
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
    <div className="flex h-screen bg-slate-50 text-slate-900 font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-6">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
            PromoMargem
          </h1>
          <p className="text-slate-400 text-xs mt-1 uppercase tracking-widest font-semibold">Gestão Inteligente</p>
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
          <div className="pt-4 pb-2 px-4 text-[10px] font-bold text-slate-500 uppercase tracking-widest">Operações</div>
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
            isActive={currentPage === 'simulador'} 
            onClick={() => setCurrentPage('simulador')}
            icon={<Calculator size={20} />} 
            label="Simulador" 
          />
        </nav>

        <div className="p-4 bg-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-xs font-bold text-white">JR</div>
            <div>
              <p className="text-sm font-medium">Gestor Comercial</p>
              <div className="flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                <p className="text-[10px] text-slate-400 font-bold uppercase">Online</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {loading && !['chat', 'compras', 'produtos', 'dashboard'].includes(currentPage) ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            {currentPage === 'dashboard' && <DashboardPage stats={stats} onNavigate={setCurrentPage} />}
            {currentPage === 'chat' && <ChatPage />}
            {currentPage === 'produtos' && <ProdutosPage />}
            {currentPage === 'compras' && <ComprasPage onComplete={() => setCurrentPage('produtos')} />}
            {currentPage === 'relatorios' && <RelatoriosPage />}
            {currentPage === 'simulador' && <SimuladorPage />}
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
      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 ${
        isActive 
          ? 'bg-blue-600 text-white shadow-lg shadow-blue-900/20' 
          : 'text-slate-400 hover:bg-slate-800 hover:text-slate-100'
      }`}
    >
      {icon}
      <span className="font-medium">{label}</span>
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

  useEffect(() => {
    axios.get(`${API_URL}/produtos`).then(res => setProdutos(res.data))
  }, [])

  return (
    <div className="max-w-6xl mx-auto p-8">
      <h2 className="text-3xl font-bold tracking-tight mb-8">Gestão de SKUs</h2>
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Produto</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Custo Médio</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Margem</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Estoque (Vol)</th>
              <th className="px-6 py-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Peso Total (Kg/L)</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {produtos.length > 0 ? produtos.map(p => (
              <tr key={p.id} className="hover:bg-slate-50/50 transition-colors">
                <td className="px-6 py-4 text-sm font-bold text-slate-900">{p.nome}</td>
                <td className="px-6 py-4 text-sm text-slate-600 text-center">R$ {p.custo.toFixed(2)}</td>
                <td className="px-6 py-4 text-center">
                  <span className={`px-2 py-1 rounded-full text-[10px] font-black ${
                    p.margem >= 0.17 ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                  }`}>{(p.margem * 100).toFixed(1)}%</span>
                </td>
                <td className="px-6 py-4 text-sm text-center font-extrabold text-slate-500">{(p.estoque_qtd || 0).toFixed(0)} <span className="text-[10px] text-slate-400">UN</span></td>
                <td className="px-6 py-4 text-sm text-center font-black text-blue-600">{(p.estoque_peso || 0).toFixed(1)} <span className="text-[10px] text-slate-400">Kg/L</span></td>
              </tr>
            )) : (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-slate-400 italic font-medium">Nenhum item em estoque. Comece fazendo uma Entrada de Compra.</td>
              </tr>
            )}
          </tbody>
        </table>
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

function DashboardPage({ stats, onNavigate }: any) {
  const [grupos, setGrupos] = useState<any[]>([])
  
  useEffect(() => {
    axios.get(`${API_URL}/grupos`).then(res => setGrupos(res.data))
  }, [])

  const marginPct = (stats?.total_skus > 0 && stats?.margem_semana) ? (stats?.margem_semana * 100).toFixed(1) : "0.0"
  const isHealthy = stats?.margem_semana >= 0.17 && stats?.margem_semana <= 0.19
  const hasSales = stats?.total_vendas_hoje > 0

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <header className="flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Painel de Decisão</h2>
          <p className="text-slate-500">Inteligência aplicada para garantir seus lucros.</p>
        </div>
        <div className="bg-white p-3 rounded-xl border border-slate-200 flex items-center gap-4 shadow-sm">
          <div className="text-right">
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider leading-none mb-1">Margem Global</p>
            <p className={`text-xl font-black ${isHealthy ? 'text-emerald-500' : 'text-amber-500'}`}>{marginPct}%</p>
          </div>
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${isHealthy ? 'bg-emerald-50 text-emerald-500' : 'bg-amber-50 text-amber-500'}`}>
            <Gauge size={24} />
          </div>
        </div>
      </header>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <StatCard title="Projeção Atual" value={`${marginPct}%`} subValue="Base Sazonal" status={isHealthy ? "ok" : "alert"} />
        <StatCard title="Vendas (Hoje)" value={`R$ ${stats?.total_vendas_hoje?.toFixed(2) || '0.00'}`} subValue="Faturamento Real" status="up" />
        <StatCard title="Total SKUs" value={stats?.total_skus || '0'} subValue="Itens Cadastrados" status="neutral" />
        <StatCard title="Rupturas" value={stats?.rupturas || '0'} subValue="Estoque Zerado" status={stats?.rupturas > 0 ? "alert" : "ok"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm relative overflow-hidden">
            <div className="absolute top-0 right-0 p-4 opacity-5">
              <TrendingUp size={120} />
            </div>
            <h3 className="font-bold text-lg mb-4">Tendência de Margem vs Vendas</h3>
            <div className="h-64 bg-slate-50 rounded-xl flex flex-col items-center justify-center text-slate-400 text-sm italic">
              {stats?.total_skus > 0 ? (
                 <span>[Gráfico de Elasticidade Alimentado]</span>
              ) : (
                 <>
                   <AlertTriangle className="mb-2 text-slate-300" size={32} />
                   <span>Cadastre produtos para gerar inteligência de mercado.</span>
                 </>
              )}
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-blue-600 to-blue-800 p-6 rounded-2xl text-white shadow-xl shadow-blue-900/20 transition-all hover:scale-[1.01]">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h3 className="text-xl font-bold mb-1 flex items-center gap-2">
                  <Sparkles className="text-blue-300" size={20} /> Copiloto IA
                </h3>
                <p className="text-blue-200 text-sm">O motor está pronto para responder qualquer dúvida.</p>
              </div>
              <button 
                onClick={() => onNavigate('chat')}
                className="bg-white/10 hover:bg-white/20 text-white text-xs font-bold py-2 px-4 rounded-lg transition-colors flex items-center gap-2"
              >
                Abrir Chat <ArrowRight size={14} />
              </button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white/10 p-4 rounded-xl border border-white/5">
                <p className="text-xs font-bold text-blue-200 uppercase mb-2">Comando Sugerido</p>
                <p className="font-bold text-lg leading-tight mb-2">Como está meu lucro hoje?</p>
                <p className="text-[10px] text-blue-100 uppercase tracking-widest font-black italic">Toque para perguntar</p>
              </div>
              <div className="bg-white/10 p-4 rounded-xl border border-white/5">
                <p className="text-xs font-bold text-blue-200 uppercase mb-2">Comando Sugerido</p>
                <p className="font-bold text-lg leading-tight mb-2">Análise de rupturas.</p>
                <p className="text-[10px] text-blue-100 uppercase tracking-widest font-black italic">Toque para perguntar</p>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm flex flex-col">
          <h3 className="font-bold text-lg mb-4">Saúde por Categoria</h3>
          <div className="flex-1 space-y-6">
            {grupos.length > 0 ? grupos.map((g: any) => (
              <GroupProgress 
                key={g.id} 
                label={g.nome} 
                value={hasSales ? 50 : 0} // Placeholder fixed logic: if no sales, show 0.
                margin={`${(g.margem_minima * 100).toFixed(0)} - ${(g.margem_maxima * 100).toFixed(0)}%`} 
                status={hasSales ? "high" : "neutral"} 
              />
            )) : (
              <p className="text-slate-400 text-sm italic">Nenhum grupo cadastrado.</p>
            )}
          </div>
          <div className="mt-8 p-4 bg-slate-50 rounded-xl border border-dashed border-slate-200 flex flex-col items-center text-center">
             <ShoppingBag className="text-slate-300 mb-2" size={24} />
             <p className="text-[10px] font-bold text-slate-500">Acompanha a saúde das 4 categorias principais em tempo real conforme as vendas ocorrem.</p>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({ title, value, subValue, status }: any) {
  const getStatusColor = () => {
    switch(status) {
      case 'up': return 'text-emerald-500';
      case 'alert': return 'text-rose-500';
      case 'ok': return 'text-blue-500';
      default: return 'text-slate-400';
    }
  }

  return (
    <div className="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm transition-all hover:shadow-md">
      <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">{title}</p>
      <p className="text-2xl font-black text-slate-900 leading-none">{value}</p>
      <div className="mt-3 flex items-center justify-between">
        <p className="text-[10px] font-medium text-slate-500 uppercase">{subValue}</p>
        <span className={`w-2 h-2 rounded-full ${getStatusColor().replace('text-', 'bg-')}`}></span>
      </div>
    </div>
  )
}

function GroupProgress({ label, value, margin, status }: any) {
  const colors = {
    ok: 'bg-emerald-500',
    low: 'bg-amber-500',
    high: 'bg-blue-500',
    neutral: 'bg-slate-200'
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm font-bold text-slate-700">{label}</span>
        <span className="text-xs font-black bg-slate-100 px-2 py-0.5 rounded text-slate-600">{margin}</span>
      </div>
      <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-1000 ${(colors as any)[status] || colors.neutral}`} style={{ width: `${value}%` }}></div>
      </div>
    </div>
  )
}

function RelatoriosPage() {
  const [produtos, setProdutos] = useState<any[]>([])
  const [salesItems, setSalesItems] = useState<any>({})
  const [salesPrices, setSalesPrices] = useState<any>({})
  const [submitting, setSubmitting] = useState(false)
  const [summary, setSummary] = useState<any>(null)
  const [copied, setCopied] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    axios.get(`${API_URL}/produtos`).then(res => setProdutos(res.data))
  }, [])

  const handleQtyChange = (id: number, val: string) => {
    const qty = parseFloat(val) || 0
    setSalesItems({ ...salesItems, [id]: qty })
  }

  const handlePriceChange = (id: number, val: string) => {
    const price = parseFloat(val) || 0
    setSalesPrices({ ...salesPrices, [id]: price })
  }

  const handleImportCSV = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    const normalize = (txt: string) => 
      txt.normalize("NFD").replace(/[\u0300-\u036f]/g, "").trim().toUpperCase()

    const reader = new FileReader()
    reader.onload = (event) => {
      const content = event.target?.result as string
      const lines = content.split(/\r?\n/)
      
      // key: normalizedName -> {qty: number, total: number}
      const importedData: Record<string, {qty: number, total: number}> = {}

      lines.forEach(line => {
        if (line.startsWith('Pedido;')) {
          const parts = line.split(';')
          if (parts.length > 12) {
            const rawName = parts[4]?.trim()
            const qtyStr = parts[10]?.replace(',', '.')
            const totalStr = parts[12]?.replace(',', '.')
            
            const qty = parseFloat(qtyStr) || 0
            const total = parseFloat(totalStr) || 0
            
            if (rawName && qty > 0) {
              const name = normalize(rawName)
              if (!importedData[name]) importedData[name] = { qty: 0, total: 0 }
              importedData[name].qty += qty
              importedData[name].total += total
            }
          }
        }
      })

      // Link imported data to our products
      const newSalesItems = { ...salesItems }
      const newSalesPrices = { ...salesPrices }
      let matchedCount = 0
      const notFoundNames: string[] = []
      
      const csvNames = Object.keys(importedData)
      const matchedCsvNames = new Set<string>()

      produtos.forEach(p => {
        const sysName = normalize(p.nome)
        
        let matchName = ""
        if (importedData[sysName]) {
          matchName = sysName
        } else {
          matchName = csvNames.find(cn => cn.includes(sysName) || sysName.includes(cn)) || ""
          if (matchedCsvNames.has(matchName)) matchName = ""
        }

        if (matchName) {
          const data = importedData[matchName]
          newSalesItems[p.id] = data.qty
          newSalesPrices[p.id] = data.total / data.qty
          matchedCount++
          matchedCsvNames.add(matchName)
        }
      })

      csvNames.forEach(cn => {
        if (!matchedCsvNames.has(cn)) notFoundNames.push(cn)
      })

      setSalesItems(newSalesItems)
      setSalesPrices(newSalesPrices)
      
      let msg = `Importação concluída!\n\n✅ ${matchedCount} produtos vinculados.`
      if (notFoundNames.length > 0) {
        msg += `\n\n⚠️ ${notFoundNames.length} itens do CSV não vinculados (apenas exibindo os 5 primeiros):\n- ${notFoundNames.slice(0, 5).join('\n- ')}`
      }
      
      alert(msg)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }

    reader.readAsText(file, 'ISO-8859-1')
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
      await axios.post(`${API_URL}/vendas/bulk`, { vendas: items })
      
      let totalVenda = 0
      let totalCusto = 0
      items.forEach(it => {
        const p = produtos.find(prod => prod.id === it.produto_id)
        totalVenda += it.quantidade * it.preco_venda
        totalCusto += it.quantidade * p.custo
      })
      const margem = totalVenda > 0 ? (totalVenda - totalCusto) / totalVenda : 0
      
      setSummary({
        data: new Date().toLocaleDateString('pt-BR'),
        venda: totalVenda,
        margem: (margem * 100).toFixed(1),
        itens: items.map(it => ({
          nome: produtos.find(p => p.id === it.produto_id).nome,
          qtd: it.quantidade,
          preco: it.preco_venda
        }))
      })
      
      alert("Vendas registradas com sucesso!")
    } catch (err) {
      alert("Erro ao salvar vendas.")
    } finally {
      setSubmitting(false)
    }
  }

  const copyToWhatsApp = () => {
    const text = `📊 *Fechamento do Dia - ${summary.data}*\n\n` +
      `💰 Total Vendido: R$ ${summary.venda.toFixed(2)}\n` +
      `🎯 Margem Média: ${summary.margem}%\n\n` +
      `*Produtos:*\n` +
      summary.itens.map((it: any) => `- ${it.nome}: ${it.qtd.toFixed(3)} x R$ ${it.preco.toFixed(2)}`).join('\n')
    
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    alert("Relatório copiado para o WhatsApp!")
  }

  if (summary) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <div className="bg-white p-8 rounded-3xl border-4 border-emerald-500 shadow-2xl relative transition-all animate-in fade-in zoom-in duration-500">
          <div className="absolute -top-4 -right-4 bg-emerald-500 text-white p-2 rounded-xl">
             <Check size={24} />
          </div>
          <h2 className="text-2xl font-black text-center mb-8">RELATÓRIO DE FECHAMENTO</h2>
          <div className="space-y-6">
            <div className="flex justify-between border-b pb-4">
              <span className="text-slate-500 font-medium">Data</span>
              <span className="font-extrabold">{summary.data}</span>
            </div>
            <div className="flex justify-between border-b pb-4">
              <span className="text-slate-500 font-medium">Total Vendido (Gross)</span>
              <span className="font-extrabold text-xl">R$ {summary.venda.toFixed(2)}</span>
            </div>
            <div className="flex justify-between border-b pb-4">
              <span className="text-slate-500 font-medium">Margem Média do Dia</span>
              <span className="font-black text-emerald-600">{summary.margem}%</span>
            </div>
          </div>

          <div className="mt-12 flex flex-col sm:flex-row gap-4">
            <button 
              onClick={copyToWhatsApp}
              className="flex-1 bg-emerald-600 text-white font-bold py-4 rounded-xl flex items-center justify-center gap-2 hover:bg-emerald-700 shadow-lg shadow-emerald-600/20 transition-all active:scale-95"
            >
               <Copy size={18} /> {copied ? 'Copiado!' : 'Copiar para WhatsApp'}
            </button>
            <button 
              onClick={() => { setSummary(null); setSalesItems({}); setSalesPrices({}); }}
              className="flex-1 bg-slate-100 text-slate-600 font-bold py-4 rounded-xl hover:bg-slate-200 transition-all active:scale-95"
            >
              Novo Lançamento
            </button>
          </div>
        </div>
      </div>
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
          <input 
            type="file" 
            accept=".csv" 
            ref={fileInputRef} 
            onChange={handleImportCSV} 
            className="hidden" 
          />
          <button 
            onClick={() => fileInputRef.current?.click()}
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
                result.status === 'SAUDÁVEL' ? 'bg-emerald-50 border-emerald-100 text-emerald-600' : 'bg-rose-50 border-rose-100 text-rose-600'
              }`}>
                 Status: {result.status}
              </div>
              <p className="text-xs text-slate-500 leading-relaxed italic">
                * Este cálculo considera que todos os faturamentos seriam afetados pela nova regra de margem.
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

export default App
