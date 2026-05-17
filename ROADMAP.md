# Roadmap

## v2（本次提交，已完成）

- ✅ `arxiv_client.py` — arXiv + Semantic Scholar Graph API
- ✅ `vector_store.py` — TF-IDF + 可选 sentence-transformers/ChromaDB
- ✅ `paper_db.py` — SQLite 持久化（papers / reading_status / tags）
- ✅ `cli.py` — 六个命令的命令行入口
- ✅ 23 个新测试（含 Semantic Scholar mock，避免真实 API 依赖）

## v3 计划

### 全文索引
- [ ] PDF 下载缓存 + 全文索引（让 `find` 能搜到正文，不只是摘要）
- [ ] 用 `pypdfium2` 或 `pdfminer.six` 替代 PyPDF2（更稳定）
- [ ] GROBID 结构化解析（章节、公式、表格）

### LLM 集成
- [ ] `summarize.py` — 接 Anthropic Claude / OpenAI 做"跨论文方法论对比"
- [ ] 让 `qa_system` 升级到 RAG：从本地向量库召回 → LLM 回答
- [ ] 对单篇论文的"批判性阅读"prompt 套件（找数据偏差、找未对照的实验）

### 引用网络
- [ ] 用 Semantic Scholar references/citations endpoint 构建本地引用图
- [ ] networkx 可视化"我的 reading list"周围 1-hop / 2-hop 论文
- [ ] 自动推荐"被你的标签下论文反复引用、但你还没读"的论文

### 工程
- [ ] BibTeX / RIS 导出（让本地库能塞进 Zotero / Mendeley）
- [ ] HTTP API + 多用户（如果有人想架在团队内网）
- [ ] CI（GitHub Actions 跑 pytest）

## 不会做的

- 不会做"重新发明 Zotero / Mendeley"：定位是 **CLI-first**，给习惯终端的人用
- 不会引入需付费 license 的依赖
- 不会把 LLM key 强制要求 — 离线场景必须可用
