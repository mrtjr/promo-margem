from typing import List
from sqlalchemy.orm import Session
from ..models import Produto

def calculate_margin(preco_venda: float, custo: float) -> float:
    if preco_venda == 0:
        return 0
    return (preco_venda - custo) / preco_venda

def calculate_global_margin(produtos: List[Produto]) -> float:
    # Use estoque_qtd for weighted calculations
    total_receita = sum(p.preco_venda * p.estoque_qtd for p in produtos if p.ativo)
    total_custo = sum(p.custo * p.estoque_qtd for p in produtos if p.ativo)
    
    if total_receita == 0:
        return 0
    return (total_receita - total_custo) / total_receita

def simulate_promotion_impact(
    produtos_all: List[Produto], 
    produtos_promo_ids: List[int], 
    desconto_pct: float
) -> dict:
    """
    Calculates the impact of a promotion on the global margin.
    """
    # Current weighted margin
    total_receita_atual = sum(p.preco_venda * p.estoque_qtd for p in produtos_all if p.ativo)
    total_custo_total = sum(p.custo * p.estoque_qtd for p in produtos_all if p.ativo)
    
    # Calculate new revenue after discount
    receita_promo = 0
    custo_promo = 0
    receita_mantida = 0
    custo_mantido = 0
    
    for p in produtos_all:
        if not p.ativo:
            continue
        if p.id in produtos_promo_ids:
            # Promo items
            novo_preco = p.preco_venda * (1 - desconto_pct / 100)
            receita_promo += novo_preco * p.estoque_qtd
            custo_promo += p.custo * p.estoque_qtd
        else:
            # Regular items
            receita_mantida += p.preco_venda * p.estoque_qtd
            custo_mantido += p.custo * p.estoque_qtd
            
    nova_receita_total = receita_promo + receita_mantida
    novo_custo_total = custo_promo + custo_mantido
    
    if nova_receita_total == 0:
        nova_margem = 0
    else:
        nova_margem = (nova_receita_total - novo_custo_total) / nova_receita_total
        
    margem_atual = (total_receita_atual - total_custo_total) / total_receita_atual if total_receita_atual > 0 else 0
    impacto_pp = (margem_atual - nova_margem) * 100
    
    status = "seguro"
    if nova_margem < 0.17:
        status = "bloqueado"
    elif nova_margem < 0.175:
        status = "alerta"

    return {
        "margem_atual": margem_atual,
        "nova_margem_estimada": nova_margem,
        "impacto_pp": impacto_pp,
        "status": status
    }


def calcular_impacto(db: Session, sku_ids: List[int], desconto_pct: float) -> dict:
    """
    Wrapper de conveniência: busca todos produtos ativos e calcula impacto
    aplicando o desconto apenas nos `sku_ids`. Usado pelo promocao_service
    e pelos endpoints de simulação.
    """
    produtos = db.query(Produto).filter(Produto.ativo == True).all()
    return simulate_promotion_impact(produtos, sku_ids, desconto_pct)
