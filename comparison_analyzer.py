"""
跨论文对比分析模块 - Comparison Analyzer Module
支持多篇论文的方法、结果、优缺点对比分析
"""

import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass
from paper_parser import PaperInfo
import json


@dataclass
class ComparisonResult:
    """对比分析结果"""
    papers: List[str]  # 论文标题列表
    comparison_table: pd.DataFrame
    method_comparison: str
    result_comparison: str
    strengths_weaknesses: Dict[str, Dict[str, List[str]]]
    
    def to_dict(self) -> Dict:
        return {
            "papers": self.papers,
            "comparison_table": self.comparison_table.to_dict() if self.comparison_table is not None else {},
            "method_comparison": self.method_comparison,
            "result_comparison": self.result_comparison,
            "strengths_weaknesses": self.strengths_weaknesses
        }


class ComparisonAnalyzer:
    """论文对比分析器"""
    
    def __init__(self):
        self.papers: List[PaperInfo] = []
    
    def add_paper(self, paper: PaperInfo):
        """添加论文到对比列表"""
        self.papers.append(paper)
    
    def add_papers(self, papers: List[PaperInfo]):
        """批量添加论文"""
        self.papers.extend(papers)
    
    def clear(self):
        """清空所有论文"""
        self.papers = []
    
    def _extract_key_info(self, paper: PaperInfo) -> Dict:
        """从单篇论文提取关键对比信息"""
        return {
            "标题": paper.title[:100] if paper.title else "N/A",
            "摘要长度": len(paper.abstract),
            "方法长度": len(paper.method),
            "实验长度": len(paper.experiments),
            "关键词数量": len(paper.keywords),
            "参考文献数量": len(paper.references),
            "关键词": ", ".join(paper.keywords[:5]) if paper.keywords else "N/A"
        }
    
    def generate_comparison_table(self) -> pd.DataFrame:
        """生成对比表格"""
        if not self.papers:
            return pd.DataFrame()
        
        data = []
        for paper in self.papers:
            info = self._extract_key_info(paper)
            data.append(info)
        
        df = pd.DataFrame(data)
        return df
    
    def compare_methods(self) -> str:
        """对比各论文的方法论"""
        if len(self.papers) < 2:
            return "需要至少两篇论文才能进行方法对比"
        
        comparison_parts = ["## 方法论对比分析\n"]
        
        for i, paper in enumerate(self.papers, 1):
            comparison_parts.append(f"\n### 论文{i}: {paper.title[:50]}...")
            
            if paper.method:
                # 提取方法关键词
                method_keywords = self._extract_method_keywords(paper.method)
                comparison_parts.append(f"**核心方法**: {', '.join(method_keywords[:5])}")
                
                # 方法简述
                method_summary = paper.method[:300] + "..." if len(paper.method) > 300 else paper.method
                comparison_parts.append(f"**方法描述**: {method_summary}")
            else:
                comparison_parts.append("**方法**: 未提取到方法部分")
        
        # 方法对比总结
        comparison_parts.append("\n### 方法对比总结")
        methods = [p.method for p in self.papers if p.method]
        if methods:
            common_themes = self._find_common_themes(methods)
            comparison_parts.append(f"**共同主题**: {', '.join(common_themes[:5]) if common_themes else '无明显共同主题'}")
        
        return "\n".join(comparison_parts)
    
    def compare_results(self) -> str:
        """对比各论文的实验结果"""
        if len(self.papers) < 2:
            return "需要至少两篇论文才能进行结果对比"
        
        comparison_parts = ["## 实验结果对比分析\n"]
        
        for i, paper in enumerate(self.papers, 1):
            comparison_parts.append(f"\n### 论文{i}: {paper.title[:50]}...")
            
            if paper.experiments:
                # 提取可能的指标
                metrics = self._extract_metrics(paper.experiments)
                if metrics:
                    comparison_parts.append(f"**关键指标**: {metrics}")
                
                exp_summary = paper.experiments[:300] + "..." if len(paper.experiments) > 300 else paper.experiments
                comparison_parts.append(f"**实验概述**: {exp_summary}")
            else:
                comparison_parts.append("**实验**: 未提取到实验部分")
        
        return "\n".join(comparison_parts)
    
    def analyze_strengths_weaknesses(self) -> Dict[str, Dict[str, List[str]]]:
        """分析各论文的优缺点"""
        result = {}
        
        for paper in self.papers:
            strengths = []
            weaknesses = []
            
            # 基于提取内容分析
            if paper.abstract and len(paper.abstract) > 200:
                strengths.append("摘要详细完整")
            
            if paper.method and len(paper.method) > 500:
                strengths.append("方法论描述详尽")
            
            if paper.experiments and len(paper.experiments) > 500:
                strengths.append("实验部分充实")
            
            if paper.references and len(paper.references) > 10:
                strengths.append("参考文献丰富")
            
            if paper.keywords and len(paper.keywords) > 3:
                strengths.append("关键词覆盖全面")
            
            # 弱点分析
            if not paper.abstract:
                weaknesses.append("缺少明确摘要")
            
            if not paper.method:
                weaknesses.append("方法论描述不足")
            
            if not paper.experiments:
                weaknesses.append("实验部分缺失")
            
            if len(paper.references) < 5:
                weaknesses.append("参考文献较少")
            
            result[paper.title[:50] if paper.title else "未知论文"] = {
                "strengths": strengths,
                "weaknesses": weaknesses
            }
        
        return result
    
    def _extract_method_keywords(self, method_text: str) -> List[str]:
        """从方法文本提取关键词"""
        # 常见方法关键词
        keywords = [
            "neural network", "transformer", "attention", "CNN", "RNN", "LSTM",
            "BERT", "GPT", "fine-tuning", "pre-training", "reinforcement learning",
            "supervised", "unsupervised", "self-supervised", "contrastive",
            "encoder", "decoder", "embedding", "classification", "regression",
            "深度学习", "神经网络", "注意力机制", "卷积", "循环神经网络",
            "迁移学习", "微调", "预训练", "强化学习"
        ]
        
        found_keywords = []
        method_lower = method_text.lower()
        for kw in keywords:
            if kw.lower() in method_lower:
                found_keywords.append(kw)
        
        return found_keywords
    
    def _extract_metrics(self, experiment_text: str) -> str:
        """从实验文本提取指标"""
        # 常见指标模式
        metrics_patterns = [
            r'accuracy[:\s]*(\d+\.?\d*)\s*%?',
            r'precision[:\s]*(\d+\.?\d*)\s*%?',
            r'recall[:\s]*(\d+\.?\d*)\s*%?',
            r'f1[:\s]*(\d+\.?\d*)\s*%?',
            r'bleu[:\s]*(\d+\.?\d*)',
            r'rouge[:\s]*(\d+\.?\d*)',
            r'mse[:\s]*(\d+\.?\d*)',
            r'rmse[:\s]*(\d+\.?\d*)',
        ]
        
        found_metrics = []
        for pattern in metrics_patterns:
            matches = re.findall(pattern, experiment_text, re.IGNORECASE)
            if matches:
                found_metrics.extend(matches[:3])
        
        return ", ".join(found_metrics) if found_metrics else "未提取到明确指标"
    
    def _find_common_themes(self, texts: List[str]) -> List[str]:
        """查找多个文本的共同主题"""
        from collections import Counter
        
        all_keywords = []
        for text in texts:
            keywords = self._extract_method_keywords(text)
            all_keywords.extend(keywords)
        
        # 统计词频
        counter = Counter(all_keywords)
        common = [kw for kw, count in counter.most_common(10) if count > 1]
        
        return common
    
    def generate_full_comparison(self) -> ComparisonResult:
        """生成完整对比报告"""
        table = self.generate_comparison_table()
        method_comp = self.compare_methods()
        result_comp = self.compare_results()
        sw_analysis = self.analyze_strengths_weaknesses()
        
        return ComparisonResult(
            papers=[p.title for p in self.papers],
            comparison_table=table,
            method_comparison=method_comp,
            result_comparison=result_comp,
            strengths_weaknesses=sw_analysis
        )
    
    def export_to_markdown(self, output_path: str):
        """导出对比报告为 Markdown"""
        result = self.generate_full_comparison()
        
        md_content = ["# 论文对比分析报告\n"]
        md_content.append(f"**对比论文数量**: {len(self.papers)}\n")
        md_content.append("---\n")
        
        # 基本信息表格
        md_content.append("## 基本信息对比\n")
        if result.comparison_table is not None and not result.comparison_table.empty:
            md_content.append(result.comparison_table.to_markdown(index=False))
        md_content.append("\n---\n")
        
        # 方法对比
        md_content.append(result.method_comparison)
        md_content.append("\n---\n")
        
        # 结果对比
        md_content.append(result.result_comparison)
        md_content.append("\n---\n")
        
        # 优缺点分析
        md_content.append("## 优缺点分析\n")
        for paper_title, analysis in result.strengths_weaknesses.items():
            md_content.append(f"\n### {paper_title}")
            if analysis["strengths"]:
                md_content.append("**优点**:")
                for s in analysis["strengths"]:
                    md_content.append(f"- {s}")
            if analysis["weaknesses"]:
                md_content.append("**不足**:")
                for w in analysis["weaknesses"]:
                    md_content.append(f"- {w}")
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(md_content))
        
        return output_path


# 需要导入 re
import re


def compare_papers(papers: List[PaperInfo], output_path: Optional[str] = None) -> ComparisonResult:
    """便捷函数：对比多篇论文"""
    analyzer = ComparisonAnalyzer()
    analyzer.add_papers(papers)
    
    result = analyzer.generate_full_comparison()
    
    if output_path:
        analyzer.export_to_markdown(output_path)
    
    return result


if __name__ == "__main__":
    # 测试示例
    print("对比分析模块测试")
    print("用法：在 dashboard.py 中集成使用")
