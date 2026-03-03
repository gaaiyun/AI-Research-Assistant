# 📚 AI 研究助手

基于 LLM 的学术论文辅助研究工具

## ✨ 功能特性

### 1. 论文智能解析 📄
- 自动提取摘要、方法、实验、结论
- 关键词识别与提取
- 参考文献解析
- 伪代码/算法提取

### 2. 跨论文对比分析 📊
- 多篇论文方法论对比
- 实验结果横向比较
- 优缺点自动分析
- Markdown 报告导出

### 3. 研究趋势分析 📈
- 基于 arXiv API 的实时数据
- 月度论文发表趋势
- 热点话题识别
- 相关技术关键词提取

### 4. 引用网络分析 🕸️
- 参考文献统计
- 引用关系可视化（开发中）
- 关键论文识别（规划中）

## 🚀 快速开始

### 安装依赖

```bash
cd ai-research-assistant
pip install -r requirements.txt
```

### 运行应用

```bash
streamlit run dashboard.py
```

应用将在浏览器中自动打开（默认 http://localhost:8501）

## 📖 使用指南

### 论文解析

1. 在侧边栏选择「📄 论文解析」
2. 上传 PDF 格式的学术论文
3. 系统自动解析并提取关键信息
4. 可导出为 JSON 或 Markdown 格式

### 对比分析

1. 至少上传 2 篇论文
2. 选择「📊 对比分析」
3. 选择要对比的论文
4. 查看对比报告并导出

### 趋势分析

1. 选择「📈 趋势分析」
2. 选择研究领域或输入自定义关键词
3. 设置分析时间范围
4. 查看趋势图表和热点论文

## 🏗️ 项目结构

```
ai-research-assistant/
├── dashboard.py          # 主界面 (Streamlit)
├── paper_parser.py       # 论文解析模块
├── comparison_analyzer.py # 对比分析模块
├── trend_analyzer.py     # 趋势分析模块
├── requirements.txt      # 依赖列表
├── README.md            # 项目说明
└── tests/               # 单元测试
    ├── test_paper_parser.py
    ├── test_comparison.py
    └── test_trend.py
```

## 🧪 测试

运行单元测试：

```bash
pytest tests/ -v --cov=.
```

测试覆盖率要求：> 70%

## 🔧 技术栈

- **前端框架**: Streamlit
- **PDF 处理**: PyPDF2
- **数据分析**: Pandas, NumPy
- **可视化**: Plotly
- **学术 API**: arXiv
- **测试框架**: pytest

## 📝 API 使用

### 论文解析

```python
from paper_parser import PaperParser

parser = PaperParser()
paper = parser.parse("path/to/paper.pdf")

print(f"标题：{paper.title}")
print(f"摘要：{paper.abstract}")
print(f"方法：{paper.method}")
```

### 对比分析

```python
from comparison_analyzer import ComparisonAnalyzer

analyzer = ComparisonAnalyzer()
analyzer.add_paper(paper1)
analyzer.add_paper(paper2)

result = analyzer.generate_full_comparison()
analyzer.export_to_markdown("report.md")
```

### 趋势分析

```python
from trend_analyzer import TrendAnalyzer

analyzer = TrendAnalyzer()
trend = analyzer.analyze_trend("large language model", months=12)

print(f"论文数量：{trend.paper_count}")
print(f"相关关键词：{trend.related_keywords}")
```

## 🎯 创新点

1. **智能解析**: 自动识别论文结构，提取关键信息
2. **跨论文对比**: 多篇论文横向对比，快速把握研究脉络
3. **趋势可视化**: 基于真实 arXiv 数据的研究热点分析
4. **代码复现辅助**: 从论文中提取伪代码和算法描述
5. **引用网络**: 可视化引用关系，识别关键论文

## 📊 示例截图

### 论文解析界面
（运行应用后查看）

### 对比分析报告
（运行应用后查看）

### 趋势分析图表
（运行应用后查看）

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🙏 致谢

- arXiv 提供免费的学术论文 API
- Streamlit 团队提供的优秀框架
- 所有开源贡献者

---

**版本**: 1.0.0  
**更新日期**: 2026-03-04  
**作者**: AI Research Team
