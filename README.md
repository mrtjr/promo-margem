# 🎯 PromoMargem

> Sistema inteligente de precificação, promoção e controle de margem para empresas de **atacado e varejo**.

---

## 📌 Visão Geral

Empresa com faturamento de R$400k–R$600k/mês, mix de 300–500 SKUs e margens variadas entre 7% e +30%. O sistema automatiza o controle de margem por grupo de produto, simula cenários de promoção agressiva e garante que a margem média semanal fique entre **17–19%** e o fechamento mensal em **18%**.

---

## 🔥 Diferenciais Realizados

- **🛠️ Gestão Dual de Estoque**: Controle simultâneo por **Volumes (UN)** e **Peso (Kg/L)**. Ideal para produtos vendidos de forma fracionada.
- **📊 Importação Inteligente (Excel/CSV)**:
  - **Entrada via Excel**: Suporte a CTRL+C/CTRL+V para entradas rápidas de estoque com criação automática de produtos.
  - **Fechamento via CSV**: Parser customizado de relatórios analíticos (`xRelVendaAnalitica2.csv`) com soma automática de vendas e cálculo de **Preço Médio Ponderado**.
- **📈 Dashboard em Tempo Real**: Métricas de SKUs totais, rupturas e saúde por categoria (Alimentícios, Temperos, Embalagens e Cereais).

---

## 🏗️ Arquitetura

```
promo-margem/
├── frontend/          # React + Vite + TypeScript
├── backend/           # Python + FastAPI (SQLAlchemy + PostgreSQL)
├── docker-compose.yml # Orquestração completa do ambiente
└── iniciar.ps1        # Script de inicialização rápida
```

---

## 🛠️ Stack Tecnológica

| Camada | Tecnologia |
|---|---|
| Frontend | React 19 + Vite + TypeScript |
| UI | Tailwind CSS + Lucide Icons |
| Backend | Python 3.12 + FastAPI |
| Banco | PostgreSQL 16 (Docker) |
| OCR/Parser | Algoritmos customizados para CSV/TSV |

---

## 🚀 Roadmap

- [x] **Fase 1** — Setup + estrutura base (backend API + banco)
- [x] **Fase 2** — Importação de produtos e grupos (Excel/manual)
- [x] **Fase 3** — Dashboard de margem e SKUs
- [ ] **Fase 4** — Simulador de promoção (Protótipo funcional)
- [ ] **Fase 5** — Engine de sugestão automática
- [x] **Fase 6** — Relatário de Fechamento via CSV
- [ ] **Fase 7** — Integração PDV/ERP via API

---

## 📦 Como Rodar

1. Certifique-se de ter o **Docker** instalado.
2. Execute o script de inicialização:
   ```powershell
   ./iniciar.ps1
   ```
3. Acesse o sistema em: `http://localhost:5173`

---

## 📄 Licença

MIT — uso livre para fins comerciais.
