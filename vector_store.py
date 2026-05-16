"""
论文语义检索 — 抽象的向量索引。

默认实现：TF-IDF（轻量，纯 scikit-learn）。
高级实现：sentence-transformers + ChromaDB（向量模型 + 持久化）。

为什么不用 ElasticSearch / Pinecone？
-----------------------------------
- 学术论文场景下，数据量通常在 1k~100k 篇，TF-IDF 已经够好
- 给"我家电脑没 GPU"的用户兜底
- 同时提供升级路径

使用
----
>>> from arxiv_client import ArxivClient
>>> from vector_store import TfidfStore
>>>
>>> papers = ArxivClient().search("retrieval augmented generation", max_results=50)
>>> store = TfidfStore()
>>> store.add(papers)
>>> hits = store.query("how to ground LLM answers with citations", k=5)
>>> for paper, score in hits:
...     print(score, paper.title)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from arxiv_client import Paper


log = logging.getLogger(__name__)


class VectorStore(ABC):
    """对所有向量检索后端统一接口。"""

    @abstractmethod
    def add(self, papers: Sequence[Paper]) -> None: ...
    @abstractmethod
    def query(self, q: str, k: int = 5) -> List[Tuple[Paper, float]]: ...
    @abstractmethod
    def size(self) -> int: ...


@dataclass
class _IndexedPaper:
    paper: Paper
    text: str  # 用于检索的拼接文本


# ----------------------------------------------------------------------------
# TF-IDF backend（默认）
# ----------------------------------------------------------------------------

class TfidfStore(VectorStore):
    """
    用 TF-IDF 做相似度检索。

    Parameters
    ----------
    ngram_range : tuple[int, int]
        n-gram 范围。默认 (1, 2) 兼顾召回率与精度。
    min_df, max_df : int / float
        词频过滤参数（剔除超低频与超高频词）。
    """

    def __init__(self, ngram_range: Tuple[int, int] = (1, 2),
                 min_df: int | float = 1, max_df: float = 0.95):
        self._items: List[_IndexedPaper] = []
        self._vectorizer = TfidfVectorizer(
            ngram_range=ngram_range,
            min_df=min_df,
            max_df=max_df,
            lowercase=True,
            stop_words="english",
        )
        self._matrix = None
        self._dirty = True

    def add(self, papers: Sequence[Paper]) -> None:
        for p in papers:
            text = self._make_text(p)
            self._items.append(_IndexedPaper(paper=p, text=text))
        self._dirty = True

    def query(self, q: str, k: int = 5) -> List[Tuple[Paper, float]]:
        if not self._items:
            return []
        self._reindex_if_needed()
        q_vec = self._vectorizer.transform([q])
        sims = cosine_similarity(q_vec, self._matrix).ravel()
        top_idx = np.argsort(sims)[::-1][:k]
        return [(self._items[i].paper, float(sims[i])) for i in top_idx]

    def size(self) -> int:
        return len(self._items)

    def _reindex_if_needed(self) -> None:
        if not self._dirty:
            return
        self._matrix = self._vectorizer.fit_transform(
            [it.text for it in self._items]
        )
        self._dirty = False

    @staticmethod
    def _make_text(p: Paper) -> str:
        return f"{p.title}\n{p.abstract}\n{' '.join(p.categories)}"


# ----------------------------------------------------------------------------
# Sentence-Transformers + ChromaDB（可选升级）
# ----------------------------------------------------------------------------

class ChromaEmbeddingStore(VectorStore):
    """
    用 sentence-transformers 做嵌入 + ChromaDB 做持久化。

    安装：
        pip install sentence-transformers chromadb

    与 TfidfStore 的差异：
    - 语义检索：可以查到不共享关键词但语义相近的论文
    - 持久化：可以在多次会话之间复用索引
    - 计算成本：第一次嵌入慢（CPU 下约 30 docs/sec），需要 ~500MB 模型权重

    Parameters
    ----------
    persist_dir : str | None
        持久化目录。None 表示内存模式（程序退出即丢失）。
    model_name : str
        sentence-transformers 模型名。默认 "all-MiniLM-L6-v2"（384 维，22M
        参数，速度快、效果还行）。学术场景建议 "allenai/specter2" 或
        "sentence-transformers/all-mpnet-base-v2"。
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        collection_name: str = "papers",
    ):
        try:
            import chromadb
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                "ChromaEmbeddingStore 需要安装可选依赖："
                "pip install sentence-transformers chromadb"
            ) from e

        self._model = SentenceTransformer(model_name)
        if persist_dir:
            self._client = chromadb.PersistentClient(path=persist_dir)
        else:
            self._client = chromadb.EphemeralClient()
        # get_or_create_collection 在 chromadb >= 0.4
        self._collection = self._client.get_or_create_collection(name=collection_name)
        self._papers_by_id: dict[str, Paper] = {}

    def add(self, papers: Sequence[Paper]) -> None:
        new_papers = [p for p in papers if p.arxiv_id not in self._papers_by_id]
        if not new_papers:
            return
        ids = [p.arxiv_id for p in new_papers]
        texts = [self._make_text(p) for p in new_papers]
        embeds = self._model.encode(texts, normalize_embeddings=True).tolist()
        metas = [{"title": p.title, "year": p.year or 0} for p in new_papers]
        self._collection.add(ids=ids, embeddings=embeds, documents=texts, metadatas=metas)
        for p in new_papers:
            self._papers_by_id[p.arxiv_id] = p

    def query(self, q: str, k: int = 5) -> List[Tuple[Paper, float]]:
        if not self._papers_by_id:
            return []
        q_vec = self._model.encode([q], normalize_embeddings=True).tolist()[0]
        res = self._collection.query(query_embeddings=[q_vec], n_results=k)
        hits: List[Tuple[Paper, float]] = []
        for arxiv_id, dist in zip(res["ids"][0], res["distances"][0]):
            paper = self._papers_by_id.get(arxiv_id)
            if paper is None:
                continue
            # Chroma 默认返回距离（越小越近），转成相似度（越大越近）
            similarity = max(0.0, 1.0 - dist)
            hits.append((paper, similarity))
        return hits

    def size(self) -> int:
        return len(self._papers_by_id)

    @staticmethod
    def _make_text(p: Paper) -> str:
        return f"{p.title}. {p.abstract}"


def make_default_store(prefer_embeddings: bool = False, **kwargs) -> VectorStore:
    """工厂函数：默认返回 TF-IDF，加 `prefer_embeddings=True` 才尝试 chroma。"""
    if prefer_embeddings:
        try:
            return ChromaEmbeddingStore(**kwargs)
        except ImportError:
            log.warning("Chroma + sentence-transformers 未安装，回退到 TF-IDF")
    return TfidfStore()
