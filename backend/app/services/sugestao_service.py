import os
import json
import httpx
from typing import List, Optional
from datetime import date
from dataclasses import asdict
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
                    "estoque_qtd": p.estoque_qtd,
                    "estoque_peso": p.estoque_peso
                } for p in produtos
            ]
        }

        prompt = f"""
        Você é um consultor de precificação inteligente para atacado e varejo.
        Analise os produtos abaixo e sugira ações estratégicas para maximizar a venda e manter a margem global entre 17% e 19%.

        Considere:
        - Produtos com estoque alto (estoque_qtd > 150) e margem alta (>25%) são ótimos para promoção.
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
        if p.estoque_qtd > 150 and p.margem > 0.25:
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
        elif p.margem < 0.10 and p.preco_venda > 0:
            suggestions.append(schemas.Sugestao(
                id=f"fallback-a-{p.id}",
                produto_id=p.id,
                produto_nome=p.nome,
                sku=p.sku,
                tipo="alerta",
                descricao="[Fallback] Margem abaixo de 10%. Revisar custo ou preço.",
                impacto_estimado="Risco de prejuízo",
                desconto_sugerido=None,
                urgencia="alta"
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
                "estoque_qtd": p.estoque_qtd,
                "estoque_peso": p.estoque_peso
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


async def get_narrativa_fechamento(
    db: Session,
    data_alvo: Optional[date] = None,
    janela_dias: int = 30,
    top_n_recs: int = 8,
) -> dict:
    """
    Gera narrativa IA consolidada do fechamento + projeção D+1 + recomendações.

    Retorna dict: {
      "narrativa": str (markdown),
      "fonte": "ia" | "template",
      "analise": dict, "projecao": dict, "recomendacoes": list
    }

    A narrativa é otimizada para:
    - Leitura rápida (< 60s) pelo gestor comercial
    - Cópia direta para WhatsApp
    - Destaque dos 3 movimentos mais importantes do próximo dia
    """
    from . import analise_service, forecast_service, recomendacao_service

    if data_alvo is None:
        data_alvo = date.today()

    analise = analise_service.analisar_fechamento(db, data_alvo, janela_dias=janela_dias)
    projecao = forecast_service.projetar_proximo_dia(db, hoje=data_alvo, top_n=10)
    recomendacoes = recomendacao_service.gerar_recomendacoes(
        db, data_alvo=data_alvo, top_n=top_n_recs, janela_dias=janela_dias
    )

    analise_dict = asdict(analise)
    projecao_dict = asdict(projecao)
    recs_dicts = [asdict(r) for r in recomendacoes]

    payload_contexto = {
        "analise_fechamento": analise_dict,
        "projecao_amanha": projecao_dict,
        "recomendacoes_top": recs_dicts,
    }

    narrativa = None
    fonte = "template"
    if OPENROUTER_API_KEY:
        narrativa = await _gerar_narrativa_ia(payload_contexto)
        if narrativa:
            fonte = "ia"

    if narrativa is None:
        narrativa = _narrativa_template(analise_dict, projecao_dict, recs_dicts)

    return {
        "narrativa": narrativa,
        "fonte": fonte,
        "analise": analise_dict,
        "projecao": projecao_dict,
        "recomendacoes": recs_dicts,
    }


async def _gerar_narrativa_ia(contexto: dict) -> Optional[str]:
    """Chama OpenRouter para gerar narrativa em markdown PT-BR."""
    prompt = f"""
Você é um consultor comercial sênior especializado em atacado/varejo alimentício no Brasil.
Gere um **briefing de fechamento diário** em português do Brasil, tom direto e profissional,
para o gestor copiar e enviar no WhatsApp da equipe.

DADOS (JSON):
{json.dumps(contexto, ensure_ascii=False, indent=2)}

ESTRUTURA OBRIGATÓRIA (use markdown):
1. **Manchete** (1 linha): status do dia + principal driver. Exemplo: "Dia saudável: margem 17,8% com alta em A-X."
2. **Resumo de números** (bullet list curto): faturamento, margem, variação 7d, rupturas
3. **Projeção amanhã** (2-3 linhas): previsão de faturamento, confiança, desvio vs média 7d
4. **3 movimentos para amanhã** (ordenado por urgência): ação + SKU + justificativa curta
5. **Riscos/atenções** (opcional, só se houver anomalias): bullet curto

REGRAS:
- Máximo 250 palavras
- Não invente números — use apenas os do JSON
- Não use jargão técnico (ABC-XYZ pode ser "produtos chave / estáveis / erráticos")
- Termine com 1 frase de recomendação prática
- Não inclua títulos tipo "Briefing de Fechamento" — comece direto pela manchete
"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "http://localhost:3000",
        "X-Title": "PromoMargem - Narrativa",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Você é um consultor comercial sênior. Responda apenas com o briefing em markdown, nada mais."},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            r = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers, json=payload,
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Narrativa IA error: {e}")
        return None


def _narrativa_template(analise: dict, projecao: dict, recomendacoes: list) -> str:
    """Fallback textual determinístico — sem IA, mas legível."""
    status = analise.get("status_meta", "desconhecido")
    status_emoji = {
        "saudavel": "🟢", "atencao": "🟡", "alerta": "🔴",
        "sem_vendas": "⚪",
    }.get(status, "⚪")
    status_texto = {
        "saudavel": "Dia saudável",
        "atencao": "Dia em atenção",
        "alerta": "Dia em alerta",
        "sem_vendas": "Dia sem vendas",
    }.get(status, "Dia")

    margem_pct = analise.get("margem_dia", 0) * 100
    fat = analise.get("faturamento_dia", 0)
    var_7d = analise.get("variacao_faturamento_7d_pct", 0)
    margem_7d = analise.get("margem_media_7d", 0) * 100
    rupturas = analise.get("rupturas", 0)
    sku_vend = analise.get("total_skus_vendidos", 0)

    linhas = []
    linhas.append(f"{status_emoji} **{status_texto}**: margem {margem_pct:.1f}% com faturamento R$ {fat:,.2f}.".replace(",", "."))
    linhas.append("")
    linhas.append("**Resumo**")
    linhas.append(f"- Faturamento do dia: R$ {fat:,.2f}".replace(",", "."))
    linhas.append(f"- Margem: {margem_pct:.1f}% (média 7d: {margem_7d:.1f}%)")
    linhas.append(f"- Variação vs média 7d: {var_7d:+.1f}%")
    linhas.append(f"- SKUs vendidos: {sku_vend} | Rupturas: {rupturas}")
    linhas.append("")

    # Projeção
    fat_prev = projecao.get("faturamento_previsto", 0)
    margem_prev = projecao.get("margem_prevista", 0) * 100
    conf = projecao.get("confianca_geral", "sem_dados")
    dia_sem = projecao.get("dia_semana", "")
    comp_7d = projecao.get("comparacao_media_7d_pct", 0)
    linhas.append(f"**Projeção para {dia_sem}**")
    linhas.append(f"- Faturamento previsto: R$ {fat_prev:,.2f} ({comp_7d:+.1f}% vs média 7d)".replace(",", "."))
    linhas.append(f"- Margem prevista: {margem_prev:.1f}% | Confiança: {conf}")
    linhas.append("")

    # Top recomendações
    if recomendacoes:
        count = min(len(recomendacoes), 3)
        rotulo = "movimento" if count == 1 else "movimentos"
        linhas.append(f"**{count} {rotulo} para amanhã**")
        for r in recomendacoes[:3]:
            acao = r.get("acao", "").replace("_", " ")
            sku = r.get("sku", "")
            nome = r.get("nome", "")
            desc = r.get("desconto_sugerido")
            urg = r.get("urgencia", "")
            extra = f" ({desc:.0f}% off)" if desc else ""
            linhas.append(f"- **{acao.upper()}**{extra} — {nome} [{sku}] · urgência {urg}")
        linhas.append("")

    # Anomalias
    anomalias = analise.get("anomalias", [])
    altas = [a for a in anomalias if a.get("severidade") == "alta"]
    if altas:
        linhas.append("**Atenção imediata**")
        for a in altas[:3]:
            linhas.append(f"- {a.get('descricao', '')}")
        linhas.append("")

    linhas.append("_Gerado sem IA (fallback determinístico)._")
    return "\n".join(linhas)
