"""
对比分析模块单元测试
"""

import pytest
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from paper_parser import PaperInfo
from comparison_analyzer import ComparisonAnalyzer, ComparisonResult, compare_papers


class TestComparisonResult:
    """测试 ComparisonResult 数据类"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        import pandas as pd
        result = ComparisonResult(
            papers=["Paper1", "Paper2"],
            comparison_table=pd.DataFrame(),
            method_comparison="",
            result_comparison="",
            strengths_weaknesses={}
        )
        
        assert len(result.papers) == 2
        assert result.method_comparison == ""
        assert result.result_comparison == ""
    
    def test_to_dict(self):
        """测试转换为字典"""
        import pandas as pd
        result = ComparisonResult(
            papers=["Paper1"],
            comparison_table=pd.DataFrame({"col": [1]}),
            method_comparison="Methods",
            result_comparison="Results",
            strengths_weaknesses={"Paper1": {"strengths": ["good"], "weaknesses": ["bad"]}}
        )
        
        data = result.to_dict()
        assert isinstance(data, dict)
        assert "papers" in data
        assert "comparison_table" in data


class TestComparisonAnalyzer:
    """测试 ComparisonAnalyzer 类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return ComparisonAnalyzer()
    
    @pytest.fixture
    def sample_papers(self):
        """创建示例论文"""
        paper1 = PaperInfo(
            title="Paper 1: Deep Learning for NLP",
            abstract="This paper presents a deep learning approach for NLP.",
            method="We use transformer architecture with attention mechanism.",
            experiments="Accuracy: 95.2% on benchmark dataset.",
            conclusion="Our method achieves state-of-the-art results.",
            keywords=["deep learning", "NLP", "transformer"],
            references=["Ref1", "Ref2", "Ref3"]
        )
        
        paper2 = PaperInfo(
            title="Paper 2: CNN for Image Classification",
            abstract="This paper presents a CNN approach for image classification.",
            method="We use convolutional neural networks with residual connections.",
            experiments="Accuracy: 98.1% on ImageNet.",
            conclusion="Residual connections improve performance significantly.",
            keywords=["CNN", "image classification", "residual"],
            references=["Ref1", "Ref2", "Ref3", "Ref4", "Ref5"]
        )
        
        return [paper1, paper2]
    
    def test_initialization(self, analyzer):
        """测试初始化"""
        assert analyzer.papers == []
    
    def test_add_paper(self, analyzer, sample_papers):
        """测试添加单篇论文"""
        analyzer.add_paper(sample_papers[0])
        assert len(analyzer.papers) == 1
    
    def test_add_papers(self, analyzer, sample_papers):
        """测试批量添加论文"""
        analyzer.add_papers(sample_papers)
        assert len(analyzer.papers) == 2
    
    def test_clear(self, analyzer, sample_papers):
        """测试清空"""
        analyzer.add_papers(sample_papers)
        analyzer.clear()
        assert len(analyzer.papers) == 0
    
    def test_generate_comparison_table(self, analyzer, sample_papers):
        """测试生成对比表格"""
        analyzer.add_papers(sample_papers)
        table = analyzer.generate_comparison_table()
        
        assert table is not None
        assert len(table) == 2
        assert "标题" in table.columns
        assert "关键词数量" in table.columns
    
    def test_compare_methods(self, analyzer, sample_papers):
        """测试方法对比"""
        analyzer.add_papers(sample_papers)
        comparison = analyzer.compare_methods()
        
        assert "方法论对比分析" in comparison
        assert "Paper 1" in comparison or "Deep Learning" in comparison
    
    def test_compare_methods_single_paper(self, analyzer, sample_papers):
        """测试单篇论文的方法对比"""
        analyzer.add_paper(sample_papers[0])
        comparison = analyzer.compare_methods()
        
        assert "需要至少两篇论文" in comparison
    
    def test_compare_results(self, analyzer, sample_papers):
        """测试结果对比"""
        analyzer.add_papers(sample_papers)
        comparison = analyzer.compare_results()
        
        assert "实验结果对比分析" in comparison
    
    def test_analyze_strengths_weaknesses(self, analyzer, sample_papers):
        """测试优缺点分析"""
        analyzer.add_papers(sample_papers)
        sw = analyzer.analyze_strengths_weaknesses()
        
        assert isinstance(sw, dict)
        assert len(sw) == 2
        
        for title, analysis in sw.items():
            assert "strengths" in analysis
            assert "weaknesses" in analysis
            assert isinstance(analysis["strengths"], list)
            assert isinstance(analysis["weaknesses"], list)
    
    def test_generate_full_comparison(self, analyzer, sample_papers):
        """测试完整对比"""
        analyzer.add_papers(sample_papers)
        result = analyzer.generate_full_comparison()
        
        assert isinstance(result, ComparisonResult)
        assert len(result.papers) == 2
        assert result.comparison_table is not None
        assert result.method_comparison != ""
        assert result.result_comparison != ""
    
    def test_export_to_markdown(self, analyzer, sample_papers, tmp_path):
        """测试导出 Markdown"""
        analyzer.add_papers(sample_papers)
        
        output_path = tmp_path / "test_report.md"
        result_path = analyzer.export_to_markdown(str(output_path))
        
        assert Path(result_path).exists()
        
        with open(result_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert "# 论文对比分析报告" in content
        assert "基本信息对比" in content


class TestComparePapers:
    """测试便捷函数"""
    
    @pytest.fixture
    def sample_papers(self):
        """创建示例论文"""
        paper1 = PaperInfo(
            title="Paper 1",
            abstract="Abstract 1",
            keywords=["kw1"]
        )
        paper2 = PaperInfo(
            title="Paper 2",
            abstract="Abstract 2",
            keywords=["kw2"]
        )
        return [paper1, paper2]
    
    def test_compare_papers_without_export(self, sample_papers):
        """测试对比不导出"""
        result = compare_papers(sample_papers)
        assert isinstance(result, ComparisonResult)
        assert len(result.papers) == 2
    
    def test_compare_papers_with_export(self, sample_papers, tmp_path):
        """测试对比并导出"""
        output_path = tmp_path / "report.md"
        result = compare_papers(sample_papers, output_path=str(output_path))
        
        assert isinstance(result, ComparisonResult)
        assert Path(output_path).exists()


class TestExtractMethodKeywords:
    """测试方法关键词提取"""
    
    def test_extract_keywords(self):
        """测试关键词提取"""
        analyzer = ComparisonAnalyzer()
        
        method_text = "We use a neural network with transformer architecture and attention mechanism."
        keywords = analyzer._extract_method_keywords(method_text)
        
        assert len(keywords) > 0
        assert any("neural" in kw.lower() for kw in keywords)
        assert any("transformer" in kw.lower() for kw in keywords)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
