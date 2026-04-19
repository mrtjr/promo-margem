# 🎯 PromoMargem

> Sistema inteligente de precificação, promoção e controle de margem para empresas de **atacado e varejo**.

---

## 📌 Visão Geral

Empresa com faturamento de R$400k–R$600k/mês, mix de 300–500 SKUs e margens variadas entre 7% e +30%. O sistema automatiza o controle de margem por grupo de produto, simula cenários de promoção agressiva e garante que a margem média semanal fique entre **17–19%** e o fechamento mensal em **18%**.

---

## 🎯 Metas de Negócio

| Indicador | Meta |
|---|---|
| Margem média semanal | 17% – 19% |
| Margem no fechamento mensal | 18% |
| Grupos de produto (margem baixa) | 7% – 12% |
| Grupos de produto (margem média) | 20% – 26% |
| Grupos de produto (margem alta) | > 30% |
| Mix de SKUs | 300 – 500 |
| Faturamento mensal | R$400k – R$600k |

---

## 🗂️ Módulos do MVP

### 1. Dashboard de Margem
- Margem atual (dia, semana, mês)
- Alertas automáticos de desvio da meta
- Agrupamento de SKUs por faixa de margem

### 2. Simulador de Promoção
- Selecione grupo de produto ou SKUs individuais
- Defina % de desconto e quantidade limite
- Visualize impacto na margem média antes de publicar

### 3. Sugestão Automática
- Engine sugere promoções seguras por grupo
- Respeita margem mínima configurável por categoria
- Prioriza itens de baixa rotação com margem acima de 10%

### 4. Monitor de Fechamento
- Relatório semanal e mensal automático
- Alertas por WhatsApp ou e-mail se margem desviar
- Exportação CSV/PDF para análise externa

---

## 🏗️ Arquitetura

```
promo-margem/
├── frontend/          # React + Vite + TypeScript
│   ├── src/
│   │   ├── pages/     # Dashboard, Simulador, Promoções, Relatórios
│   │   ├── components/
│   │   └── hooks/
├── backend/           # Python + FastAPI
│   ├── app/
│   │   ├── routes/    # /produtos, /grupos, /simulacao, /relatorios
│   │   ├── services/  # margem_engine, promo_engine, alertas
│   │   └── models/
├── database/          # PostgreSQL (scripts de criação)
├── docs/              # PRD, wireframes, decisões de arquitetura
└── docker-compose.yml
```

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Frontend | React 18 + Vite + TypeScript |
| UI | Tailwind CSS + Shadcn/ui |
| Gráficos | Recharts |
| Backend | Python 3.12 + FastAPI |
| Análise | Pandas + NumPy |
| Banco | PostgreSQL 16 |
| ORM | SQLAlchemy + Alembic |
| Infra | Docker + Docker Compose |
| Deploy | Local (servidor HP) ou VPS |

---

## 🚀 Roadmap

- [ ] **Fase 1** — Setup + estrutura base (backend API + banco)
- [ ] **Fase 2** — Importação de produtos e grupos (CSV/manual)
- [ ] **Fase 3** — Dashboard de margem com alertas
- [ ] **Fase 4** — Simulador de promoção
- [ ] **Fase 5** — Engine de sugestão automática
- [ ] **Fase 6** — Relatórios e exportações
- [ ] **Fase 7** — Integração PDV/ERP (CSV/API)

---

## 📄 Licença

MIT — uso livre para fins comerciais.
