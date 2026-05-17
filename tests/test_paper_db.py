"""paper_db.py 测试 — SQLite 持久化。"""
from datetime import datetime
from pathlib import Path

import pytest

from arxiv_client import Paper
from paper_db import PaperDB


def _make_paper(arxiv_id: str = "2401.00001", **overrides) -> Paper:
    defaults = dict(
        arxiv_id=arxiv_id,
        title="Test Paper",
        abstract="An abstract.",
        authors=["Alice", "Bob"],
        published=datetime(2024, 1, 1, 12, 0, 0),
        categories=["cs.LG", "stat.ML"],
        pdf_url="https://arxiv.org/pdf/2401.00001",
        primary_category="cs.LG",
    )
    defaults.update(overrides)
    return Paper(**defaults)


@pytest.fixture
def db(tmp_path: Path) -> PaperDB:
    return PaperDB(tmp_path / "test.sqlite")


def test_upsert_and_get(db: PaperDB):
    p = _make_paper()
    assert db.upsert([p]) == 1
    fetched = db.get(p.arxiv_id)
    assert fetched is not None
    assert fetched.title == "Test Paper"
    assert fetched.authors == ["Alice", "Bob"]
    assert fetched.categories == ["cs.LG", "stat.ML"]
    assert db.count() == 1


def test_upsert_updates_existing(db: PaperDB):
    p = _make_paper()
    db.upsert([p])
    p2 = _make_paper(title="Updated Title", citation_count=42)
    db.upsert([p2])
    fetched = db.get(p.arxiv_id)
    assert fetched.title == "Updated Title"
    assert fetched.citation_count == 42
    assert db.count() == 1


def test_upsert_preserves_existing_optional_fields(db: PaperDB):
    """二次 upsert 时，若新记录的 venue/citation_count 是 None，应保留旧值。"""
    db.upsert([_make_paper(citation_count=100, venue="NeurIPS", year=2024)])
    db.upsert([_make_paper(title="Refreshed")])  # 没传 citation_count / venue
    fetched = db.get("2401.00001")
    assert fetched.title == "Refreshed"
    assert fetched.citation_count == 100
    assert fetched.venue == "NeurIPS"
    assert fetched.year == 2024


def test_search_title(db: PaperDB):
    db.upsert([
        _make_paper(arxiv_id="2401.00001", title="LLM alignment via RLHF"),
        _make_paper(arxiv_id="2401.00002", title="CNN for image classification"),
        _make_paper(arxiv_id="2401.00003", title="LLM safety benchmark"),
    ])
    hits = db.search_title("LLM")
    assert len(hits) == 2
    titles = {h.title for h in hits}
    assert titles == {"LLM alignment via RLHF", "LLM safety benchmark"}


def test_reading_status_workflow(db: PaperDB):
    db.upsert([_make_paper()])
    assert db.get_status("2401.00001") is None
    db.set_status("2401.00001", "reading", notes="第 3 章 unclear")
    note = db.get_status("2401.00001")
    assert note.status == "reading"
    assert "unclear" in note.notes

    db.set_status("2401.00001", "done")
    note = db.get_status("2401.00001")
    assert note.status == "done"
    # 空 notes 不应覆盖原 notes
    assert "unclear" in note.notes


def test_invalid_status_raises(db: PaperDB):
    db.upsert([_make_paper()])
    with pytest.raises(ValueError):
        db.set_status("2401.00001", "foo")


def test_list_by_status(db: PaperDB):
    db.upsert([
        _make_paper(arxiv_id=f"2401.{i:05d}") for i in range(1, 5)
    ])
    db.set_status("2401.00001", "queued")
    db.set_status("2401.00002", "queued")
    db.set_status("2401.00003", "done")

    queued = db.list_by_status("queued")
    assert {p.arxiv_id for p in queued} == {"2401.00001", "2401.00002"}


def test_tags(db: PaperDB):
    db.upsert([_make_paper()])
    db.add_tag("2401.00001", "LLM")
    db.add_tag("2401.00001", "Alignment")
    db.add_tag("2401.00001", "LLM")  # 重复，应被忽略
    assert sorted(db.tags_of("2401.00001")) == ["alignment", "llm"]

    db.remove_tag("2401.00001", "LLM")
    assert db.tags_of("2401.00001") == ["alignment"]


def test_list_by_tag(db: PaperDB):
    db.upsert([
        _make_paper(arxiv_id="2401.00001"),
        _make_paper(arxiv_id="2401.00002"),
    ])
    db.add_tag("2401.00001", "rag")
    db.add_tag("2401.00002", "rag")
    hits = db.list_by_tag("rag")
    assert {p.arxiv_id for p in hits} == {"2401.00001", "2401.00002"}


def test_persistence_across_sessions(tmp_path: Path):
    path = tmp_path / "persist.sqlite"
    db1 = PaperDB(path)
    db1.upsert([_make_paper()])
    db1.set_status("2401.00001", "reading")
    db1.add_tag("2401.00001", "rag")
    db1.close()

    db2 = PaperDB(path)
    assert db2.count() == 1
    assert db2.get_status("2401.00001").status == "reading"
    assert db2.tags_of("2401.00001") == ["rag"]
