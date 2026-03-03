"""
pytest 配置文件
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_dir():
    """项目根目录"""
    return project_root


@pytest.fixture(scope="session")
def tests_dir():
    """测试目录"""
    return Path(__file__).parent


@pytest.fixture
def sample_pdf_text():
    """示例 PDF 文本内容"""
    return """
    Deep Learning for Natural Language Processing
    
    ABSTRACT
    This paper presents a novel deep learning approach for natural language processing tasks.
    Our method achieves state-of-the-art results on multiple benchmarks.
    
    Keywords: deep learning, NLP, transformer, attention
    
    1. INTRODUCTION
    Natural language processing has seen significant advances with deep learning.
    
    2. METHOD
    We propose a transformer-based architecture with multi-head attention mechanism.
    The model consists of encoder and decoder layers.
    
    3. EXPERIMENTS
    We conducted experiments on three benchmark datasets.
    Results show accuracy of 95.5% on dataset A, 93.2% on dataset B.
    
    4. CONCLUSION
    Our method demonstrates superior performance compared to previous approaches.
    Future work includes extending to multilingual settings.
    
    REFERENCES
    [1] Vaswani et al. Attention is All You Need.
    [2] Devlin et al. BERT: Pre-training of Deep Bidirectional Transformers.
    [3] Radford et al. Language Models are Unsupervised Multitask Learners.
    """


@pytest.fixture
def mock_arxiv_result():
    """模拟 arXiv 结果"""
    class MockResult:
        def __init__(self, title, published, authors, summary):
            self.title = title
            self.published = published
            self.authors = authors
            self.summary = summary
            self.entry_id = "http://arxiv.org/abs/1234.5678"
            self.categories = ["cs.AI"]
            self.comment = "10 pages"
    
    return MockResult
