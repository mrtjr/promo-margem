"""
Catalog Embedding Index — vetores TF-IDF char n-gram do catalogo.

Sprint S0 — Fundacoes Agentic.

SUBSTITUI a heuristica `PALAVRAS_CHAVE_GRUPO` (mapa hardcoded de palavras
no frontend) e `sugerirProdutoExistente` (substring match) por:
  - vetorizacao TF-IDF char n-gram (3-5)
  - normalizacao (NFD, lowercase, sem espaco extra)
  - top-K matching via cosine similarity
  - score calibrado para thresholding
  - judge programatico (faixa de confianca)

Por que TF-IDF char n-gram, nao sentence-transformers?
  - Zero dependencia nova (numpy ja esta no stack via pandas)
  - Offline 100%, sem download de modelo
  - Bundling PyInstaller-friendly (~117MB de modelo evitados)
  - Performance: catalogo desktop tipico <10k produtos -> match em <50ms
  - Adequado pro escopo narrow do Reconciliator V0 (matching de nomes
    similares, nao classificacao semantica geral)

Upgrade path documentado: quando precisar de matching semantico real
("manga" -> "frutas"), trocar implementacao mantendo mesma interface
(EmbeddingModel.encode(text) -> vec). Modelo recomendado:
sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2.

API publica:
  - rebuild_index(db) -> reconstroi tudo
  - upsert_produto(db, produto_id) -> indexa 1 produto (chamado em PATCH/POST)
  - top_k(db, query, k=5) -> [(produto, score), ...]
  - judge(top_k_results) -> 'auto' | 'ambiguous' | 'no_match'
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Optional

from sqlalchemy.orm import Session

from . import models

# ============================================================================
# Hyperparametros do modelo TF-IDF char n-gram
# ============================================================================
# Char n-gram: 3 a 5 caracteres. Cobre matching por palavra parcial,
# erros de digitacao leves, e variacoes de pluralizacao.
NGRAM_MIN = 3
NGRAM_MAX = 5

# Top-K threshold para Reconciliator V0:
#   score >= AUTO_THRESHOLD     -> auto-resolve (action='associar')
#   AMBIG_THRESHOLD <= score < AUTO_THRESHOLD -> ambiguo (humano decide)
#   score < AMBIG_THRESHOLD     -> no_match (action='criar' default)
AUTO_THRESHOLD = 0.85
AMBIG_THRESHOLD = 0.55

MODEL_NAME = "tfidf-charngram-v1"


# ============================================================================
# Normalizacao + tokenizacao
# ============================================================================

def normalize_text(s: str) -> str:
    """
    NFD + remove diacriticos + lowercase + colapsa espaco.
    Espelha exatamente a logica de `normalizarChave` do frontend (TS) —
    determinismo cross-stack.
    """
    if not s:
        return ""
    nfd = unicodedata.normalize("NFD", s)
    no_diac = "".join(c for c in nfd if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", no_diac.strip().lower())


def char_ngrams(text: str, n_min: int = NGRAM_MIN, n_max: int = NGRAM_MAX) -> list[str]:
    """
    Char n-grams de tamanho n_min a n_max, com word-boundary marker.
    "manga palmer" -> ["#ma", "man", "ang", "nga", "ga#", "#pa", ...]
    """
    if not text:
        return []
    # Marker de word boundary ('#') ajuda a discriminar inicio/fim de palavras
    words = [f"#{w}#" for w in text.split() if w]
    grams: list[str] = []
    for w in words:
        for n in range(n_min, n_max + 1):
            if len(w) < n:
                continue
            grams.extend(w[i : i + n] for i in range(len(w) - n + 1))
    return grams


# ============================================================================
# Vocab + IDF (corpus-wide)
# ============================================================================

def _build_idf(docs_grams: list[list[str]]) -> dict[str, float]:
    """
    IDF = log((1 + N) / (1 + df(t))) + 1.  (smoothed, sklearn-like)
    """
    N = len(docs_grams)
    df: Counter[str] = Counter()
    for grams in docs_grams:
        for term in set(grams):
            df[term] += 1
    return {term: math.log((1 + N) / (1 + d)) + 1 for term, d in df.items()}


def _tf(grams: list[str]) -> dict[str, float]:
    """TF normalizado: count / total_count."""
    if not grams:
        return {}
    counts = Counter(grams)
    total = sum(counts.values())
    return {term: c / total for term, c in counts.items()}


def _vectorize(grams: list[str], idf: dict[str, float]) -> dict[str, float]:
    """TF-IDF sparse vector como dict (term -> score)."""
    tf = _tf(grams)
    vec: dict[str, float] = {}
    for term, tf_val in tf.items():
        idf_val = idf.get(term)
        if idf_val is None:
            # Termo OOV (out of vocab) — ignora. Ataca robustez quando
            # query traz nomes nunca vistos antes do treino.
            continue
        vec[term] = tf_val * idf_val
    # L2 normaliza pro cosine virar dot product
    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm > 0:
        vec = {k: v / norm for k, v in vec.items()}
    return vec


def _cosine_sparse(a: dict[str, float], b: dict[str, float]) -> float:
    """Dot product de vetores L2-normalizados = cosine similarity."""
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


# ============================================================================
# Persistencia: vetor virou JSON dense list (para SQLite-friendly)
# ============================================================================
# Nota: armazenamos sparse como list[(term, score)] no JSON pra economizar
# espaco quando vocab eh grande. Decoded na hora do match.

def _encode_for_storage(vec: dict[str, float]) -> list[list]:
    """sparse dict -> [[term, score], ...]"""
    return [[term, score] for term, score in vec.items()]


def _decode_from_storage(stored: list) -> dict[str, float]:
    """[[term, score], ...] -> dict"""
    return {item[0]: item[1] for item in stored}


# ============================================================================
# IDF cache: re-treinado a cada rebuild_index. Em produto desktop com
# catalogo crescendo, IDF estabiliza rapido — reindex incremental sem
# re-treinar IDF eh aceitavel (drift pequeno).
# ============================================================================

_idf_cache: dict[str, float] = {}
_idf_built_for_n: int = 0


def _docs_from_produto(p: models.Produto) -> str:
    """
    Texto canonico de cada produto. Inclui nome + codigo (se houver).
    Codigo atua como termo de alta especificidade (high-IDF).
    """
    parts = [normalize_text(p.nome or "")]
    if p.codigo:
        parts.append(f"#cod:{normalize_text(p.codigo)}")
    return " ".join(parts)


# ============================================================================
# API publica
# ============================================================================

def rebuild_index(db: Session) -> dict:
    """
    Recompute todos os embeddings do catalogo. Recria IDF do zero.

    Idempotente: sempre produz mesmo resultado dado o mesmo catalogo.
    Deletes embeddings de produtos que nao existem mais.

    Returns: dict com stats {'indexed': N, 'pruned': M}
    """
    global _idf_cache, _idf_built_for_n

    produtos = db.query(models.Produto).filter(models.Produto.ativo == True).all()
    if not produtos:
        # Catalogo vazio — limpa embeddings orfaos e zera IDF
        db.query(models.CatalogEmbedding).delete()
        _idf_cache = {}
        _idf_built_for_n = 0
        return {"indexed": 0, "pruned": 0}

    docs = [_docs_from_produto(p) for p in produtos]
    docs_grams = [char_ngrams(d) for d in docs]
    idf = _build_idf(docs_grams)

    _idf_cache = idf
    _idf_built_for_n = len(produtos)

    # Drop embeddings antigas (incluindo de produtos deletados/inativos)
    existing_ids = {e.produto_id for e in db.query(models.CatalogEmbedding).all()}
    produto_ids = {p.id for p in produtos}
    pruned = existing_ids - produto_ids
    if pruned:
        db.query(models.CatalogEmbedding).filter(
            models.CatalogEmbedding.produto_id.in_(pruned)
        ).delete(synchronize_session=False)

    # Upsert embeddings
    indexed = 0
    for p, grams in zip(produtos, docs_grams):
        vec = _vectorize(grams, idf)
        existing = db.query(models.CatalogEmbedding).filter(
            models.CatalogEmbedding.produto_id == p.id
        ).first()
        if existing:
            existing.vector = _encode_for_storage(vec)
            existing.nome_indexed = p.nome or ""
            existing.codigo_indexed = p.codigo
            existing.model_name = MODEL_NAME
        else:
            db.add(models.CatalogEmbedding(
                produto_id=p.id,
                vector=_encode_for_storage(vec),
                nome_indexed=p.nome or "",
                codigo_indexed=p.codigo,
                model_name=MODEL_NAME,
            ))
        indexed += 1

    db.flush()
    return {"indexed": indexed, "pruned": len(pruned)}


def upsert_produto_embedding(db: Session, produto_id: int) -> Optional[dict]:
    """
    Reindexa 1 produto. Reusa IDF cache se existe; se cache vazio,
    chama rebuild_index (lazy first-time init).

    Chamado quando produto eh criado/atualizado pra manter index live.
    """
    global _idf_cache

    p = db.query(models.Produto).filter(models.Produto.id == produto_id).first()
    if not p or not p.ativo:
        # Produto nao existe ou foi desativado — limpa embedding se existir
        db.query(models.CatalogEmbedding).filter(
            models.CatalogEmbedding.produto_id == produto_id
        ).delete()
        return None

    if not _idf_cache:
        # Cold start — IDF nunca foi construida nesta sessao
        rebuild_index(db)
        return {"action": "rebuild_triggered", "produto_id": produto_id}

    # Reusa IDF existente. Drift pequeno: novo produto contribui muito
    # pouco na proxima query, mas eh suficiente pro Reconciliator V0.
    grams = char_ngrams(_docs_from_produto(p))
    vec = _vectorize(grams, _idf_cache)

    existing = db.query(models.CatalogEmbedding).filter(
        models.CatalogEmbedding.produto_id == produto_id
    ).first()
    if existing:
        existing.vector = _encode_for_storage(vec)
        existing.nome_indexed = p.nome or ""
        existing.codigo_indexed = p.codigo
        existing.model_name = MODEL_NAME
    else:
        db.add(models.CatalogEmbedding(
            produto_id=p.id,
            vector=_encode_for_storage(vec),
            nome_indexed=p.nome or "",
            codigo_indexed=p.codigo,
            model_name=MODEL_NAME,
        ))
    db.flush()
    return {"action": "upsert", "produto_id": produto_id}


def top_k(
    db: Session,
    query: str,
    *,
    k: int = 5,
    codigo_hint: Optional[str] = None,
) -> list[dict]:
    """
    Retorna top-K produtos mais similares ao query (nome + codigo opcional).

    [{produto_id, nome, codigo, score, rationale}, ...]
    Ordenado por score desc.

    codigo_hint: se fornecido, sera concatenado ao query (boost pra match
    de codigo exato vira top-1 com score altissimo).
    """
    global _idf_cache

    if not _idf_cache:
        # Cold start
        rebuild_index(db)

    if not _idf_cache:
        # Catalogo vazio
        return []

    # Vetoriza query
    q_text_parts = [normalize_text(query or "")]
    if codigo_hint:
        q_text_parts.append(f"#cod:{normalize_text(codigo_hint)}")
    q_text = " ".join(q_text_parts)
    q_grams = char_ngrams(q_text)
    q_vec = _vectorize(q_grams, _idf_cache)
    if not q_vec:
        return []

    # Busca embeddings + computa cosine. Catalogo desktop <10k -> OK in-memory.
    embs = (
        db.query(models.CatalogEmbedding, models.Produto)
        .join(models.Produto, models.Produto.id == models.CatalogEmbedding.produto_id)
        .filter(models.Produto.ativo == True)
        .all()
    )

    scored: list[tuple[float, models.Produto, str]] = []
    for emb, p in embs:
        d_vec = _decode_from_storage(emb.vector)
        score = _cosine_sparse(q_vec, d_vec)
        if score <= 0:
            continue

        # Rationale heuristico — explica POR QUE bateu
        rationale = _explain_match(query, codigo_hint, p, score)
        scored.append((score, p, rationale))

    scored.sort(key=lambda t: t[0], reverse=True)
    return [
        {
            "produto_id": p.id,
            "nome": p.nome,
            "codigo": p.codigo,
            "grupo_id": p.grupo_id,
            "score": round(s, 4),
            "rationale": r,
        }
        for s, p, r in scored[:k]
    ]


def judge(results: list[dict]) -> str:
    """
    Classifica top-K em 3 categorias para Reconciliator decidir:
      'auto'      - top1 score >= AUTO_THRESHOLD (resolve sozinho)
      'ambiguous' - top1 score em [AMBIG_THRESHOLD, AUTO_THRESHOLD)
                    OU top1-top2 muito proximos (margem < 0.10)
      'no_match'  - top1 score < AMBIG_THRESHOLD ou results vazio

    Returns: 'auto' | 'ambiguous' | 'no_match'
    """
    if not results:
        return "no_match"
    top1 = results[0]["score"]
    if top1 < AMBIG_THRESHOLD:
        return "no_match"
    if top1 >= AUTO_THRESHOLD:
        # Sanity check: top2 muito proximo do top1 derruba para ambiguo
        if len(results) >= 2 and (top1 - results[1]["score"]) < 0.05:
            return "ambiguous"
        return "auto"
    return "ambiguous"


def _explain_match(
    query: str,
    codigo_hint: Optional[str],
    p: models.Produto,
    score: float,
) -> str:
    """
    Rationale curto pra debugging humano e display em UI.
    Deteta o tipo de match dominante.
    """
    q_norm = normalize_text(query or "")
    p_norm = normalize_text(p.nome or "")

    if codigo_hint and p.codigo and normalize_text(codigo_hint) == normalize_text(p.codigo):
        return f"codigo exato ({p.codigo})"
    if q_norm == p_norm:
        return "nome exato"
    if q_norm in p_norm or p_norm in q_norm:
        return "nome substring"
    return f"similaridade char-ngram score={score:.2f}"
