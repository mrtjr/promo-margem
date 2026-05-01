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

### 💧 DFC + DMPL · *novo em v0.13*
Dois demonstrativos contábeis derivados **on-demand** do BP + DRE — não persistem, sempre consistentes com o estado atual:
- **DFC (Fluxos de Caixa)** método indireto (Lei 6.404/76 art. 188, CPC 03 R2): parte do Lucro Líquido e ajusta pelas variações patrimoniais entre o BP do mês N e N-1. Estrutura em 3 atividades (Operacional, Investimento, Financiamento). **Reconciliação automática**: variação calculada vs variação real (caixa final − caixa inicial), com flag se diferença > R$ 0,01.
- **DMPL (Mutações do PL)** matriz `componente × movimentação`: Capital Social, Reservas, Lucros Acumulados, redutoras (Prejuízos Acumulados, Ações em Tesouraria) — coluna LL ligada direto ao DRE; o resto vai em "Outras movimentações" (catch-all). Validação de fechamento: total do DMPL bate com `bp.total_patrimonio_liquido`.
- 3 endpoints REST: `GET /dfc?mes=YYYY-MM`, `GET /dfc/comparativo?meses=N`, `GET /dmpl?mes=YYYY-MM`.
- 2 páginas frontend (`Financeiro → DFC` e `→ DMPL`) com seletor de mês, KPIs, tabela cascata, comparativo de 6 meses (DFC), e indicador de fechamento (DMPL).

### 🪄 Engine de Promoção orientado a meta · *novo em v0.12*
Inverte o simulador: você informa a **meta de margem semanal** e o engine propõe **3 cestas rankeadas** (conservador, balanceado, agressivo) com SKUs, descontos sugeridos, projeções e risco de stockout — pronto pra aprovar.

- **Elasticidade-preço por SKU** — regressão log-log sobre `VendaDiariaSKU` (90 dias). Quando dados são insuficientes (CV de preço <3% ou <10 obs), cai num **prior por classe ABC-XYZ** (de -0,8 para A-X até -2,2 para C-Z). Cache em `ElasticidadeSKU` com TTL 7d, recalculado no startup.
- **Solver greedy multi-perfil** — para cada (SKU, nível de desconto), avalia contribuição marginal de lucro × risco de stockout × restrições de margem. Adiciona em ordem decrescente de score até atingir meta global. Sem dependências externas (numpy/pulp/ortools).
- **3 perfis distintos**:
  - **Conservador** maximiza lucro com `desconto_max=10%`
  - **Balanceado** maximiza lucro irrestrito (default)
  - **Agressivo** maximiza volume (sacrifica até 1pp de margem)
- **Restrições do solver**:
  - `desconto ≤ teto do grupo` (`Grupo.desconto_maximo_permitido`)
  - `margem_pos_acao ≥ 5%` (piso técnico)
  - `risco_stockout < 30%` (≥30% bloqueia o SKU; 15-30% = flag amarela)
  - SKU não está em `Promocao(ativa)` cobrindo hoje
  - SKU não tem `produtos.bloqueado_engine=TRUE` (**blacklist** editável por SKU na tela Produtos)
- **Janela ideal heurística** — 7 dias default; estende a 14d se cobertura >14d (escoar encalhado); reduz a 3d se forecast com confiança baixa.
- **Lifecycle**: `proposta → aprovada (cria Promocao rascunho) | descartada (manual) | expirada (24h+)`. Aprovar uma cesta automaticamente descarta as outras 2 do mesmo run. Auditoria completa em `cestas_promocao` + `cesta_itens`.
- **UI** — aba "Engine" no Simulador + entrada de menu **Promo Inteligente** (atalho). 3 cards lado-a-lado com KPIs (margem proj, lucro semanal, SKUs, desconto médio); drawer expansível com cada SKU mostrando β, qualidade da elasticidade, cobertura pós-promo, risco. Toggle de blacklist no modal de edição de produto.

### 💀 Quebras e Perdas · *novo em v0.11*
Tipo de movimentação dedicado para perdas de estoque, separado de venda:
- **4 motivos** padronizados — `vencimento`, `avaria`, `desvio`, `doacao` — validados por CHECK constraint no banco.
- **Custo congelado no momento** — `custo_unitario` da `Movimentacao` recebe o CMP atual; reversão recalcula CMP a partir das ENTRADAs remanescentes (espelho de `excluir_entrada`).
- **Não polui demanda** — quebra reduz estoque mas **não** cria `Venda` nem `VendaDiariaSKU`, mantendo forecast e ABC-XYZ limpos.
- **Linha 4.2 do DRE** — `Lucro Bruto = Receita Líquida − CMV − Quebras` com conta contábil dedicada (`4.2 Quebras e Perdas de Estoque`, tipo CMV/DEBITO).
- **UI dedicada** — formulário rápido (busca produto → qtd → motivo cartão), histórico filtrável, KPIs do mês (valor perdido, % faturamento vs benchmark ABRAS 1,5–2%, top 5 produtos com mais perda).
- **Bulk transacional** — endpoint `/quebras/bulk` aceita lote com rollback total em qualquer falha.
- **Dashboard** — KPI "Quebras (mês)" com semáforo verde <1,5% / âmbar 1,5–2% / vermelho >2%.

### 🧾 Balanço Patrimonial (BP) · *novo em v0.10*
Módulo completo de BP mensal seguindo **Lei 6.404/76 art. 178 + CPC 26 (R1) + NBC TG 26 (R4)**:
- **~65 campos** organizados em Ativo Circulante, Realizável a Longo Prazo, Investimentos, Imobilizado, Intangível, Passivo Circulante, Passivo Não Circulante e Patrimônio Líquido.
- **Contas redutoras** armazenadas em positivo e subtraídas no cálculo (depreciação acumulada, amortização acumulada, prejuízos acumulados, ações em tesouraria).
- **Equação fundamental** `ATIVO = PASSIVO + PL` validada a cada save (tolerância 0,01).
- **Ciclo de vida** — `rascunho → fechado → auditado` (estado auditado é imutável).
- **7 indicadores** automáticos — Liquidez Corrente/Seca/Imediata, Endividamento Geral, Composição do Endividamento, Imobilização do PL, Capital de Giro Líquido.
- **Comparativo histórico** — série de 12 meses.
- **UI com 6 abas** — Resumo, Ativo, Passivo, PL, Indicadores, Histórico.

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
│           ├── bp_service.py                # balanço patrimonial + indicadores
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
| `m_006_balanco_patrimonial` | Cria tabela `balanco_patrimonial` (~65 campos + metadata + CHECK status) |

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

### Balanço Patrimonial
| Método | Rota | Descrição |
|---|---|---|
| GET | `/bp?mes=YYYY-MM` | Retorna BP do mês (auto-cria rascunho) |
| GET | `/bp/listar?ano=YYYY` | Listagem compacta de todos os BPs do ano |
| GET | `/bp/comparativo?ate=...&meses=12` | Série histórica para gráfico |
| GET | `/bp/indicadores?mes=...` | 7 indicadores financeiros calculados |
| POST | `/bp` | Upsert do rascunho (totais recalculados pelo backend) |
| POST | `/bp/fechar?mes=...` | Valida balanceamento e fecha o BP |
| POST | `/bp/auditar?mes=...` | Marca como auditado (estado imutável) |
| POST | `/bp/reabrir?mes=...` | Reabre BP fechado para rascunho |
| DELETE | `/bp/{bp_id}` | Exclui BP (somente rascunho) |

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
| `balanco_patrimonial` | BP mensal (~65 campos + totais + status + indicadores) |
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
- [x] **Fase 10** — Balanço Patrimonial (BP) mensal + indicadores + ciclo rascunho/fechado/auditado
- [x] **Fase 11** — Quebras/Perdas como tipo de movimentação + linha 4.2 do DRE
- [x] **Fase 12** — Engine de promoção orientada a meta (solver inverso + elasticidade + 3 perfis + blacklist)
- [x] **Fase 13** — DFC (Demonstração dos Fluxos de Caixa) + DMPL (Mutações do PL) ligadas ao BP
- [ ] **Fase 14** — Integração PDV/ERP via webhook (config pronta; falta validação em produção)

---

## Princípios de projeto

- **Audit log first** — `Movimentacao` é a fonte de verdade. Estoque, CMP e agregados são derivados *recalculáveis*.
- **Idempotência onde possível** — re-importar CSV, reconciliar, reaplicar migrações = mesmo resultado.
- **Fail safe sobre dados sujos** — produto sem custo bloqueia importação; CHECK constraints evitam corrupção; soft-delete preserva referências.
- **Nada de magic** — sem Alembic, sem ORMs no frontend. Raw SQL onde melhora legibilidade.

---

## Releases

Histórico de versões publicadas. Cada release tem tag `vX.Y.Z` no GitHub e nota de release detalhada em [Releases](../../releases).

### v0.12.1 — Manutenção P0/P1/P2/P3 · *2026-05-01*
> Apertando os parafusos: 7 bugs reais corrigidos, performance do solver, +23 cenários de teste E2E, dead code removido, API consistente, frontend tipado, DevOps endurecido. Zero feature nova.

**🔴 P0 — Bugs reais (silent failures)**
- `PATCH /produtos/{id}` agora persiste `bloqueado_engine` (toggle de blacklist do Engine estava silenciosamente quebrado).
- Aprovar cesta no Engine não re-roda mais o solver (cada clique antes criava 3 cestas órfãs).
- Dashboard `/stats` busca só no mount (antes refazia em todo page change → 30+ requests/sessão).
- Startup não destrói mais grupos com nomes diferentes do hardcoded; `seed_grupos_padrao` é idempotente e NÃO destrutivo.
- Fallback `grupo_id=1` substituído por `_primeiro_grupo_id()` dinâmico.
- `@app.on_event("startup")` migrado para `lifespan` context manager.
- 5× Pydantic v1 `.dict()` substituídos por `.model_dump()`.

**🟡 P1 — Performance**
- Solver Engine: cache de `produtos_all` reduz **~6N+15 queries → 1** por `/propor`.
- `_recalcular_produto_do_zero`: 3 queries → 1 com `tipo.in_(...)`.
- Migration `m_009_indices_performance`: índices compostos `(produto_id, data DESC)` em `movimentacoes` e `vendas`.
- Bench documentado em `bench_p1_perf.py`.

**🟠 P2 — Testes (4 suítes novas, 23 cenários)**
- `test_csv_fechamento_e2e.py` — caminho mais crítico do produto (parse + match + idempotência) cobrindo 750 linhas de service.
- `test_bp_e2e.py` — equação fundamental, redutoras, ciclo de vida, indicadores.
- `test_estoque_reversao_e2e.py` — `excluir_entrada` / `excluir_venda` (CMP recalc, orfanização, isolamento por dia).
- `test_forecast_e2e.py` — cascata de confianças + DoW factor.

**🟤 P3 — Cleanup**
- `Movimentacao.peso_medida` (campo legado) removido. Migration `m_010_drop_peso_medida` aplica `DROP COLUMN`.
- Import órfão `from sqlalchemy import and_` removido.

**🟣 P3 — API consistente**
- `BulkOperationResponse {ok, registradas, total, erros}` padroniza `/entradas/bulk` e `/vendas/bulk`.
- `SimulacaoPorGrupoResponse` adiciona schema ao `/simular/grupo`.
- `registrar_entrada_bulk` deixa de ser `async` desnecessário.

**🟢 P3 — Frontend hygiene**
- `src/types.ts` com `Produto`, `Grupo`, `Stats` canônicos.
- 9 `useState<any>` quentes tipados (TS pegou bug latente em `RelatoriosPage`: `produtos.find()` podia retornar `undefined`).
- `VITE_API_URL` env var com fallback `/api` + `vite-env.d.ts` + `.env.example`.
- Componente `<Confirm>` reutilizável substitui 3 `confirm()` nativos (Reconciliar / Excluir lançamento / Salvar antes de fechar BP).

**⚪ P3 — DevOps**
- `.dockerignore` em 3 níveis — build context limpo (corte ~200MB de `node_modules` no frontend).
- `CORSMiddleware` com env var `CORS_ORIGINS` — destrava `npm run dev` falando com backend em porta separada.
- Endpoint `GET /health` (DB check + 503 quando DB down).
- Healthchecks no `docker-compose.yml` (`pg_isready` + `service_healthy`).
- Lazy-load de `OPENROUTER_API_KEY` (era avaliado no import → setar a var depois do startup não tinha efeito).

**Validação final**
- 8 suítes E2E verdes (54+ cenários) — zero regressão.
- `tsc --noEmit` exit 0; `vite build` exit 0.
- Migrations m_007–m_010 aplicadas idempotentemente em PostgreSQL.

### v0.13.0 — DFC + DMPL · *2026-05-01*
> Dois demonstrativos contábeis derivados on-demand do BP + DRE: Fluxos de Caixa (método indireto) e Mutações do Patrimônio Líquido. Sem persistir snapshot, sempre consistentes.

**Adicionado**
- 💧 `dfc_service.py` (~270 linhas) — DFC método indireto, 3 atividades (Operacional, Investimento, Financiamento), reconciliação automática com variação real de caixa.
- 📊 `dmpl_service.py` (~150 linhas) — matriz `componente × mutação` com 7 componentes do PL; validação de fechamento contra `bp.total_patrimonio_liquido`.
- 🔌 3 endpoints REST: `GET /dfc?mes=YYYY-MM`, `GET /dfc/comparativo?meses=N`, `GET /dmpl?mes=YYYY-MM`.
- 🖼️ 2 páginas frontend (`Financeiro → DFC`, `Financeiro → DMPL`) com seletor de mês, KPIs, tabela cascata, comparativo histórico de 6 meses (DFC), indicador de fechamento (DMPL).
- 🧪 9 cenários E2E (`test_dfc_e2e.py` 5 + `test_dmpl_e2e.py` 4) cobrindo BP ausente, reconciliação OK, compra de imobilizado em Investimento, empréstimo em Financiamento, depreciação em Operacional, aumento de capital, fechamento contra PL e redutoras com sinal negativo.

**Garantias**
- Cálculo derivado on-demand: nenhuma persistência. Mudança em BP/DRE reflete imediatamente.
- DFC exige BP do mês N e N-1; DMPL aceita N-1 ausente (saldo inicial = 0).
- Reconciliação DFC: se |variação calculada − variação real| > R$ 0,01, sinaliza `reconciliacao_ok=false` (informativo, não bloqueia).
- DMPL fechamento: soma final por componente bate com `bp.total_patrimonio_liquido` na tolerância 0,01.

### v0.12.0 — Engine de Promoção orientada a meta · *2026-04-25*
> Solver inverso: meta de margem semanal → 3 cestas de SKUs com desconto, projeção e risco de stockout. Tudo aprovável em 1 clique.

**Adicionado**
- 🪄 `engine_promocao_service` (~570 linhas) — solver greedy multi-perfil (conservador / balanceado / agressivo).
- 📈 `elasticidade_service` — regressão log-log sobre `VendaDiariaSKU` com fallback bayesiano por classe ABC-XYZ. Cache em `ElasticidadeSKU` com TTL 7d.
- 🚫 Coluna `produtos.bloqueado_engine` (BOOLEAN) — **blacklist** editável SKU a SKU na tela Produtos.
- 🗃️ Tabelas `cestas_promocao` + `cesta_itens` — propostas persistidas com status `proposta → aprovada | descartada | expirada`.
- 🔌 7 endpoints REST: `POST /promocoes/engine/propor`, `GET /promocoes/engine/propostas`, `GET /promocoes/engine/propostas/{id}`, `POST /promocoes/engine/aprovar/{id}`, `POST /promocoes/engine/descartar/{id}`, `GET /promocoes/engine/elasticidades`, `POST /admin/recalcular-elasticidades`.
- 🖼️ Aba **Engine** no Simulador + entrada de menu **Promo Inteligente** (atalho). 3 cards de cesta com KPIs e drawer expansível por SKU mostrando β, qualidade da elasticidade, cobertura pós-promo, risco de stockout.
- 🔒 Toggle "Excluir do Engine de Promoção" no modal de edição de produto + ícone de cadeado na listagem de SKUs blacklistados.
- ⚙️ Recálculo automático de elasticidades no startup (respeita TTL); auto-expiração de propostas com >24h.
- 📜 Migração idempotente `m_008_engine_promocao` cria 3 tabelas, coluna blacklist, índices e CHECK constraints (qualidade, fonte, status, perfil, beta clamped).
- 🧪 8 cenários de teste E2E (`test_engine_promocao_e2e.py`): regressão de elasticidade, fallback no prior, meta respeitada, descarte por stockout, blacklist + teto, aprovar→Promocao, perfis distintos, meta inalcançável.

**Garantias**
- Solver não inventa nada — reaproveita `forecast_service`, `analise_service`, `recomendacao_service`, `margin_engine` (1 ponto de verdade pra margem global).
- `Lucro Bruto` continua respeitando `Receita Líquida − CMV − Quebras` no DRE; engine apenas projeta lucro futuro de promoção, não altera DRE atual.
- Aprovar cesta cria `Promocao(rascunho)` — não publica automaticamente. Usuário ainda passa pelo `POST /promocoes/{id}/publicar` antes da promoção entrar em vigor.
- Descartar uma cesta não cria efeito colateral; aprovação é idempotente (chamar 2x retorna mesma `Promocao`).
- Sem dependências novas: regressão linear em Python puro, sem `numpy`/`scipy`/`pulp`/`ortools`.
- Backend é fonte única de verdade para β e cestas; cliente nunca calcula nada — só renderiza.

### v0.11.0 — Quebras e Perdas · *2026-04-25*
> Tipo de movimentação dedicado para perdas de estoque, integrado ao DRE como linha 4.2 — sem contaminar histórico de demanda.

**Adicionado**
- 💀 `Movimentacao.tipo='QUEBRA'` com coluna `motivo` (vencimento / avaria / desvio / doacao) protegida por CHECK constraint.
- 📋 `quebra_service` completo — `registrar_quebra`, `registrar_quebra_bulk` (transacional), `excluir_quebra`, `listar_quebras`, `resumo_mes`, `total_quebras_mes`.
- 🔌 5 endpoints REST — `POST /quebras`, `POST /quebras/bulk`, `GET /quebras`, `GET /quebras/resumo`, `DELETE /quebras/{id}`.
- 📒 Conta contábil `4.2 Quebras e Perdas de Estoque` (tipo CMV / DEBITO) seedada no plano de contas padrão.
- 🧮 DRE: nova linha 4.2 entre CMV e Lucro Bruto. `Lucro Bruto = Receita Líquida − CMV − Quebras`.
- 📊 `DREMensal.quebras` persistido no snapshot mensal.
- 🖼️ Página `/quebras` no frontend — formulário (busca produto, qtd, peso opcional, 4 cartões de motivo) + histórico com filtros + 4 KPIs mensais + top 5 produtos.
- 🎯 KPI "Quebras (mês)" no Dashboard com semáforo (benchmark ABRAS 1,5–2%).
- 📜 Histórico de Movimentações ganhou filtro/badge/exclusão para tipo QUEBRA.
- 📜 Migração idempotente `m_007_movimentacao_quebra` adiciona coluna, 3 CHECK constraints, índice `ix_mov_tipo_data`, conta 4.2 e `dre_mensal.quebras`.
- 🧪 7 cenários de teste E2E (`test_quebra_e2e.py`) cobrindo registro, validações, isolamento da demanda, DRE, reversão, bulk transacional, resumo.

**Garantias**
- QUEBRA reduz `estoque_qtd` e `estoque_peso`, mas **não** cria `Venda` nem `VendaDiariaSKU` → forecast e ABC-XYZ permanecem íntegros.
- `custo_unitario` é congelado no momento da quebra (CMP atual) → DRE soma direto do log sem recálculo.
- Reversão (`excluir_quebra`) é espelho exato de `excluir_entrada`: deleta movimentação, recalcula estoque/CMP a partir do log restante, reativa produto se necessário.
- CMP não muda quando há QUEBRA — só ENTRADAs alimentam a média ponderada.

### v0.10.0 — Balanço Patrimonial · *2026-04-25*
> Módulo contábil completo de BP mensal seguindo padrões brasileiros (Lei 6.404/76 + CPC 26).

**Adicionado**
- 🧾 Tabela `balanco_patrimonial` com ~65 campos (Ativo Circulante, Realizável LP, Investimentos, Imobilizado, Intangível, Passivo Circulante, Passivo Não Circulante, PL).
- 🔢 Recálculo automático de totais e validação `ATIVO = PASSIVO + PL` (tolerância 0,01).
- ♻️ Ciclo de vida `rascunho → fechado → auditado` com estados imutáveis após auditoria.
- 📐 7 indicadores financeiros automáticos (Liquidez Corrente/Seca/Imediata, Endividamento Geral, Composição Endividamento, Imobilização do PL, Capital de Giro Líquido).
- 📈 Comparativo histórico de 12 meses + listagem por ano.
- 🖼️ UI no Financeiro com 6 abas (Resumo, Ativo, Passivo, PL, Indicadores, Histórico).
- 🛠️ 9 endpoints REST (`/bp`, `/bp/listar`, `/bp/comparativo`, `/bp/indicadores`, `/bp/fechar`, `/bp/auditar`, `/bp/reabrir`, `DELETE /bp/{id}`).
- 📜 Migração idempotente `m_006_balanco_patrimonial`.

**Convenções**
- Contas redutoras (depreciação, amortização, prejuízos, ações em tesouraria) gravadas em **positivo** e subtraídas pelo motor — frontend exibe com sinal negativo.
- Backend é **fonte única de verdade** para totais — valores enviados pelo cliente são ignorados e recalculados.

### v0.9.x — Estabilização do CSV
- `fix(fechamento-csv)`: re-import idempotente com ENTRADA-espelho preservada
- `fix(fechamento-csv)`: tratamento definitivo de produtos sem custo
- `fix(fechamento)`: matching CSV ignora produtos soft-deleted

### v0.9.0 — DRE + Promoções + Histórico
- Cascata DRE mensal com Simples Nacional 8%
- Ciclo de vida de promoções (rascunho → publicada → encerrada)
- Histórico unificado de movimentações com exclusão reversível
- Reconciliação global a partir do audit log

### v0.8.x e anteriores
Fases 1-7: setup, importação produtos/grupos, dashboard, simulador, engine de recomendação + IA, fechamento via CSV (preview/commit), exclusão reversível.

---

## Licença

MIT — uso livre para fins comerciais.
