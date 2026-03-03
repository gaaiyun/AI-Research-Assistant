"""
研究趋势分析模块 - Trend Analyzer Module
基于 arXiv API 的研究热点分析、时间线可视化
"""

import arxiv
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import re


@dataclass
class TrendData:
    """趋势数据"""
    keyword: str
    paper_count: int
    time_series: pd.DataFrame
    top_papers: List[Dict]
    related_keywords: List[str]
    
    def to_dict(self) -> Dict:
        return {
            "keyword": self.keyword,
            "paper_count": self.paper_count,
            "time_series": self.time_series.to_dict() if self.time_series is not None else {},
            "top_papers": self.top_papers,
            "related_keywords": self.related_keywords
        }


class TrendAnalyzer:
    """研究趋势分析器"""
    
    # 热门研究领域关键词
    RESEARCH_AREAS = {
        "LLM": ["large language model", "LLM", "GPT", "transformer"],
        "Computer Vision": ["computer vision", "image classification", "object detection", "segmentation"],
        "NLP": ["natural language processing", "NLP", "text classification", "sentiment analysis"],
        "Reinforcement Learning": ["reinforcement learning", "RL", "Q-learning", "policy gradient"],
        "Generative AI": ["generative", "GAN", "diffusion", "stable diffusion", "DALL-E"],
        "Machine Learning": ["machine learning", "deep learning", "neural network"],
        "AI Safety": ["AI safety", "alignment", "AI ethics", "responsible AI"],
        "Multimodal": ["multimodal", "vision-language", "CLIP", "image-text"]
    }
    
    def __init__(self):
        self.client = arxiv.Client()
        self.cache = {}
    
    def search_arxiv(self, query: str, max_results: int = 100, 
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None) -> List[arxiv.Result]:
        """搜索 arXiv 论文"""
        try:
            # 构建搜索条件
            search = arxiv.Search(
                query=query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            results = []
            for result in self.client.results(search):
                # 日期过滤
                if start_date and result.published < start_date:
                    continue
                if end_date and result.published > end_date:
                    continue
                results.append(result)
                
                if len(results) >= max_results:
                    break
            
            return results
        except Exception as e:
            print(f"搜索 arXiv 失败：{e}")
            return []
    
    def analyze_trend(self, keyword: str, months: int = 12) -> TrendData:
        """分析特定关键词的研究趋势"""
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        # 搜索论文
        papers = self.search_arxiv(
            query=keyword,
            max_results=500,
            start_date=start_date,
            end_date=end_date
        )
        
        # 构建时间序列
        time_series = self._create_time_series(papers, months)
        
        # 提取高引论文
        top_papers = self._extract_top_papers(papers)
        
        # 提取相关关键词
        related_keywords = self._extract_related_keywords(papers)
        
        return TrendData(
            keyword=keyword,
            paper_count=len(papers),
            time_series=time_series,
            top_papers=top_papers,
            related_keywords=related_keywords
        )
    
    def _create_time_series(self, papers: List[arxiv.Result], months: int) -> pd.DataFrame:
        """创建月度论文数量时间序列"""
        if not papers:
            return pd.DataFrame()
        
        # 按月统计
        month_counts = {}
        for paper in papers:
            month_key = paper.published.strftime("%Y-%m")
            month_counts[month_key] = month_counts.get(month_key, 0) + 1
        
        # 创建 DataFrame
        df = pd.DataFrame(list(month_counts.items()), columns=["month", "count"])
        df = df.sort_values("month")
        
        return df
    
    def _extract_top_papers(self, papers: List[arxiv.Result], top_n: int = 10) -> List[Dict]:
        """提取高影响力论文"""
        # 简单策略：按标题长度和摘要质量排序（arXiv API 不直接提供引用数）
        scored_papers = []
        
        for paper in papers:
            score = 0
            # 标题长度适中得分高
            if 20 < len(paper.title) < 150:
                score += 1
            # 摘要较长通常更详细
            if len(paper.summary) > 500:
                score += 1
            # 有多个作者
            if len(paper.authors) > 2:
                score += 1
            # 有注释
            if paper.comment:
                score += 1
            
            scored_papers.append((score, paper))
        
        # 排序
        scored_papers.sort(reverse=True, key=lambda x: x[0])
        
        # 提取 top N
        top_papers = []
        for score, paper in scored_papers[:top_n]:
            top_papers.append({
                "title": paper.title,
                "authors": [str(a) for a in paper.authors],
                "published": paper.published.strftime("%Y-%m-%d"),
                "arxiv_id": paper.entry_id.split("/")[-1],
                "categories": paper.categories,
                "summary_preview": paper.summary[:200] + "..." if len(paper.summary) > 200 else paper.summary
            })
        
        return top_papers
    
    def _extract_related_keywords(self, papers: List[arxiv.Result]) -> List[str]:
        """从论文中提取相关关键词"""
        from collections import Counter
        
        # 常见技术术语
        tech_terms = [
            "transformer", "attention", "BERT", "GPT", "neural", "deep learning",
            "fine-tuning", "pre-training", "embedding", "encoder", "decoder",
            "classification", "generation", "summarization", "question answering",
            "reinforcement learning", "unsupervised", "self-supervised", "contrastive"
        ]
        
        term_counts = Counter()
        for paper in papers:
            text = (paper.title + " " + paper.summary).lower()
            for term in tech_terms:
                if term in text:
                    term_counts[term] += 1
        
        # 返回最常见的相关术语
        related = [term for term, count in term_counts.most_common(10)]
        return related
    
    def compare_areas(self, areas: Optional[List[str]] = None, months: int = 12) -> pd.DataFrame:
        """对比多个研究领域的趋势"""
        if areas is None:
            areas = list(self.RESEARCH_AREAS.keys())
        
        results = []
        for area in areas:
            keywords = self.RESEARCH_AREAS.get(area, [area])
            query = " OR ".join(keywords)
            
            papers = self.search_arxiv(query=query, max_results=200)
            
            results.append({
                "area": area,
                "paper_count": len(papers),
                "query": query
            })
        
        df = pd.DataFrame(results)
        df = df.sort_values("paper_count", ascending=False)
        
        return df
    
    def get_hot_topics(self, days: int = 30, min_papers: int = 20) -> List[Dict]:
        """获取近期热点话题"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        topic_counts = {}
        
        # 搜索各领域的论文
        for area, keywords in self.RESEARCH_AREAS.items():
            query = " OR ".join(keywords)
            papers = self.search_arxiv(
                query=query,
                max_results=300,
                start_date=start_date,
                end_date=end_date
            )
            
            if len(papers) >= min_papers:
                topic_counts[area] = len(papers)
        
        # 排序
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [{"topic": topic, "paper_count": count} for topic, count in sorted_topics]
    
    def generate_timeline_data(self, keyword: str, months: int = 12) -> Dict:
        """生成时间线可视化数据"""
        trend_data = self.analyze_trend(keyword, months)
        
        if trend_data.time_series is None or trend_data.time_series.empty:
            return {"months": [], "counts": [], "keyword": keyword}
        
        return {
            "months": trend_data.time_series["month"].tolist(),
            "counts": trend_data.time_series["count"].tolist(),
            "keyword": keyword,
            "total_papers": trend_data.paper_count
        }
    
    def export_trend_report(self, keyword: str, output_path: str, months: int = 12):
        """导出趋势分析报告"""
        trend_data = self.analyze_trend(keyword, months)
        
        report = [
            f"# {keyword} 研究趋势分析报告",
            f"\n**分析时间范围**: 过去{months}个月",
            f"**论文总数**: {trend_data.paper_count}",
            "\n---\n"
        ]
        
        # 时间序列数据
        report.append("## 月度论文数量\n")
        if trend_data.time_series is not None and not trend_data.time_series.empty:
            report.append(trend_data.time_series.to_markdown(index=False))
        
        # 热点论文
        report.append("\n## 代表性论文\n")
        for i, paper in enumerate(trend_data.top_papers[:5], 1):
            report.append(f"\n### {i}. {paper['title']}")
            report.append(f"**作者**: {', '.join(paper['authors'][:3])}{' et al.' if len(paper['authors']) > 3 else ''}")
            report.append(f"**发布时间**: {paper['published']}")
            report.append(f"**摘要**: {paper['summary_preview']}")
        
        # 相关关键词
        report.append("\n## 相关技术关键词\n")
        for kw in trend_data.related_keywords:
            report.append(f"- {kw}")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(report))
        
        return output_path


def analyze_research_trend(keyword: str, months: int = 12) -> TrendData:
    """便捷函数：分析研究趋势"""
    analyzer = TrendAnalyzer()
    return analyzer.analyze_trend(keyword, months)


if __name__ == "__main__":
    # 测试示例
    analyzer = TrendAnalyzer()
    
    print("测试 arXiv 趋势分析...")
    trend = analyzer.analyze_trend("large language model", months=6)
    print(f"关键词：{trend.keyword}")
    print(f"论文数量：{trend.paper_count}")
    print(f"相关关键词：{trend.related_keywords[:5]}")
