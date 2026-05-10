"""
LLM-judge — Sprint S1.3.

Disambigua casos `ambiguous` produzidos pelo embedding_index.judge().
Quando o TF-IDF entrega top-1 com confianca media (0.55 <= score < 0.85),
chamamos um LLM curto para decidir entre as alternativas.

Design:
  - DEPENDENCIA OPCIONAL: roda apenas se ANTHROPIC_API_KEY estiver no env
  - DEGRADACAO GRACIOSA: sem chave -> retorna "judge_indisponivel", caller
    mantem comportamento atual (top-1 com confianca media + needs_review)
  - CACHE em memoria por (nome_csv, top-K-hash) — evita chamadas duplicadas
    no mesmo modal/import session
  - ZERO mudanca contratual no Reconciliator pra quem nao usa LLM
  - Custo estimado registrado em agent_run.cost_estimate

Modelo padrao: claude-haiku-4-5 (cheap, fast, plenty preciso pra escolha
binaria/ternaria entre 3 candidatos). Override via env LLM_JUDGE_MODEL.

Schema de entrada/saida estritamente JSON. Prompt direto, sem cadeia de
raciocinio extensa. Se o LLM responder algo que nao parsa, fallback
silencioso para "judge_indisponivel".
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Any, Optional

# httpx ja esta no requirements; importacao tardia preserva startup rapido
# se nao for usado.

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------
ENV_API_KEY = "ANTHROPIC_API_KEY"
ENV_MODEL = "LLM_JUDGE_MODEL"
DEFAULT_MODEL = "claude-haiku-4-5"
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_TIMEOUT_SEC = 8.0
DEFAULT_MAX_TOKENS = 256

# Estimativa conservadora: input ~250 tokens, output ~80 tokens.
# Custo Haiku 4.5 (assumido em USD): $0.80/M input, $4.00/M output.
# Ajustavel se modelo trocar.
COST_INPUT_PER_TOKEN = 0.80 / 1_000_000
COST_OUTPUT_PER_TOKEN = 4.00 / 1_000_000


@dataclass
class JudgeResult:
    """
    Resultado de uma chamada de judge.
      - status: 'aceitar_top1' | 'sugerir_topN' | 'criar' | 'ignorar' | 'judge_indisponivel'
      - top_n_idx: quando 'sugerir_topN', indice (0-based) do candidato escolhido
      - confidence_after: nova confianca apos judge (pode subir ou cair)
      - rationale: 1 frase explicativa do LLM (curta)
      - tokens_in / tokens_out: para custo agregado
      - model: identificador do modelo usado
      - error: mensagem se status='judge_indisponivel'
    """
    status: str
    top_n_idx: Optional[int] = None
    confidence_after: Optional[float] = None
    rationale: Optional[str] = None
    tokens_in: int = 0
    tokens_out: int = 0
    model: Optional[str] = None
    error: Optional[str] = None

    @property
    def cost_usd(self) -> float:
        return (
            self.tokens_in * COST_INPUT_PER_TOKEN
            + self.tokens_out * COST_OUTPUT_PER_TOKEN
        )


# ---------------------------------------------------------------------------
# Cache em memoria — limpo a cada restart do backend
# ---------------------------------------------------------------------------
_cache: dict[str, JudgeResult] = {}
_max_cache = 500


def _cache_key(nome_csv: str, candidatos: list[dict]) -> str:
    """
    Hash estavel de (nome + ids dos candidatos + scores arredondados).
    Mesmo input -> mesmo cache hit.
    """
    parts = [nome_csv.strip().lower()]
    for c in candidatos[:5]:
        parts.append(f"{c.get('produto_id')}:{round(c.get('score', 0), 3)}")
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# API publica
# ---------------------------------------------------------------------------

def is_available() -> bool:
    """True se a chave esta configurada. Caller pode decidir nao chamar."""
    return bool(os.getenv(ENV_API_KEY))


def disambiguate(
    nome_csv: str,
    codigo_csv: Optional[str],
    candidatos: list[dict],
) -> JudgeResult:
    """
    Pede ao LLM pra escolher entre os candidatos top-K do embedding_index.

    candidatos = [{produto_id, nome, codigo, score, rationale}, ...]
    (mesmo formato de top_k())

    Retorna JudgeResult. Sempre retorna algo — se sem chave ou erro,
    status='judge_indisponivel' (caller mantem fallback atual).
    """
    if not candidatos:
        return JudgeResult(status="judge_indisponivel", error="sem_candidatos")

    if not is_available():
        return JudgeResult(status="judge_indisponivel", error="ANTHROPIC_API_KEY ausente")

    key = _cache_key(nome_csv, candidatos)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    try:
        result = _chamar_llm(nome_csv, codigo_csv, candidatos)
    except Exception as e:
        return JudgeResult(status="judge_indisponivel", error=f"erro_llm: {e}")

    # Cache LRU rudimentar — drop oldest se cheio
    if len(_cache) >= _max_cache:
        _cache.pop(next(iter(_cache)))
    _cache[key] = result
    return result


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _build_prompt(nome_csv: str, codigo_csv: Optional[str], candidatos: list[dict]) -> str:
    """
    Prompt JSON-only. Sem cadeia de raciocinio — modelo decide direto.
    """
    cand_lines = []
    for i, c in enumerate(candidatos[:3]):
        cand_lines.append(
            f"  {i}. id={c['produto_id']} | nome={c['nome']} | codigo={c.get('codigo') or '-'} "
            f"| score_embedding={c.get('score', 0):.3f}"
        )
    cand_block = "\n".join(cand_lines)

    return (
        "Voce eh um juiz de matching de produtos para um sistema operacional comercial.\n"
        "Decida se algum dos candidatos eh o mesmo produto que aparece no CSV de vendas.\n"
        "\n"
        f"PRODUTO NO CSV: '{nome_csv}'\n"
        f"CODIGO NO CSV: {codigo_csv or '(nenhum)'}\n"
        "\n"
        "CANDIDATOS DO CATALOGO:\n"
        f"{cand_block}\n"
        "\n"
        "Responda APENAS com JSON valido neste formato:\n"
        '{\n'
        '  "decisao": "aceitar_top1" | "sugerir_topN" | "criar" | "ignorar",\n'
        '  "top_n_idx": 0|1|2 (so quando decisao=sugerir_topN),\n'
        '  "confidence": 0.0-1.0,\n'
        '  "rationale": "frase curta em portugues"\n'
        '}\n'
        "\n"
        "Regras:\n"
        '- "aceitar_top1": candidato 0 eh confiantemente o mesmo produto\n'
        '- "sugerir_topN": outro candidato (1 ou 2) eh melhor match que o 0\n'
        '- "criar": nenhum candidato eh o mesmo produto, deve cadastrar novo\n'
        '- "ignorar": dado insuficiente ou produto irrelevante\n'
        "- confidence 0.85+ = decisao firme; 0.6-0.85 = boa; <0.6 = duvidosa\n"
    )


def _chamar_llm(nome_csv: str, codigo_csv: Optional[str], candidatos: list[dict]) -> JudgeResult:
    """
    Chama Anthropic Messages API via httpx. Importacao tardia.
    """
    import httpx  # noqa: WPS433

    api_key = os.getenv(ENV_API_KEY, "")
    model = os.getenv(ENV_MODEL, DEFAULT_MODEL)

    payload = {
        "model": model,
        "max_tokens": DEFAULT_MAX_TOKENS,
        "messages": [
            {"role": "user", "content": _build_prompt(nome_csv, codigo_csv, candidatos)},
        ],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    with httpx.Client(timeout=DEFAULT_TIMEOUT_SEC) as client:
        resp = client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # Extrai texto + usage
    content = data.get("content", [])
    text = ""
    for block in content:
        if block.get("type") == "text":
            text += block.get("text", "")
    text = text.strip()

    usage = data.get("usage", {})
    tokens_in = int(usage.get("input_tokens", 0))
    tokens_out = int(usage.get("output_tokens", 0))

    # Parse JSON do output do LLM. Se falhar -> judge_indisponivel.
    parsed = _safe_parse_json(text)
    if parsed is None:
        return JudgeResult(
            status="judge_indisponivel",
            error="resposta_nao_eh_json",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=model,
        )

    decisao = parsed.get("decisao")
    if decisao not in {"aceitar_top1", "sugerir_topN", "criar", "ignorar"}:
        return JudgeResult(
            status="judge_indisponivel",
            error=f"decisao_invalida: {decisao}",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model=model,
        )

    confidence = parsed.get("confidence")
    if isinstance(confidence, (int, float)):
        confidence = max(0.0, min(1.0, float(confidence)))
    else:
        confidence = None

    top_n_idx = parsed.get("top_n_idx")
    if not isinstance(top_n_idx, int) or top_n_idx < 0 or top_n_idx >= len(candidatos):
        top_n_idx = None

    return JudgeResult(
        status=decisao,
        top_n_idx=top_n_idx,
        confidence_after=confidence,
        rationale=str(parsed.get("rationale", ""))[:200] if parsed.get("rationale") else None,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        model=model,
    )


def _safe_parse_json(text: str) -> Optional[dict]:
    """Tenta parsear JSON, com tolerancia a fences markdown."""
    if not text:
        return None
    # Tira fences markdown comuns
    if text.startswith("```"):
        # Encontra fim do fence
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)

    try:
        return json.loads(text)
    except Exception:
        # Tenta extrair primeiro { ... } JSON da string
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return None
        return None
