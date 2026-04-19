# PRD — PromoMargem

**Versão:** 1.0  
**Data:** 2026-04-19  
**Status:** Em desenvolvimento

---

## 1. Problema

Empresas de atacado e varejo com mix amplo de produtos (300–500 SKUs) têm dificuldade em fazer promoções agressivas sem comprometer a margem global. A precificação manual leva a guerras de preço, estoque parado e perda de rentabilidade. Sem dados consolidados, o gestor não sabe quais produtos podem ser promovidos com segurança.

---

## 2. Objetivo

Criar um sistema que permita:

1. Visualizar margem real em tempo real por produto, grupo e período
2. Simular o impacto de promoções antes de publicá-las
3. Garantir que a margem média semanal fique em 17–19%
4. Fechar o mês dentro de 18% de margem consolidada
5. Sugerir automaticamente promoções seguras por grupo

---

## 3. Usuários

| Perfil | Função principal |
|---|---|
| Gestor comercial | Define e aprova promoções |
| Comprador | Analisa margem por fornecedor/grupo |
| Financeiro | Monitora fechamento de margem mensal |

---

## 4. Regras de Negócio Principais

### 4.1 Faixas de Margem por Grupo

| Grupo | Margem | Estratégia |
|---|---|---|
| Baixa | 7% – 12% | Promoção só com volume alto; desconto máximo configurável |
| Média | 20% – 26% | Promoção agressiva permitida; desconto até 15% |
| Alta | > 30% | Promoção livre; upsell e bundles |

### 4.2 Regras de Margem Operacional

- **Meta semanal:** 17% ≤ margem média ≤ 19%
- **Meta mensal:** margem consolidada = 18%
- **Alerta amarelo:** margem abaixo de 17,5% ou acima de 19,5%
- **Alerta vermelho:** margem abaixo de 17% ou projeção mensal fora de 17,8%–18,2%
- **Margem mínima absoluta por produto:** configurável por grupo (default: 7%)

### 4.3 Regras de Promoção

- O simulador deve calcular o impacto na margem média antes de salvar
- Promoções com impacto > 1,5 pp na margem semanal precisam de aprovação manual
- Toda promoção tem data de início, fim e limite de quantidade opcionais
- Produtos com margem < 10% não entram em promoção sem override manual

---

## 5. Funcionalidades do MVP

### F1 — Cadastro de Produtos e Grupos
- CRUD de produtos com: nome, SKU, custo, preço de venda, grupo, estoque
- Importação via CSV (modelo disponível)
- Cálculo automático de margem = (preço - custo) / preço

### F2 — Dashboard de Margem
- Margem atual: dia, semana, mês
- Indicadores: margem por grupo, por top 20 SKUs, total
- Alerta visual se fora da meta
- Histórico de variação de margem (gráfico)

### F3 — Simulador de Promoção
- Seleção de grupo(s) ou SKU(s) individuais
- Input: % desconto, quantidade máxima, período
- Output: nova margem estimada semanal/mensal, variação em pp
- Botão "Publicar promoção" ou "Salvar como rascunho"

### F4 — Engine de Sugestão
- Analisa SKUs com baixa rotação + margem ≥ 10%
- Sugere desconto máximo seguro para manter meta
- Exibe: "Promo sugerida: grupo Médio, 15% off em 30 SKUs → margem estimada 17,8%"

### F5 — Monitor e Relatórios
- Relatório semanal automático (segunda-feira 08h)
- Alerta por e-mail/WhatsApp se meta desviar
- Exportação: CSV e PDF
- Relatório de fechamento mensal

---

## 6. Fora de Escopo (v1)

- Integração com PDV em tempo real (fase 7)
- App mobile
- Multi-empresa (fase futura)
- Precificação por concorrência (fase futura)

---

## 7. Requisitos Não-Funcionais

| Requisito | Detalhamento |
|---|---|
| Performance | Dashboard carrega em < 2s com 500 SKUs |
| Usabilidade | Interface autoexplicativa — sem treinamento |
| Segurança | Login com senha; dados locais ou VPS privada |
| Escalabilidade | Suporta até 5.000 SKUs sem refatoração |
| Disponibilidade | Roda offline (servidor local) ou online |

---

## 8. Métrica de Sucesso

- Margem mensal dentro de 17,8%–18,2% por 3 meses consecutivos
- Gestor consegue simular e publicar promoção em menos de 3 minutos
- Zero promoções publicadas que causem margem abaixo de 16,5%
