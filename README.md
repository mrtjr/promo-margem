# PromoMargem

> Motor de inteligência de margem, projeção e promoção para operações de atacado e varejo.

---

## Visão geral

Empresa com faturamento de R$400k–R$600k/mês, mix de 300–500 SKUs e margens variando de 7% a +30%. O sistema analisa o fechamento do dia, projeta D+1 e recomenda ações comerciais automaticamente, mantendo a margem semanal entre **17–19%** e o fechamento mensal em **18%**.

---

## Funcionalidades

### Núcleo operacional
- **Gestão dual de estoque**: controle simultâneo por volume (UN) e peso (Kg/L), com custo médio ponderado (CMP) recalculado a cada entrada.
- **Entrada rápida via Excel**: CTRL+C / CTRL+V com criação automática de produtos e rateio de grupo.
- **Fechamento via CSV**: parser do relatório analítico `xRelVendaAnalitica2.csv`, soma automática por SKU e cálculo de preço médio ponderado por dia.
- **Histórico de movimentações com exclusão reversível**: ver, auditar e excluir entradas/saídas. A exclusão recalcula estoque, peso e CMP a partir do log — sem estado fantasma.
- **Reconciliação global**: `POST /admin/reconciliar-estoques` recalcula todos os produtos a partir das movimentações; desativa produtos órfãos (sem movimentação e sem venda).

### Inteligência
- **Análise de fechamento**: faturamento/custo/margem do dia, comparativo 7d e 30d, classificação ABC/XYZ, top SKUs, anomalias.
- **Projeção D+1**: forecast por SKU via rolling mean 8d + fator dia-da-semana, consolidado em faturamento e margem previstos.
- **Recomendações por SKU**: ação comercial sugerida (promoção, ajuste pra cima, monitorar, repor urgente) com justificativa, urgência e impacto esperado.
- **Saúde por grupo**: margem real × faixa alvo por categoria (Alimentícios, Temperos, Embalagens, Cereais).
- **Simulador de cesta**: impacto em pontos percentuais de aplicar desconto a N SKUs selecionados.
- **Narrativa do fechamento**: briefing diário gerado por IA (com fallback template) juntando análise + projeção + recomendações.

### Dashboard
- KPIs de margem (dia, semana, mês), faturamento do dia, SKUs totais, rupturas.
- Série histórica com status (seguro / alerta / bloqueado).
- Briefing diário com os próximos movimentos acionáveis.

---

## Arquitetura

```
promo-margem/
├── frontend/          # React 19 + Vite + TypeScript + Tailwind
├── backend/           # FastAPI + SQLAlchemy + PostgreSQL
│   └── app/services/  # margin, estoque, recomendacao, forecast, analise,
│                      # categoria, serie, sugestao
├── docker-compose.yml # db + backend + frontend
└── iniciar.ps1        # script de inicialização rápida
```

Serviços:
- `estoque_service` — entradas, vendas, reversão, reconciliação, CMP.
- `analise_service` — fechamento do dia + ABC/XYZ + anomalias.
- `forecast_service` — projeção D+1 rolling mean + DoW factor.
- `recomendacao_service` — ação comercial por SKU.
- `categoria_service` — saúde de margem por grupo.
- `serie_service` — série temporal de fechamento.
- `sugestao_service` — briefing e chat IA.

---

## Stack

| Camada | Tecnologia |
|---|---|
| Frontend | React 19 · Vite · TypeScript · Tailwind · Lucide |
| Design | Claude Design tokens (Fraunces + JetBrains Mono, paleta cream/coral/sage) |
| Backend | Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy |
| Banco | PostgreSQL 16 |
| Infra | Docker Compose (`promo-margem`) |

---

## Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| GET | `/stats` | KPIs do dashboard |
| GET | `/produtos?incluir_inativos=false` | Lista de SKUs (filtra inativos por padrão) |
| POST | `/entradas/bulk` | Lançamento em lote de entradas |
| POST | `/vendas/bulk` | Fechamento de vendas diárias |
| GET | `/historico/movimentacoes?dias=30&tipo=&produto_id=` | Auditoria unificada |
| DELETE | `/entradas/{id}` | Reverte ENTRADA, recalcula estoque/CMP |
| DELETE | `/vendas/{id}` | Reverte venda, devolve estoque, decrementa agregados |
| POST | `/admin/reconciliar-estoques` | Recalcula todos os produtos e soft-deleta órfãos |
| GET | `/fechamento/analise` | Análise de fechamento + ABC/XYZ |
| GET | `/fechamento/narrativa` | Briefing IA |
| GET | `/projecao/amanha` | Projeção D+1 |
| GET | `/recomendacoes` | Recomendações por SKU |
| POST | `/recomendacoes/simular-cesta` | Simulador de cesta |
| GET | `/categorias/saude` | Saúde por grupo |

---

## Roadmap

- [x] **Fase 1** — Setup e API base
- [x] **Fase 2** — Importação de produtos e grupos
- [x] **Fase 3** — Dashboard de margem e SKUs
- [x] **Fase 4** — Simulador de promoção (cesta)
- [x] **Fase 5** — Engine de recomendação automática + narrativa IA
- [x] **Fase 6** — Fechamento via CSV
- [x] **Fase 7** — Histórico + exclusão reversível + reconciliação
- [ ] **Fase 8** — Integração PDV/ERP via API

---

## Como rodar

1. Docker instalado.
2. `./iniciar.ps1` (ou `docker compose -p promo-margem up -d`).
3. Frontend: <http://localhost:3000> · Backend: <http://localhost:8000>.

---

## Licença

MIT — uso livre para fins comerciais.
