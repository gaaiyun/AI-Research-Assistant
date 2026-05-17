# AI Research Assistant

> 一个**本地化、可离线检索**的学术论文助手。  
> arXiv 抓元数据，Semantic Scholar 补 citation，SQLite 持久化，TF-IDF / 句向量检索。

## 它能解决什么

- 想跟一个研究方向，但没时间天天刷 arXiv → 一句话搜索 + 保存到本地库
- 想找过往读过的某篇论文，但只记得大意 → 本地语义检索（`find` 命令）
- 需要 arXiv 不直接提供的 **citation 数 / 发表场所 / 影响力指标** → 自动从 Semantic Scholar 补全
- 看了一堆论文头脑里乱了 → 阅读状态（queued/reading/done/skip）+ 自定义标签，全部 SQLite 持久化

## v2 的关键改动

| 模块 | 作用 |
|---|---|
| `arxiv_client.py` | 统一封装 arXiv + Semantic Scholar Graph API（citation/venue/年份/影响力） |
| `vector_store.py` | 抽象向量索引，默认 TF-IDF；可选 sentence-transformers + ChromaDB |
| `paper_db.py` | SQLite 持久化：papers / reading_status / tags 三张表 |
| `cli.py` | `search` / `find` / `status` / `tag` / `list` / `info` 六个命令 |

v1 已有的 `paper_parser` / `comparison_analyzer` / `qa_system` / `trend_analyzer` 没有删，依然可用；v2 在它们旁边增加了"真能跑、能持久化、能检索"的能力。

## 快速开始

```bash
pip install -r requirements.txt

# 搜 + 存到本地库
python cli.py search "retrieval augmented generation" --max 30 --enrich --save

# 检索本地库
python cli.py find "how to ground LLM answers with citations" -k 5

# 标记阅读状态
python cli.py status 2310.11511 reading --notes "第 3 节 retrieval head 设计很重要"

# 加标签
python cli.py tag 2310.11511 add rag llm

# 列出所有"reading"
python cli.py list --status reading

# 看一篇论文的元数据 + 我的标签 + 状态
python cli.py info 2310.11511
```

Streamlit Dashboard 也可用：

```bash
streamlit run dashboard.py
```

## 库的方式调用

```python
from arxiv_client import ArxivClient, SemanticScholarClient, enrich_with_semantic_scholar
from paper_db import PaperDB
from vector_store import TfidfStore

papers = ArxivClient().search("mixture of experts", max_results=50)
enrich_with_semantic_scholar(papers, client=SemanticScholarClient())

db = PaperDB("my-research.sqlite")
db.upsert(papers)

# 语义检索
store = TfidfStore()
store.add(db.all())
for paper, score in store.query("conditional computation in transformers", k=5):
    print(score, paper.arxiv_id, paper.title)
```

## 升级到嵌入式检索

默认 TF-IDF 已经够用（千级论文 < 1s 检索），但语义检索能找到不共享关键词的相关论文。装上可选依赖：

```bash
pip install sentence-transformers chromadb
```

然后：

```python
from vector_store import ChromaEmbeddingStore
store = ChromaEmbeddingStore(persist_dir="./vector_index", model_name="sentence-transformers/all-MiniLM-L6-v2")
store.add(papers)
hits = store.query("how to build a faithful summarizer", k=5)
```

## 设计取舍

**为什么 SQLite 不上 Postgres？**  
论文场景下数据规模 ≤ 10 万，单用户单文件、可备份、零运维。

**为什么默认 TF-IDF 不直接用 embedding？**  
sentence-transformers + chromadb 装机量 ~1.5 GB，模型权重 ~500 MB；学术论文场景下 TF-IDF 命中率已经在 90%+，跑得快、依赖少。需要语义召回时再升级。

**为什么 Semantic Scholar 默认不开 enrich？**  
公开 API 限速 1 req/s。100 篇要等近 2 分钟。日常浏览用 arXiv 就够，整理"重要 reading list" 时再用 `--enrich`。

## 文件结构

```
.
├─ arxiv_client.py        # arXiv + Semantic Scholar
├─ vector_store.py        # TF-IDF / Chroma 抽象
├─ paper_db.py            # SQLite 持久化
├─ cli.py                 # CLI 入口
│
├─ paper_parser.py        # v1：PDF 解析
├─ comparison_analyzer.py # v1：跨论文对比
├─ qa_system.py           # v1：基于关键词的 QA
├─ trend_analyzer.py      # v1：趋势分析
├─ dashboard.py           # Streamlit UI
│
└─ tests/                 # 23 新测试 + 71 原有测试，共 94 个
```

## 测试

```bash
python -m pytest tests/ -o addopts=""
```

23 个新测试覆盖：arxiv_client（含 Semantic Scholar mock）、vector_store、paper_db。

## 路线图

见 [`ROADMAP.md`](ROADMAP.md)。下一步重点：
1. PDF 全文本地存储 + 全文索引（让"我在某篇论文里读过 XX"变得可搜）
2. 真接入 OpenAI/Anthropic API 给 `comparison_analyzer` 提供 LLM 跨论文摘要

## 许可

MIT
