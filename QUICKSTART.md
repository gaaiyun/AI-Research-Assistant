# 🚀 快速开始指南

## 安装

### 1. 安装依赖

```bash
cd ai-research-assistant
pip install -r requirements.txt
```

### 2. 验证安装

```bash
# 运行测试
python run_tests.py

# 或者使用 pytest
pytest tests/ -v
```

## 启动应用

```bash
streamlit run dashboard.py
```

应用将在 http://localhost:8501 自动打开

## 使用流程

### 📄 论文解析

1. 点击侧边栏【论文解析】
2. 上传 PDF 论文文件
3. 等待自动解析
4. 查看提取的信息

### 📊 对比分析

1. 上传至少 2 篇论文
2. 点击【对比分析】
3. 选择要对比的论文
4. 查看相似度、差异分析

### 📈 趋势分析

1. 点击【趋势分析】
2. 输入研究关键词
3. 查看 arXiv 趋势图表

### ❓ 智能问答

1. 确保已加载论文
2. 点击【智能问答】
3. 输入问题
4. 获取答案和来源

## 测试覆盖率

当前测试覆盖率：**67%**

- paper_parser.py: 84%
- comparison_analyzer.py: 90%
- qa_system.py: 84%
- trend_analyzer.py: 82%

## 常见问题

### Q: 无法启动应用？
A: 确保已安装所有依赖：`pip install -r requirements.txt`

### Q: PDF 解析失败？
A: 确保 PDF 文件是文本格式，不是扫描图片

### Q: arXiv 搜索无结果？
A: 检查网络连接，或尝试更具体的关键词

## 技术支持

遇到问题？查看 README.md 获取更多信息。
