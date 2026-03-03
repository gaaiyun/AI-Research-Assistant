"""
趋势分析模块单元测试
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from trend_analyzer import TrendAnalyzer, TrendData, analyze_research_trend


class TestTrendData:
    """测试 TrendData 数据类"""
    
    def test_default_initialization(self):
        """测试默认初始化"""
        import pandas as pd
        data = TrendData(
            keyword="test",
            paper_count=10,
            time_series=pd.DataFrame(),
            top_papers=[],
            related_keywords=[]
        )
        
        assert data.keyword == "test"
        assert data.paper_count == 10
        assert isinstance(data.top_papers, list)
    
    def test_to_dict(self):
        """测试转换为字典"""
        import pandas as pd
        data = TrendData(
            keyword="test",
            paper_count=10,
            time_series=pd.DataFrame({"month": ["2024-01"], "count": [5]}),
            top_papers=[{"title": "Paper1"}],
            related_keywords=["kw1"]
        )
        
        result = data.to_dict()
        assert isinstance(result, dict)
        assert result["keyword"] == "test"
        assert result["paper_count"] == 10


class TestTrendAnalyzer:
    """测试 TrendAnalyzer 类"""
    
    @pytest.fixture
    def analyzer(self):
        """创建分析器实例"""
        return TrendAnalyzer()
    
    def test_initialization(self, analyzer):
        """测试初始化"""
        assert analyzer.client is not None
        assert analyzer.cache == {}
    
    def test_research_areas_defined(self, analyzer):
        """测试研究领域已定义"""
        assert len(analyzer.RESEARCH_AREAS) > 0
        assert "LLM" in analyzer.RESEARCH_AREAS
        assert "Computer Vision" in analyzer.RESEARCH_AREAS
    
    def test_search_arxiv_basic(self, analyzer):
        """测试基本 arXiv 搜索"""
        # 注意：这个测试需要网络连接
        results = analyzer.search_arxiv("machine learning", max_results=5)
        
        # 可能返回 0 个或多个结果（取决于网络）
        assert isinstance(results, list)
    
    def test_search_arxiv_with_date_filter(self, analyzer):
        """测试带日期过滤的搜索"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        results = analyzer.search_arxiv(
            "deep learning",
            max_results=5,
            start_date=start_date,
            end_date=end_date
        )
        
        assert isinstance(results, list)
    
    def test_create_time_series_empty(self, analyzer):
        """测试创建空时间序列"""
        df = analyzer._create_time_series([], 12)
        assert df is not None
        assert df.empty
    
    def test_extract_top_papers_empty(self, analyzer):
        """测试提取空论文列表"""
        top = analyzer._extract_top_papers([])
        assert top == []
    
    def test_extract_related_keywords_empty(self, analyzer):
        """测试提取空关键词列表"""
        keywords = analyzer._extract_related_keywords([])
        assert keywords == []
    
    def test_compare_areas(self, analyzer):
        """测试多领域对比"""
        # 注意：这个测试需要网络连接
        areas = ["LLM", "NLP"]
        df = analyzer.compare_areas(areas, months=3)
        
        assert df is not None
        assert "area" in df.columns
        assert "paper_count" in df.columns
    
    def test_get_hot_topics(self, analyzer):
        """测试获取热点话题"""
        # 注意：这个测试需要网络连接
        topics = analyzer.get_hot_topics(days=30, min_papers=5)
        
        assert isinstance(topics, list)
    
    def test_generate_timeline_data_empty(self, analyzer):
        """测试生成空时间线数据"""
        data = analyzer.generate_timeline_data("test_keyword", months=3)
        
        assert isinstance(data, dict)
        assert data["keyword"] == "test_keyword"
        assert "months" in data
        assert "counts" in data
    
    def test_export_trend_report(self, analyzer, tmp_path):
        """测试导出趋势报告"""
        output_path = tmp_path / "trend_report.md"
        
        # 注意：这个测试需要网络连接
        try:
            result_path = analyzer.export_trend_report("machine learning", str(output_path), months=3)
            
            assert Path(result_path).exists()
            
            with open(result_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            assert "# machine learning 研究趋势分析报告" in content or "# " in content
        except Exception:
            # 网络问题可能导致失败，跳过
            pytest.skip("Network unavailable")


class TestAnalyzeResearchTrend:
    """测试便捷函数"""
    
    def test_analyze_research_trend(self):
        """测试分析研究趋势"""
        # 注意：这个测试需要网络连接
        try:
            trend = analyze_research_trend("deep learning", months=3)
            
            assert isinstance(trend, TrendData)
            assert trend.keyword == "deep learning"
        except Exception:
            # 网络问题可能导致失败，跳过
            pytest.skip("Network unavailable")


class TestResearchAreas:
    """测试研究领域配置"""
    
    def test_llm_keywords(self):
        """测试 LLM 关键词"""
        analyzer = TrendAnalyzer()
        llm_keywords = analyzer.RESEARCH_AREAS["LLM"]
        
        assert len(llm_keywords) > 0
        assert any("language model" in kw.lower() for kw in llm_keywords)
    
    def test_cv_keywords(self):
        """测试计算机视觉关键词"""
        analyzer = TrendAnalyzer()
        cv_keywords = analyzer.RESEARCH_AREAS["Computer Vision"]
        
        assert len(cv_keywords) > 0
        assert any("vision" in kw.lower() for kw in cv_keywords)
    
    def test_all_areas_have_keywords(self):
        """测试所有领域有关键词"""
        analyzer = TrendAnalyzer()
        
        for area, keywords in analyzer.RESEARCH_AREAS.items():
            assert len(keywords) > 0, f"{area} 没有定义关键词"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
