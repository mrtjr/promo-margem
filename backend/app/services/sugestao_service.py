import os
import json
import httpx
from typing import List
from sqlalchemy.orm import Session
from .. import models, schemas
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/auto")

def get_smart_suggestions(db: Session) -> List[schemas.Sugestao]:
    # 1. Gather Context
    produtos = db.query(models.Produto).all()
    grupos = db.query(models.Grupo).all()
    
    # 2. Try AI First
    if OPENROUTER_API_KEY:
        ai_suggestions = get_ai_suggestions(produtos, grupos)
        if ai_suggestions:
            return ai_suggestions
            
    # 3. Fallback to Hardcoded Rules
    return get_fallback_suggestions(produtos)

def get_ai_suggestions(produtos, grupos) -> List[schemas.Sugestao]:
    try:
        # Prepare context as text
        context_data = {
            "config": {
                "meta_margem_global": "17% - 19%",
                "moeda": "BRL"
            },
            "produtos": [
                {
                    "id": p.id,
                    "sku": p.sku,
                    "nome": p.nome,
                    "custo": p.custo,
                    "preco_venda": p.preco_venda,
                    "margem": f"{p.margem*100:.1f}%",
                    "estoque": p.estoque
                } for p in produtos
            ]
        }

        prompt = f"""
        Você é um consultor de precificação inteligente para atacado e varejo. 
        Analise os produtos abaixo e sugira ações estratégicas para maximizar a venda e manter a margem global entre 17% e 19%.
        
        Considere:
        - Produtos com estoque alto (>150 un) e margem alta (>25%) são ótimos para promoção.
        - Produtos com margem baixa (<10%) precisam de ajuste de preço ou alerta.
        - Seja específico nas descrições de PORQUE a ação foi sugerida.
        
        DADOS:
        {json.dumps(context_data, indent=2)}
        
        Responda APENAS um array JSON contendo objetos no formato:
        {{
            "id": "id-unico",
            "produto_id": 123,
            "produto_nome": "Nome",
            "sku": "SKU",
            "tipo": "promoção" | "ajuste_cima" | "alerta",
            "descricao": "Texto explicativo",
            "impacto_estimado": "Texto explicativo do impacto",
            "desconto_sugerido": 10.0,
            "urgencia": "alta" | "media" | "baixa"
        }}
        """

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "PromoMargem",
            "Content-Type": "application/json"
        }

        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "system", "content": "Você é um especialista em margem de lucro e precificação. Retorne apenas JSON puro sem markdown."},
                {"role": "user", "content": prompt}
            ],
            "response_format": { "type": "json_object" }
        }

        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            res_json = response.json()
            
            content = res_json['choices'][0]['message']['content']
            
            # OpenRouter/Auto might wrap in markdown or just return JSON object
            data = json.loads(content)
            
            # If AI returns a wrapped object like {"suggestions": [...]}
            if isinstance(data, dict):
                for key in ['suggestions', 'sugestoes', 'data']:
                    if key in data:
                        suggestions_raw = data[key]
                        break
                else:
                    # Maybe it returned as root fields? 
                    # Let's hope it's a list or an object with the list
                    suggestions_raw = data if isinstance(data, list) else [data]
            else:
                suggestions_raw = data

            # Convert to schemas
            final_suggestions = []
            for s in suggestions_raw:
                final_suggestions.append(schemas.Sugestao(**s))
            
            return final_suggestions

    except Exception as e:
        print(f"AI Suggestion Error: {e}")
        return None

def get_fallback_suggestions(produtos) -> List[schemas.Sugestao]:
    suggestions = []
    for p in produtos:
        if p.estoque > 150 and p.margem > 0.25:
            suggestions.append(schemas.Sugestao(
                id=f"fallback-p-{p.id}",
                produto_id=p.id,
                produto_nome=p.nome,
                sku=p.sku,
                tipo="promoção",
                descricao="[Fallback] Estoque alto e margem excedente.",
                impacto_estimado="+10% giro",
                desconto_sugerido=10.0,
                urgencia="media"
            ))
    return suggestions

async def get_ai_chat_response(db: Session, messages: List[schemas.ChatMessage]) -> str:
    # 1. Gather all data as context
    produtos = db.query(models.Produto).all()
    grupos = db.query(models.Grupo).all()
    
    context_data = {
        "status_atual": {
            "meta_global": "17-19%",
            "produtos_totais": len(produtos)
        },
        "produtos": [
            {
                "sku": p.sku,
                "nome": p.nome,
                "custo": p.custo,
                "preco": p.preco_venda,
                "margem": f"{p.margem*100:.1f}%",
                "estoque": p.estoque
            } for p in produtos
        ]
    }

    system_prompt = f"""
    Você é o 'Copiloto PromoMargem', um consultor sênior de estratégia comercial e precificação.
    Você tem acesso em tempo real aos dados da loja do usuário abaixo.
    
    CONTEXTO DO SISTEMA:
    {json.dumps(context_data, indent=2)}
    
    DIRETRIZES:
    1. Responda em Português do Brasil com tom profissional porém amigável.
    2. Sempre que sugerir algo, fundamente com os dados de margem e estoque presentes no contexto.
    3. Use Markdown para formatar tabelas, negritos e listas.
    4. Se o usuário perguntar sobre meta, lembre-o que a meta é entre 17% e 19% de margem global.
    5. Você pode simular cenários se o usuário pedir (ex: "E se eu baixar o Arroz em 5%?").
    """

    full_messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Append conversation history
    for m in messages:
        full_messages.append({"role": m.role, "content": m.content})

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "PromoMargem",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": full_messages
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            res_json = response.json()
            return res_json['choices'][0]['message']['content']
    except Exception as e:
        return f"Desculpe, tive um problema ao me conectar com o cérebro da IA. Erro: {str(e)}"
