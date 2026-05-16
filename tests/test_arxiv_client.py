"""arxiv_client.py 测试 — 只测离线逻辑，不打真实 API。"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from arxiv_client import (
    ArxivClient,
    Paper,
    SemanticScholarClient,
    _arxiv_to_paper,
    enrich_with_semantic_scholar,
)


class _FakeArxivResult:
    """模拟 arxiv 包返回的 Result 对象。"""

    def __init__(
        self,
        entry_id: str = "http://arxiv.org/abs/2401.12345v1",
        title: str = "Test",
        summary: str = "abstract",
        authors=None,
        published: datetime = datetime(2024, 1, 5),
        categories=None,
        pdf_url: str = "http://arxiv.org/pdf/2401.12345",
        primary_category: str = "cs.LG",
    ):
        self.entry_id = entry_id
        self.title = title
        self.summary = summary
        self.authors = authors or [MagicMock(name="John Doe")]
        for a in self.authors:
            a.name = getattr(a, "name", "Author")
        self.published = published
        self.categories = categories or ["cs.LG", "stat.ML"]
        self.pdf_url = pdf_url
        self.primary_category = primary_category


def test_arxiv_to_paper_strips_version_suffix():
    r = _FakeArxivResult(entry_id="http://arxiv.org/abs/2401.12345v3")
    p = _arxiv_to_paper(r)
    assert p.arxiv_id == "2401.12345"


def test_arxiv_to_paper_extracts_authors():
    a1 = MagicMock(); a1.name = "Alice"
    a2 = MagicMock(); a2.name = "Bob"
    r = _FakeArxivResult(authors=[a1, a2])
    p = _arxiv_to_paper(r)
    assert p.authors == ["Alice", "Bob"]


def test_arxiv_search_filters_by_date():
    with patch("arxiv_client.arxiv.Client") as MockClient:
        instance = MockClient.return_value
        # 三篇论文，日期分别在前/中/后
        instance.results.return_value = iter([
            _FakeArxivResult(published=datetime(2024, 1, 1)),
            _FakeArxivResult(published=datetime(2024, 6, 1)),
            _FakeArxivResult(published=datetime(2024, 12, 1)),
        ])
        c = ArxivClient()
        out = c.search("foo", max_results=10, after=datetime(2024, 5, 1))
        assert len(out) == 2
        assert all(p.published >= datetime(2024, 5, 1) for p in out)


def test_arxiv_search_respects_max_results():
    with patch("arxiv_client.arxiv.Client") as MockClient:
        instance = MockClient.return_value
        instance.results.return_value = iter([_FakeArxivResult() for _ in range(20)])
        c = ArxivClient()
        out = c.search("foo", max_results=5)
        assert len(out) == 5


@patch("arxiv_client.time.sleep")
@patch("arxiv_client.requests.Session.get")
def test_semantic_scholar_returns_none_on_404(mock_get, _mock_sleep):
    mock_get.return_value = MagicMock(status_code=404)
    s2 = SemanticScholarClient()
    assert s2.get_by_arxiv("2401.99999") is None


@patch("arxiv_client.time.sleep")
@patch("arxiv_client.requests.Session.get")
def test_semantic_scholar_parses_json(mock_get, _mock_sleep):
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {
        "paperId": "abc123",
        "title": "Test",
        "year": 2024,
        "venue": "NeurIPS",
        "citationCount": 42,
        "referenceCount": 30,
        "influentialCitationCount": 5,
    }
    mock_get.return_value = mock_response
    s2 = SemanticScholarClient()
    data = s2.get_by_arxiv("2401.00001")
    assert data["citationCount"] == 42
    assert data["venue"] == "NeurIPS"


@patch("arxiv_client.time.sleep")
@patch("arxiv_client.requests.Session.get")
def test_enrich_with_semantic_scholar(mock_get, _mock_sleep):
    mock_response = MagicMock(status_code=200)
    mock_response.json.return_value = {
        "paperId": "abc",
        "year": 2024,
        "venue": "ICLR",
        "citationCount": 100,
        "referenceCount": 50,
        "influentialCitationCount": 10,
    }
    mock_get.return_value = mock_response

    papers = [
        Paper(
            arxiv_id="2401.00001",
            title="t",
            abstract="a",
            authors=[],
            published=datetime(2024, 1, 1),
        )
    ]
    enrich_with_semantic_scholar(papers, client=SemanticScholarClient())
    assert papers[0].citation_count == 100
    assert papers[0].venue == "ICLR"
    assert papers[0].year == 2024
