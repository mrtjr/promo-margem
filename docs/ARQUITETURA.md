# Arquitetura — PromoMargem

## Visão Geral

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                 │
│         React 18 + Vite + TypeScript + Tailwind                 │
│   Dashboard │ Simulador │ Promoções │ Sugestões │ Relatórios    │
└───────────────────────┬─────────────────────────────────────────┘
                        │ REST API (HTTP/JSON)
┌───────────────────────▼─────────────────────────────────────────┐
│                        BACKEND                                  │
│              Python 3.12 + FastAPI                              │
│                                                                 │
│  /produtos  /grupos  /simulacao  /promocoes  /relatorios        │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ MargemEngine │  │ PromoEngine  │  │   AlertaService      │  │
│  │ calcula %    │  │ simula/publ. │  │   e-mail/WhatsApp    │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└───────────────────────┬─────────────────────────────────────────┘
                        │ SQLAlchemy ORM
┌───────────────────────▼─────────────────────────────────────────┐
│                      BANCO DE DADOS                             │
│                    PostgreSQL 16                                │
│  produtos │ grupos │ promocoes │ historico_margem │ alertas     │
└─────────────────────────────────────────────────────────────────┘
```

## Modelo de Dados

### Tabela: grupos
```sql
id, nome, margem_minima, margem_maxima, desconto_maximo_permitido
```

### Tabela: produtos
```sql
id, sku, nome, grupo_id, custo, preco_venda, estoque, ativo
-- margem calculada: (preco_venda - custo) / preco_venda
```

### Tabela: promocoes
```sql
id, nome, grupo_id, sku_ids[], desconto_pct, qtd_limite,
data_inicio, data_fim, status (rascunho/ativa/encerrada),
impacto_margem_estimado, aprovada_por
```

### Tabela: historico_margem
```sql
id, data, tipo (dia/semana/mes), margem_pct,
faturamento, custo_total, alerta_disparado
```

## Fluxo Principal — Simulação de Promoção

```
Gestor seleciona grupo/SKUs
        ↓
Define: desconto %, qtd máx, período
        ↓
Frontend chama POST /simulacao
        ↓
MargemEngine calcula:
  nova_margem = (receita_estimada - custo_total) / receita_estimada
  impacto_pp  = margem_atual - nova_margem
        ↓
Retorna: nova_margem_semanal, impacto_pp, status (seguro/alerta/bloqueado)
        ↓
Gestor confirma → POST /promocoes (publica ou rascunho)
        ↓
AlertaService verifica se nova_margem < 17% → bloqueia ou envia alerta
```

## Infraestrutura

```yaml
# docker-compose.yml (simplificado)
services:
  frontend:  { build: ./frontend,  ports: ["3000:3000"] }
  backend:   { build: ./backend,   ports: ["8000:8000"] }
  db:        { image: postgres:16,  ports: ["5432:5432"] }
```

Roda no servidor HP local ou em VPS de R$40-80/mês.
