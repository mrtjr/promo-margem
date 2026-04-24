# PromoMargem

> **Motor de inteligência de margem, projeção e promoção** para operações de atacado e varejo.
> De **CSV do PDV** ao **briefing do dia seguinte** — em um único fluxo auditável.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/license-MIT-green)](#licença)

---

## Para quem é

Atacadista/varejista com:

- **Faturamento** R$ 400 mil – R$ 600 mil/mês
- **Mix** 300 a 500 SKUs
- **Margens** dispersas (de 7% a +30%) — algumas categorias contam como prejuízo de fato
- **Meta** margem semanal **17–19%** e fechamento mensal em **18%**

O sistema fecha o dia, projeta o D+1, sugere o que promover e o que repor — sem o gestor precisar abrir planilha.

---

## Funcionalidades

### 🔁 Operação diária
- **Estoque dual** — controle simultâneo por **quantidade (UN)** e **peso (Kg/L)**, com **Custo Médio Ponderado (CMP)** recalculado a cada entrada.
- **Entrada Inteligente** — colar do Excel (CTRL+C/V), criação automática de produtos novos, rateio de grupo, código ERP opcional para matching futuro.
- **Histórico de Movimentações** — ENTRADAS e SAÍDAS unificadas, filtros por tipo/produto/janela, **exclusão reversível** que recalcula estoque + CMP a partir do log.
- **Reconciliação global** (`/admin/reconciliar-tudo`) — recalcula todos os produtos a partir das movimentações e desativa órfãos. Funciona como botão de "verdade canônica".

### 📥 Importação CSV (Fechamento de Vendas)
Pipeline em duas fases — **preview** e **commit** — para o relatório `xRelVendaAnalitica2.csv`:

| Etapa | O que faz |
|---|---|
| **Parse** | Lê o CSV (encoding tolerante), detecta a data alvo, agrupa por SKU, calcula preço médio ponderado por dia |
| **Match em camadas** | 1º código ERP exato → 2º nome normalizado (sem acento/case) → senão **bloqueia para resolução** |
| **Preview** | Mostra cada linha com status: `ok`, `sem_custo`, `pendente_match`, `erro_dado`. Frontend permite **associar/criar/corrigir-custo/ignorar** linha a linha |
| **Commit idempotente** | Substitui fechamento da data se já existe (pede confirmação explícita), gera **par ENTRADA-espelho + SAÍDA** para audit trail balanceado, atualiza `VendaDiariaSKU` e `HistoricoMargem` |

**Garantias**:
- Nenhuma SAÍDA com `custo=0` é gravada (bloqueia importação se algum produto fica sem CMP).
- Re-importar o mesmo dia produz o mesmo estado final (idempotente).
- Entrada manual de estoque **não** é tocada pela substituição.
- Produtos órfãos (custo zerado, sem entrada) são **soft-deleted** e reativados automaticamente quando uma nova ENTRADA estabelece o CMP.

### 🧠 Inteligência de margem
- **Análise de fechamento** — faturamento/custo/margem do dia, comparativos 7d e 30d, classificação **ABC/XYZ**, top SKUs, anomalias.
- **Projeção D+1** — forecast por SKU via *rolling mean 8d* + fator dia-da-semana, consolidado em faturamento e margem previstos.
- **Recomendações por SKU** — ação comercial sugerida (promoção, ajuste pra cima, monitorar, repor urgente) com justificativa, urgência e impacto esperado.
- **Saúde por grupo** — margem real × faixa alvo por categoria (Alimentícios, Temperos, Embalagens, Cereais).
- **Simulador de cesta** — impacto em pontos percentuais de aplicar desconto a N SKUs selecionados.
- **Briefing diário** — narrativa gerada por IA juntando análise + projeção + recomendações (com fallback template determinístico).

### 📊 DRE (Demonstração de Resultados)
- **Cascata mensal** — Receita → CMV → Lucro Bruto → Despesas → **Simples Nacional 8%** → Lucro Líquido.
- **Comparativo histórico** — série de 6/12 meses lado a lado.
- **Lançamentos manuais** — despesas por conta contábil (folha, aluguel, energia, marketing…) com plano de contas pré-populado.
- **Configuração tributária** — regime, alíquota e PIS/COFINS ajustáveis.
- **Fechar mês** — congela DRE, gera snapshot.

### 🎯 Promoções
- Cadastro com período de vigência, SKUs alvo, desconto.
- Estados: **rascunho → publicada → encerrada**.
- Simulador de impacto antes de publicar.

### 🔌 Integração PDV (em construção)
- Tabelas `integracao_pdv_config` e `integracao_pdv_log` prontas.
- Endpoint `POST /webhooks/pdv-vendas` aceita pushes do PDV com idempotência por chave.
- Rotacionar token, listar logs, configurar nome do PDV via UI.

---

## Pipeline de dados

```
┌───────────────┐        ┌─────────────┐
│ CSV (PDV/ERP) │──┐  ┌──│ Excel paste │  ← entradas em lote
└───────────────┘  │  │  └─────────────┘
                   ▼  ▼
        ┌──────────────────────────┐
        │  Movimentacao (audit)    │  ENTRADA / SAIDA
        │  Venda + VendaDiariaSKU  │  fonte de verdade
        └──────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
  ┌──────────┐         ┌──────────────┐
  │ Estoque  │         │ Análise +    │
  │ + CMP    │         │ Forecast +   │
  └──────────┘         │ Recomendação │
                       └──────┬───────┘
                              ▼
                       ┌──────────────┐
                       │ Briefing IA  │
                       │ + DRE mensal │
                       └──────────────┘
```

A `Movimentacao` é o **audit log** — toda exclusão é reversível e o estoque é sempre **recalculável** a partir do log.

---

## Stack

| Camada | Tecnologia |
|---|---|
| **Frontend** | React 19 · Vite · TypeScript · Tailwind CSS · Lucide |
| **Design** | Claude Design tokens (Fraunces + JetBrains Mono · paleta cream/coral/sage) |
| **Backend** | Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy |
| **Banco** | PostgreSQL 16 |
| **IA** | Claude (Anthropic) — via prompt nativo, com fallback template |
| **Infra** | Docker Compose (`promo-margem`) |

---

## Arquitetura

```
promo-margem/
├── frontend/                      # React 19 + Vite + Tailwind
│   └── src/App.tsx                # SPA single-file (modais, dashboard, importer)
│
├── backend/
│   └── app/
│       ├── main.py                # rotas FastAPI
│       ├── models.py              # SQLAlchemy
│       ├── schemas.py             # Pydantic
│       ├── database.py            # engine + Session
│       ├── migrations.py          # ALTER TABLE idempotentes
│       └── services/
│           ├── estoque_service.py          # entradas, vendas, reversão, CMP
│           ├── fechamento_csv_service.py   # parser + preview + commit idempotente
│           ├── analise_service.py          # fechamento + ABC/XYZ + anomalias
│           ├── forecast_service.py         # rolling mean 8d + DoW factor
│           ├── recomendacao_service.py     # ação por SKU
│           ├── categoria_service.py        # saúde por grupo
│           ├── serie_service.py            # série temporal de margem
│           ├── sugestao_service.py         # briefing IA + chat
│           ├── promocao_service.py         # ciclo de vida da promoção
│           ├── dre_service.py              # cascata mensal + simples
│           ├── pdv_service.py              # webhook + idempotência PDV
│           └── margin_engine.py            # núcleo do cálculo de margem
│
├── docker-compose.yml             # db + backend + frontend
└── iniciar.ps1                    # bootstrap rápido (Windows)
```

### Migrações
`backend/app/migrations.py` aplica **raw SQL idempotente** no startup (Alembic-free). Cada migração checa o estado antes de alterar:

| Migração | Faz |
|---|---|
| `m_001_venda_data_fechamento` | Adiciona `vendas.data_fechamento` e backfilla |
| `m_002_integracao_pdv_tabelas` | Garante tabelas `integracao_pdv_*` |
| `m_003_produto_codigo` | Adiciona `produtos.codigo` (UNIQUE parcial) |
| `m_004_soft_delete_produtos_custo_zero` | Soft-delete de produtos órfãos pré-validação |
| `m_005_produto_custo_nonneg` | CHECK CONSTRAINT `custo >= 0` |

---

## Endpoints principais

### Dashboard & análise
| Método | Rota | Descrição |
|---|---|---|
| GET | `/stats` | KPIs do dashboard |
| GET | `/margem/serie` | Série histórica de margem (dia/semana/mês) |
| GET | `/fechamento/analise` | Análise de fechamento + ABC/XYZ |
| GET | `/fechamento/narrativa` | Briefing IA do dia |
| GET | `/projecao/amanha` | Projeção D+1 |
| GET | `/recomendacoes` | Recomendações por SKU |
| GET | `/recomendacoes/simular-cesta` | Simulador de desconto em cesta |
| GET | `/categorias/saude` | Margem real × alvo por grupo |
| GET | `/sugestao/por-grupo` · `/sugestao/resumo` | Recomendações agregadas |

### Operação
| Método | Rota | Descrição |
|---|---|---|
| GET | `/produtos?incluir_inativos=false` | Lista de SKUs |
| GET | `/grupos` | Grupos / categorias |
| POST | `/entradas/bulk` | Lançamento em lote (Entrada Inteligente) |
| POST | `/vendas/bulk` | Fechamento manual de vendas |
| POST | `/fechamento/importar-csv/preview` | Parse + match + classificação por linha |
| POST | `/fechamento/importar-csv/commit` | Aplica resoluções, gera vendas + audit trail |
| GET | `/historico/movimentacoes` | Auditoria unificada (ENTRADAS + SAÍDAS) |
| DELETE | `/entradas/{id}` · `/vendas/{id}` | Reversão com recálculo de estoque/CMP |
| POST | `/admin/reconciliar-estoques` · `/admin/reconciliar-agregados` · `/admin/reconciliar-tudo` | Recalcula tudo do log |

### DRE & tributário
| Método | Rota | Descrição |
|---|---|---|
| GET | `/dre?ano=&mes=` | Cascata do mês |
| GET | `/dre/comparativo?meses=12` | Série comparativa |
| POST | `/dre/fechar` | Fecha o mês (snapshot) |
| GET / POST / DELETE | `/despesas` | Lançamentos manuais |
| GET | `/contas` | Plano de contas |
| GET / PUT | `/tributario` | Regime + alíquota |

### Promoções
| Método | Rota | Descrição |
|---|---|---|
| GET / POST | `/promocoes` | Listar / criar |
| POST | `/promocoes/{id}/publicar` · `/encerrar` | Mudança de estado |
| POST | `/simular/grupo` | Simular desconto em grupo |

### PDV
| Método | Rota | Descrição |
|---|---|---|
| GET / PUT | `/pdv/config` | Config + token |
| POST | `/pdv/rotacionar-token` | Rotaciona token de acesso |
| GET | `/pdv/logs` | Histórico de pushes |
| POST | `/webhooks/pdv-vendas` | Endpoint do PDV (idempotente) |

---

## Modelo de dados (essencial)

| Tabela | Papel |
|---|---|
| `produtos` | SKU + código ERP (opcional) + custo + estoque dual + grupo |
| `grupos` | Categorias com faixa de margem alvo |
| `movimentacoes` | Audit log (ENTRADA/SAIDA) — fonte para recalculo |
| `vendas` | Vendas individuais com data + data_fechamento |
| `vendas_diarias_sku` | Agregado diário por produto (cache de forecast) |
| `historico_margem` | Snapshot por dia/semana/mês |
| `promocoes` | Promoções + SKUs alvo |
| `dre_lancamento` · `dre_conta` · `dre_config_tributaria` | DRE |
| `integracao_pdv_config` · `integracao_pdv_log` | Webhook PDV |

---

## Setup rápido

### Pré-requisitos
- Docker Desktop instalado e rodando

### Subir tudo
```powershell
# Windows
.\iniciar.ps1
```
```bash
# Linux/Mac
docker compose -p promo-margem up -d
```

### URLs
- **Frontend**: <http://localhost:3000>
- **Backend (Swagger)**: <http://localhost:8000/docs>
- **Postgres**: `localhost:5432` (db `promomargem`)

### Logs
```bash
docker compose -p promo-margem logs -f backend
```

### Reset completo (cuidado)
```bash
docker compose -p promo-margem down -v   # apaga volume do Postgres
```

---

## Roadmap

- [x] **Fase 1** — Setup e API base
- [x] **Fase 2** — Importação de produtos e grupos
- [x] **Fase 3** — Dashboard de margem e SKUs
- [x] **Fase 4** — Simulador de promoção (cesta)
- [x] **Fase 5** — Engine de recomendação automática + narrativa IA
- [x] **Fase 6** — Fechamento via CSV (preview/commit, idempotente)
- [x] **Fase 7** — Histórico + exclusão reversível + reconciliação
- [x] **Fase 8** — DRE mensal + Simples Nacional
- [x] **Fase 9** — Promoções (ciclo de vida + simulação)
- [ ] **Fase 10** — Integração PDV/ERP via webhook (config pronta; falta validação em produção)
- [ ] **Fase 11** — Engine de promoção automática (gatilhos por margem/giro)

---

## Princípios de projeto

- **Audit log first** — `Movimentacao` é a fonte de verdade. Estoque, CMP e agregados são derivados *recalculáveis*.
- **Idempotência onde possível** — re-importar CSV, reconciliar, reaplicar migrações = mesmo resultado.
- **Fail safe sobre dados sujos** — produto sem custo bloqueia importação; CHECK constraints evitam corrupção; soft-delete preserva referências.
- **Nada de magic** — sem Alembic, sem ORMs no frontend. Raw SQL onde melhora legibilidade.

---

## Licença

MIT — uso livre para fins comerciais.
