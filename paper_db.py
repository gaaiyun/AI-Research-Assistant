"""
论文本地持久化 — SQLite。

为什么用 SQLite？
- 内置 stdlib，零依赖
- 文件一份，方便备份、跨设备同步
- 足够支撑万级别论文

数据库设计
---------
papers
    arxiv_id PRIMARY KEY
    title, abstract, authors_json, primary_category, categories_json
    published_at, pdf_url
    citation_count, reference_count, influential_citation_count
    venue, year
    fetched_at, last_seen_at

reading_status
    arxiv_id FK, status ('queued' | 'reading' | 'done' | 'skip'), notes, updated_at

tags  (用户自定义标签)
    arxiv_id FK, tag, created_at
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

from arxiv_client import Paper


_SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    arxiv_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    abstract TEXT,
    authors_json TEXT,
    primary_category TEXT,
    categories_json TEXT,
    published_at TEXT,
    pdf_url TEXT,
    semantic_scholar_id TEXT,
    citation_count INTEGER,
    reference_count INTEGER,
    influential_citation_count INTEGER,
    venue TEXT,
    year INTEGER,
    fetched_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);
CREATE INDEX IF NOT EXISTS idx_papers_primary_category ON papers(primary_category);
CREATE INDEX IF NOT EXISTS idx_papers_citation_count ON papers(citation_count);

CREATE TABLE IF NOT EXISTS reading_status (
    arxiv_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(status IN ('queued','reading','done','skip')),
    notes TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (arxiv_id) REFERENCES papers(arxiv_id)
);

CREATE TABLE IF NOT EXISTS tags (
    arxiv_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (arxiv_id, tag),
    FOREIGN KEY (arxiv_id) REFERENCES papers(arxiv_id)
);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
"""


@dataclass
class ReadingNote:
    arxiv_id: str
    status: str
    notes: str = ""
    updated_at: Optional[datetime] = None


class PaperDB:
    """轻量持久化层。"""

    def __init__(self, path: str | Path = "papers.sqlite"):
        self.path = Path(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(_SCHEMA)

    # ---------- papers ----------

    def upsert(self, papers: Iterable[Paper]) -> int:
        now = datetime.now().isoformat()
        rows = []
        for p in papers:
            rows.append(
                (
                    p.arxiv_id,
                    p.title,
                    p.abstract,
                    json.dumps(p.authors, ensure_ascii=False),
                    p.primary_category,
                    json.dumps(p.categories, ensure_ascii=False),
                    p.published.isoformat() if p.published else None,
                    p.pdf_url,
                    p.semantic_scholar_id,
                    p.citation_count,
                    p.reference_count,
                    p.influential_citation_count,
                    p.venue,
                    p.year,
                    now,
                    now,
                )
            )
        if not rows:
            return 0
        with self._conn:
            self._conn.executemany(
                """
                INSERT INTO papers
                    (arxiv_id, title, abstract, authors_json, primary_category,
                     categories_json, published_at, pdf_url, semantic_scholar_id,
                     citation_count, reference_count, influential_citation_count,
                     venue, year, fetched_at, last_seen_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(arxiv_id) DO UPDATE SET
                    title=excluded.title,
                    abstract=excluded.abstract,
                    authors_json=excluded.authors_json,
                    primary_category=excluded.primary_category,
                    categories_json=excluded.categories_json,
                    published_at=excluded.published_at,
                    pdf_url=excluded.pdf_url,
                    semantic_scholar_id=COALESCE(excluded.semantic_scholar_id, papers.semantic_scholar_id),
                    citation_count=COALESCE(excluded.citation_count, papers.citation_count),
                    reference_count=COALESCE(excluded.reference_count, papers.reference_count),
                    influential_citation_count=COALESCE(excluded.influential_citation_count, papers.influential_citation_count),
                    venue=COALESCE(excluded.venue, papers.venue),
                    year=COALESCE(excluded.year, papers.year),
                    last_seen_at=excluded.last_seen_at
                """,
                rows,
            )
        return len(rows)

    def get(self, arxiv_id: str) -> Optional[Paper]:
        cur = self._conn.execute(
            "SELECT * FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        )
        row = cur.fetchone()
        return _row_to_paper(row) if row else None

    def all(self, limit: int = 1000) -> List[Paper]:
        cur = self._conn.execute(
            "SELECT * FROM papers ORDER BY published_at DESC LIMIT ?", (limit,)
        )
        return [_row_to_paper(r) for r in cur.fetchall()]

    def count(self) -> int:
        cur = self._conn.execute("SELECT COUNT(*) FROM papers")
        return cur.fetchone()[0]

    def search_title(self, q: str, limit: int = 50) -> List[Paper]:
        cur = self._conn.execute(
            "SELECT * FROM papers WHERE title LIKE ? ORDER BY citation_count DESC NULLS LAST LIMIT ?",
            (f"%{q}%", limit),
        )
        return [_row_to_paper(r) for r in cur.fetchall()]

    # ---------- reading status ----------

    def set_status(self, arxiv_id: str, status: str, notes: str = "") -> None:
        if status not in ("queued", "reading", "done", "skip"):
            raise ValueError(f"未知 status: {status}")
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO reading_status (arxiv_id, status, notes, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(arxiv_id) DO UPDATE SET
                    status=excluded.status,
                    notes=COALESCE(NULLIF(excluded.notes, ''), reading_status.notes),
                    updated_at=excluded.updated_at
                """,
                (arxiv_id, status, notes, datetime.now().isoformat()),
            )

    def get_status(self, arxiv_id: str) -> Optional[ReadingNote]:
        cur = self._conn.execute(
            "SELECT arxiv_id, status, notes, updated_at FROM reading_status WHERE arxiv_id = ?",
            (arxiv_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return ReadingNote(
            arxiv_id=row["arxiv_id"],
            status=row["status"],
            notes=row["notes"] or "",
            updated_at=datetime.fromisoformat(row["updated_at"]) if row["updated_at"] else None,
        )

    def list_by_status(self, status: str) -> List[Paper]:
        cur = self._conn.execute(
            """
            SELECT p.* FROM papers p
            JOIN reading_status rs ON p.arxiv_id = rs.arxiv_id
            WHERE rs.status = ?
            ORDER BY rs.updated_at DESC
            """,
            (status,),
        )
        return [_row_to_paper(r) for r in cur.fetchall()]

    # ---------- tags ----------

    def add_tag(self, arxiv_id: str, tag: str) -> None:
        with self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO tags (arxiv_id, tag, created_at)
                VALUES (?, ?, ?)
                """,
                (arxiv_id, tag.strip().lower(), datetime.now().isoformat()),
            )

    def remove_tag(self, arxiv_id: str, tag: str) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM tags WHERE arxiv_id=? AND tag=?",
                (arxiv_id, tag.strip().lower()),
            )

    def list_by_tag(self, tag: str) -> List[Paper]:
        cur = self._conn.execute(
            """
            SELECT p.* FROM papers p
            JOIN tags t ON p.arxiv_id = t.arxiv_id
            WHERE t.tag = ?
            ORDER BY p.year DESC NULLS LAST
            """,
            (tag.strip().lower(),),
        )
        return [_row_to_paper(r) for r in cur.fetchall()]

    def tags_of(self, arxiv_id: str) -> List[str]:
        cur = self._conn.execute(
            "SELECT tag FROM tags WHERE arxiv_id=? ORDER BY created_at", (arxiv_id,)
        )
        return [r["tag"] for r in cur.fetchall()]

    # ---------- bookkeeping ----------

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def transaction(self):
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise


def _row_to_paper(row: sqlite3.Row) -> Paper:
    return Paper(
        arxiv_id=row["arxiv_id"],
        title=row["title"],
        abstract=row["abstract"] or "",
        authors=json.loads(row["authors_json"]) if row["authors_json"] else [],
        published=datetime.fromisoformat(row["published_at"]) if row["published_at"] else datetime.min,
        categories=json.loads(row["categories_json"]) if row["categories_json"] else [],
        pdf_url=row["pdf_url"],
        primary_category=row["primary_category"],
        semantic_scholar_id=row["semantic_scholar_id"],
        citation_count=row["citation_count"],
        reference_count=row["reference_count"],
        influential_citation_count=row["influential_citation_count"],
        venue=row["venue"],
        year=row["year"],
    )
