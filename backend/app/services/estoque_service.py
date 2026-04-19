from sqlalchemy.orm import Session
from .. import models, schemas
import uuid

def registrar_entrada(db: Session, entrada: schemas.EntradaCreate):
    # Determine which product
    produto = None
    if entrada.produto_id:
        produto = db.query(models.Produto).filter(models.Produto.id == entrada.produto_id).first()
    
    if not produto and entrada.nome_produto:
        # Check if already exists by name
        produto = db.query(models.Produto).filter(models.Produto.nome == entrada.nome_produto).first()
        
        if not produto:
            # Create new product automatically
            new_sku = f"AUTO-{uuid.uuid4().hex[:6].upper()}"
            produto = models.Produto(
                sku=new_sku,
                nome=entrada.nome_produto,
                grupo_id=entrada.grupo_id or 1, # Default to first group if none
                custo=entrada.custo_unitario,
                preco_venda=entrada.custo_unitario * 1.2, # Markup inicial de 20%
                estoque_qtd=0,
                estoque_peso=0
            )
            db.add(produto)
            db.commit()
            db.refresh(produto)

    if produto:
        # Calculate new weighted average cost based on Total Weight
        total_peso_novo = entrada.quantidade * entrada.peso
        
        peso_atual = produto.estoque_peso
        custo_atual = produto.custo
        
        novo_peso_total = peso_atual + total_peso_novo
        
        if novo_peso_total > 0:
            # Custo Médio Ponderado (CMP) baseado no peso total
            novo_custo_medio = ((peso_atual * custo_atual) + (total_peso_novo * entrada.custo_unitario)) / novo_peso_total
            produto.custo = novo_custo_medio
        
        # Update Stock
        produto.estoque_qtd += entrada.quantidade
        produto.estoque_peso += total_peso_novo
        
        # Log movement
        mov = models.Movimentacao(
            produto_id=produto.id,
            tipo="ENTRADA",
            quantidade=entrada.quantidade,
            peso=entrada.peso,
            custo_unitario=entrada.custo_unitario,
            cidade=entrada.cidade,
            peso_medida=None
        )
        db.add(mov)
        db.commit()
        return True
    return False

async def registrar_entrada_bulk(db: Session, entradas: list):
    for e in entradas:
        registrar_entrada(db, e)
    return True

def registrar_venda_bulk(db: Session, vendas: list):
    for v in vendas:
        v_schema = schemas.VendaBulkItem(**v)
        produto = db.query(models.Produto).filter(models.Produto.id == v_schema.produto_id).first()
        if produto:
            # Calculate weight to remove based on current average weight per volume
            if produto.estoque_qtd > 0:
                peso_medio_volume = produto.estoque_peso / produto.estoque_qtd
                peso_baixado = v_schema.quantidade * peso_medio_volume
                
                # Minimum safety check
                produto.estoque_qtd -= v_schema.quantidade
                produto.estoque_peso -= peso_baixado
                
                # Prevent negative stock
                if produto.estoque_qtd < 0: produto.estoque_qtd = 0
                if produto.estoque_peso < 0: produto.estoque_peso = 0
            
            # Record sale
            venda_mod = models.Venda(
                produto_id=produto.id,
                quantidade=v_schema.quantidade,
                preco_venda=v_schema.preco_venda,
                custo_total=v_schema.quantidade * (produto.custo if produto.custo else 0)
            )
            db.add(venda_mod)
            
            # Movement log
            mov = models.Movimentacao(
                produto_id=produto.id,
                tipo="SAIDA",
                quantidade=v_schema.quantidade,
                custo_unitario=v_schema.preco_venda
            )
            db.add(mov)
    
    db.commit()
    return True
