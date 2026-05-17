"""vector_store.py 测试 — TF-IDF 检索逻辑。"""
from datetime import datetime

import pytest

from arxiv_client import Paper
from vector_store import TfidfStore, make_default_store


def _p(arxiv_id: str, title: str, abstract: str = "") -> Paper:
    return Paper(
        arxiv_id=arxiv_id,
        title=title,
        abstract=abstract,
        authors=[],
        published=datetime(2024, 1, 1),
        categories=["cs.CL"],
    )


@pytest.fixture
def corpus():
    return [
        _p("2401.00001", "Retrieval Augmented Generation for LLMs",
           "RAG combines parametric and non-parametric memory to improve factuality."),
        _p("2401.00002", "Direct Preference Optimization",
           "DPO trains language models without explicit reward modeling."),
        _p("2401.00003", "Sparse Mixture of Experts",
           "MoE models scale capacity with conditional computation."),
        _p("2401.00004", "Mamba: Selective State Space Models",
           "Linear-time sequence modeling with selective mechanisms."),
        _p("2401.00005", "Tree-of-Thoughts Reasoning",
           "Deliberate problem solving with LLMs by exploring intermediate reasoning steps."),
    ]


def test_empty_store_returns_no_hits():
    s = TfidfStore()
    assert s.query("anything", k=5) == []
    assert s.size() == 0


def test_query_returns_top_k(corpus):
    s = TfidfStore()
    s.add(corpus)
    hits = s.query("retrieval augmented generation", k=3)
    assert len(hits) == 3
    assert hits[0][0].arxiv_id == "2401.00001"
    # 分数应单调递减
    assert hits[0][1] >= hits[1][1] >= hits[2][1]


def test_query_lexical_match(corpus):
    s = TfidfStore()
    s.add(corpus)
    hits = s.query("preference optimization", k=2)
    assert hits[0][0].arxiv_id == "2401.00002"


def test_incremental_add(corpus):
    s = TfidfStore()
    s.add(corpus[:3])
    assert s.size() == 3
    s.add(corpus[3:])
    assert s.size() == 5
    hits = s.query("mamba state space", k=1)
    assert hits[0][0].arxiv_id == "2401.00004"


def test_make_default_store_returns_tfidf():
    s = make_default_store(prefer_embeddings=False)
    assert isinstance(s, TfidfStore)


def test_make_default_falls_back_when_chroma_missing():
    # 不强求装 chroma；这里只要求 prefer_embeddings=True 不抛异常
    try:
        s = make_default_store(prefer_embeddings=True)
        # 装了就用 ChromaEmbeddingStore，没装就回退 TfidfStore，两种都接受
        assert s is not None
    except Exception as e:
        pytest.fail(f"应当优雅回退而不是抛异常: {e}")
