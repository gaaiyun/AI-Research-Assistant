"""
命令行入口 — 用 stdlib argparse，不依赖额外 CLI 框架。

用法
----
$ python cli.py search "retrieval augmented generation" --max 30 --enrich --save
$ python cli.py find "how to do RAG with citations" --k 5
$ python cli.py status 2410.12345 reading
$ python cli.py tag 2410.12345 add llm rag
$ python cli.py list --status queued
$ python cli.py info 2410.12345

设计原则
-------
- 所有命令都用同一个 papers.sqlite 数据库
- 不联网命令（list/info/find）速度都在 <1s，便于做日常工作流
- search 默认不 enrich Semantic Scholar，避免新手等很久；加 --enrich 打开
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List

from arxiv_client import ArxivClient, SemanticScholarClient, enrich_with_semantic_scholar
from paper_db import PaperDB
from vector_store import TfidfStore


DEFAULT_DB = "papers.sqlite"


def _open_db(args) -> PaperDB:
    return PaperDB(args.db)


# ----------------------------------------------------------------------------
# search
# ----------------------------------------------------------------------------

def cmd_search(args) -> int:
    client = ArxivClient()
    papers = client.search(query=args.query, max_results=args.max)
    if args.enrich:
        s2 = SemanticScholarClient()
        enrich_with_semantic_scholar(papers, client=s2)

    if args.save:
        db = _open_db(args)
        n = db.upsert(papers)
        db.close()
        print(f"[saved] {n} papers → {args.db}", file=sys.stderr)

    _print_papers(papers, show_index=True, format=args.format)
    return 0


def _print_papers(papers, show_index: bool = False, format: str = "compact") -> None:
    if format == "json":
        print(json.dumps([p.to_dict() for p in papers], ensure_ascii=False, indent=2))
        return
    for i, p in enumerate(papers, start=1):
        prefix = f"{i:>3}. " if show_index else ""
        cite = f" [{p.citation_count} cites]" if p.citation_count is not None else ""
        ven = f" — {p.venue} ({p.year})" if p.venue else (f" — {p.year}" if p.year else "")
        print(f"{prefix}{p.arxiv_id}{cite}{ven}")
        print(f"     {p.title}")
        print(f"     {', '.join(p.authors[:3])}{'…' if len(p.authors) > 3 else ''}")
        if format == "verbose":
            print(f"     {p.abstract[:200]}…")
        print()


# ----------------------------------------------------------------------------
# find（语义检索，已 saved 的论文）
# ----------------------------------------------------------------------------

def cmd_find(args) -> int:
    db = _open_db(args)
    papers = db.all(limit=10_000)
    if not papers:
        print("数据库为空。先用 `search ... --save` 添加论文。", file=sys.stderr)
        return 1
    store = TfidfStore()
    store.add(papers)
    hits = store.query(args.query, k=args.k)
    if not hits:
        print("无匹配。")
        return 0
    print(f"前 {len(hits)} 个匹配：")
    for paper, score in hits:
        print(f"  [{score:.3f}] {paper.arxiv_id}  {paper.title}")
    return 0


# ----------------------------------------------------------------------------
# status & tag & list & info
# ----------------------------------------------------------------------------

def cmd_status(args) -> int:
    db = _open_db(args)
    db.set_status(args.arxiv_id, args.status, notes=args.notes or "")
    print(f"{args.arxiv_id} → {args.status}")
    return 0


def cmd_tag(args) -> int:
    db = _open_db(args)
    if args.action == "add":
        for t in args.tags:
            db.add_tag(args.arxiv_id, t)
    else:
        for t in args.tags:
            db.remove_tag(args.arxiv_id, t)
    print(f"{args.arxiv_id} tags: {db.tags_of(args.arxiv_id)}")
    return 0


def cmd_list(args) -> int:
    db = _open_db(args)
    if args.status:
        papers = db.list_by_status(args.status)
    elif args.tag:
        papers = db.list_by_tag(args.tag)
    else:
        papers = db.all(limit=args.max)
    _print_papers(papers, format=args.format)
    print(f"\n共 {len(papers)} 条")
    return 0


def cmd_info(args) -> int:
    db = _open_db(args)
    p = db.get(args.arxiv_id)
    if not p:
        print(f"找不到 {args.arxiv_id}", file=sys.stderr)
        return 1
    note = db.get_status(args.arxiv_id)
    tags = db.tags_of(args.arxiv_id)
    print(json.dumps({
        "paper": p.to_dict(),
        "status": note.status if note else None,
        "notes": note.notes if note else None,
        "tags": tags,
    }, ensure_ascii=False, indent=2))
    return 0


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="research-assistant", description="本地化的 AI 研究助手 CLI")
    p.add_argument("--db", default=DEFAULT_DB, help=f"SQLite 路径（默认 {DEFAULT_DB}）")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("search", help="arXiv 搜索（可选 enrich + save）")
    sp.add_argument("query")
    sp.add_argument("--max", type=int, default=30)
    sp.add_argument("--enrich", action="store_true", help="补 Semantic Scholar citation 等字段")
    sp.add_argument("--save", action="store_true", help="保存到本地 SQLite")
    sp.add_argument("--format", choices=["compact", "verbose", "json"], default="compact")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("find", help="本地语义检索（TF-IDF）")
    sp.add_argument("query")
    sp.add_argument("-k", type=int, default=5)
    sp.set_defaults(func=cmd_find)

    sp = sub.add_parser("status", help="设置阅读状态")
    sp.add_argument("arxiv_id")
    sp.add_argument("status", choices=["queued", "reading", "done", "skip"])
    sp.add_argument("--notes", default="")
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("tag", help="加 / 减标签")
    sp.add_argument("arxiv_id")
    sp.add_argument("action", choices=["add", "remove"])
    sp.add_argument("tags", nargs="+")
    sp.set_defaults(func=cmd_tag)

    sp = sub.add_parser("list", help="按状态 / 标签列论文")
    g = sp.add_mutually_exclusive_group()
    g.add_argument("--status", choices=["queued", "reading", "done", "skip"])
    g.add_argument("--tag")
    sp.add_argument("--max", type=int, default=50)
    sp.add_argument("--format", choices=["compact", "verbose", "json"], default="compact")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("info", help="单篇论文详情 + 元数据 + 状态")
    sp.add_argument("arxiv_id")
    sp.set_defaults(func=cmd_info)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
