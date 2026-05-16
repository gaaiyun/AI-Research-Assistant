"""
arXiv + Semantic Scholar 统一客户端。

为什么不能只用 arXiv API？
------------------------
arXiv API 提供论文元数据 + PDF 链接，但没有：

- 引用关系（谁引了谁）
- 作者识别符（同名作者消歧）
- 发表场所（venue, conference）
- 影响力指标（citation count）

Semantic Scholar 的 Graph API（免费、不需 key、有限速）补齐了这些。
本模块把两者结合在一起：

- `search(query)` → arXiv 搜索（按提交时间排序，方便看最新进展）
- `enrich(arxiv_id)` → Semantic Scholar 补全 citation 和 reference

API doc:
- arXiv: https://info.arxiv.org/help/api/user-manual.html
- Semantic Scholar: https://api.semanticscholar.org/api-docs/graph
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterator, List, Optional

import arxiv
import requests


log = logging.getLogger(__name__)

# Semantic Scholar 公开 API，建议轮询间隔 >= 1s
_S2_BASE = "https://api.semanticscholar.org/graph/v1"
_S2_TIMEOUT = 15
_S2_MIN_INTERVAL = 1.05  # 秒，略多于 1s 以保险


@dataclass
class Paper:
    """统一论文记录。"""

    arxiv_id: str
    title: str
    abstract: str
    authors: List[str]
    published: datetime
    categories: List[str] = field(default_factory=list)
    pdf_url: Optional[str] = None
    primary_category: Optional[str] = None

    # Semantic Scholar 补全字段
    semantic_scholar_id: Optional[str] = None
    citation_count: Optional[int] = None
    reference_count: Optional[int] = None
    venue: Optional[str] = None
    year: Optional[int] = None
    influential_citation_count: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "arxiv_id": self.arxiv_id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "published": self.published.isoformat(),
            "categories": self.categories,
            "pdf_url": self.pdf_url,
            "primary_category": self.primary_category,
            "semantic_scholar_id": self.semantic_scholar_id,
            "citation_count": self.citation_count,
            "reference_count": self.reference_count,
            "venue": self.venue,
            "year": self.year,
            "influential_citation_count": self.influential_citation_count,
        }


class ArxivClient:
    """对 `arxiv` 包的薄包装，返回我们自己的 Paper dataclass。"""

    def __init__(self, page_size: int = 100, delay_seconds: float = 3.0):
        self._client = arxiv.Client(page_size=page_size, delay_seconds=delay_seconds)

    def search(
        self,
        query: str,
        max_results: int = 50,
        sort_by: str = "submitted_date",
        sort_order: str = "desc",
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
    ) -> List[Paper]:
        """同步返回 `max_results` 条匹配的论文。"""
        sort_map = {
            "relevance": arxiv.SortCriterion.Relevance,
            "last_updated": arxiv.SortCriterion.LastUpdatedDate,
            "submitted_date": arxiv.SortCriterion.SubmittedDate,
        }
        order_map = {"asc": arxiv.SortOrder.Ascending, "desc": arxiv.SortOrder.Descending}
        search = arxiv.Search(
            query=query,
            max_results=max_results * 3 if (after or before) else max_results,
            sort_by=sort_map.get(sort_by, arxiv.SortCriterion.SubmittedDate),
            sort_order=order_map.get(sort_order, arxiv.SortOrder.Descending),
        )

        out: List[Paper] = []
        for r in self._client.results(search):
            if after and r.published.replace(tzinfo=None) < after:
                continue
            if before and r.published.replace(tzinfo=None) > before:
                continue
            out.append(_arxiv_to_paper(r))
            if len(out) >= max_results:
                break
        return out

    def get_by_id(self, arxiv_id: str) -> Optional[Paper]:
        search = arxiv.Search(id_list=[arxiv_id])
        try:
            r = next(self._client.results(search))
            return _arxiv_to_paper(r)
        except StopIteration:
            return None


def _arxiv_to_paper(r: "arxiv.Result") -> Paper:
    return Paper(
        arxiv_id=r.entry_id.rsplit("/", 1)[-1].split("v")[0],
        title=r.title.strip().replace("\n", " "),
        abstract=r.summary.strip().replace("\n", " "),
        authors=[a.name for a in r.authors],
        published=r.published.replace(tzinfo=None),
        categories=list(r.categories),
        pdf_url=r.pdf_url,
        primary_category=r.primary_category,
    )


class SemanticScholarClient:
    """Semantic Scholar Graph API 的最小封装。"""

    def __init__(self, timeout: float = _S2_TIMEOUT):
        self._last_call_ts = 0.0
        self._timeout = timeout
        self._session = requests.Session()

    def _throttle(self) -> None:
        """简易速率控制（公开 API 无 key 时建议 1 req/s）。"""
        now = time.monotonic()
        sleep_for = _S2_MIN_INTERVAL - (now - self._last_call_ts)
        if sleep_for > 0:
            time.sleep(sleep_for)
        self._last_call_ts = time.monotonic()

    def get_by_arxiv(self, arxiv_id: str) -> Optional[dict]:
        """以 arXiv:<id> 查询 Semantic Scholar。"""
        self._throttle()
        fields = "paperId,title,year,venue,citationCount,referenceCount,influentialCitationCount"
        url = f"{_S2_BASE}/paper/arXiv:{arxiv_id}"
        try:
            r = self._session.get(url, params={"fields": fields}, timeout=self._timeout)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                log.warning("Semantic Scholar rate limit hit, sleeping 5s")
                time.sleep(5)
                return self.get_by_arxiv(arxiv_id)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            log.warning("S2 request failed for %s: %s", arxiv_id, e)
            return None

    def references(self, paper_id: str, limit: int = 50) -> List[dict]:
        """获取一篇论文引用的（被引）参考文献列表。"""
        self._throttle()
        url = f"{_S2_BASE}/paper/{paper_id}/references"
        try:
            r = self._session.get(
                url,
                params={"limit": limit, "fields": "title,year,venue,citationCount"},
                timeout=self._timeout,
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            return [item.get("citedPaper", {}) for item in data]
        except requests.RequestException as e:
            log.warning("S2 references failed for %s: %s", paper_id, e)
            return []

    def citations(self, paper_id: str, limit: int = 50) -> List[dict]:
        """获取引用该论文的论文列表（forward citations）。"""
        self._throttle()
        url = f"{_S2_BASE}/paper/{paper_id}/citations"
        try:
            r = self._session.get(
                url,
                params={"limit": limit, "fields": "title,year,venue,citationCount"},
                timeout=self._timeout,
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            return [item.get("citingPaper", {}) for item in data]
        except requests.RequestException as e:
            log.warning("S2 citations failed for %s: %s", paper_id, e)
            return []


def enrich_with_semantic_scholar(papers: List[Paper], client: Optional[SemanticScholarClient] = None) -> List[Paper]:
    """对一批 Paper 调 Semantic Scholar 补字段。原地修改并返回。"""
    s2 = client or SemanticScholarClient()
    for p in papers:
        meta = s2.get_by_arxiv(p.arxiv_id)
        if meta is None:
            continue
        p.semantic_scholar_id = meta.get("paperId")
        p.citation_count = meta.get("citationCount")
        p.reference_count = meta.get("referenceCount")
        p.influential_citation_count = meta.get("influentialCitationCount")
        p.venue = meta.get("venue")
        p.year = meta.get("year")
    return papers


def stream_search(
    query: str,
    max_results: int = 200,
    enrich: bool = False,
) -> Iterator[Paper]:
    """便利函数：流式 yield 论文（不一次性等所有）。"""
    client = ArxivClient()
    s2 = SemanticScholarClient() if enrich else None
    batch = client.search(query=query, max_results=max_results)
    for p in batch:
        if enrich and s2:
            meta = s2.get_by_arxiv(p.arxiv_id)
            if meta:
                p.citation_count = meta.get("citationCount")
                p.year = meta.get("year")
                p.venue = meta.get("venue")
        yield p
