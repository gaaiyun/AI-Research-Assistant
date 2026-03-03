"""
论文解析模块 - Paper Parser Module
支持 PDF 解析、摘要提取、关键信息抽取
"""

import PyPDF2
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import json


@dataclass
class PaperInfo:
    """论文信息数据类"""
    title: str = ""
    abstract: str = ""
    authors: List[str] = None
    keywords: List[str] = None
    method: str = ""
    experiments: str = ""
    conclusion: str = ""
    references: List[str] = None
    
    def __post_init__(self):
        if self.authors is None:
            self.authors = []
        if self.keywords is None:
            self.keywords = []
        if self.references is None:
            self.references = []
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "keywords": self.keywords,
            "method": self.method,
            "experiments": self.experiments,
            "conclusion": self.conclusion,
            "references": self.references
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class PaperParser:
    """论文解析器"""
    
    # 常见章节标题模式
    SECTION_PATTERNS = {
        "abstract": [r"abstract", r"摘要", r"summary"],
        "introduction": [r"introduction", r"intro", r"引言", r"背景"],
        "method": [r"method", r"methodology", r"approach", r"方法", r"模型", r"算法"],
        "experiment": [r"experiment", r"evaluation", r"result", r"实验", r"结果", r"评估"],
        "conclusion": [r"conclusion", r"concluding", r"总结", r"结论", r"未来工作"],
        "references": [r"reference", r"bibliography", r"文献", r"引用"]
    }
    
    def __init__(self):
        self.text = ""
        self.pages = []
    
    def load_pdf(self, pdf_path: str) -> bool:
        """加载 PDF 文件"""
        try:
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                self.pages = []
                self.text = ""
                
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        self.pages.append(page_text)
                        self.text += page_text + "\n"
                
                return len(self.text) > 0
        except Exception as e:
            print(f"加载 PDF 失败：{e}")
            return False
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """从 PDF 提取纯文本"""
        if self.load_pdf(pdf_path):
            return self.text
        return ""
    
    def _find_section(self, text: str, patterns: List[str]) -> Tuple[int, int]:
        """查找章节位置"""
        for pattern in patterns:
            match = re.search(rf'\n\s*{pattern}[^\n]*\n', text, re.IGNORECASE)
            if match:
                start = match.start()
                # 查找下一个章节开始位置
                next_sections = []
                for sec_patterns in self.SECTION_PATTERNS.values():
                    for p in sec_patterns:
                        next_match = re.search(rf'\n\s*{p}[^\n]*\n', text[start+1:], re.IGNORECASE)
                        if next_match:
                            next_sections.append(next_match.start())
                
                end = min(next_sections) if next_sections else len(text)
                return start, start + end + 1
        
        return -1, -1
    
    def extract_abstract(self) -> str:
        """提取摘要"""
        start, end = self._find_section(self.text, self.SECTION_PATTERNS["abstract"])
        if start != -1:
            return self.text[start:end].strip()
        
        # 尝试查找 "ABSTRACT" 关键词
        abstract_match = re.search(r'ABSTRACT\s*\n(.*?)(?=\n\s*(?:INTRODUCTION|1\.|I\.))', 
                                   self.text, re.IGNORECASE | re.DOTALL)
        if abstract_match:
            return abstract_match.group(1).strip()
        
        return ""
    
    def extract_method(self) -> str:
        """提取方法部分"""
        start, end = self._find_section(self.text, self.SECTION_PATTERNS["method"])
        if start != -1:
            return self.text[start:end].strip()
        return ""
    
    def extract_experiments(self) -> str:
        """提取实验部分"""
        start, end = self._find_section(self.text, self.SECTION_PATTERNS["experiment"])
        if start != -1:
            return self.text[start:end].strip()
        return ""
    
    def extract_conclusion(self) -> str:
        """提取结论部分"""
        start, end = self._find_section(self.text, self.SECTION_PATTERNS["conclusion"])
        if start != -1:
            return self.text[start:end].strip()
        return ""
    
    def extract_references(self) -> List[str]:
        """提取参考文献"""
        start, end = self._find_section(self.text, self.SECTION_PATTERNS["references"])
        if start != -1:
            ref_text = self.text[start:end]
            # 提取参考文献条目
            refs = re.findall(r'\[\d+\]\s*(.+?)(?=\[\d+\]|$)', ref_text, re.DOTALL)
            return [ref.strip() for ref in refs if ref.strip()]
        return []
    
    def extract_keywords(self) -> List[str]:
        """提取关键词"""
        # 查找关键词部分
        keywords_match = re.search(r'keywords?\s*[:：]\s*(.+?)(?=\n\n|\n\s*\d|\n\s*[A-Z])', 
                                   self.text, re.IGNORECASE)
        if keywords_match:
            keywords_text = keywords_match.group(1)
            # 分割关键词
            keywords = re.split(r'[;,，]', keywords_text)
            return [kw.strip() for kw in keywords if kw.strip()]
        return []
    
    def extract_title(self) -> str:
        """提取标题（通常是第一行非空文本）"""
        lines = self.text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and len(line) > 10 and len(line) < 500:
                # 排除一些常见非标题文本
                if not any(word in line.lower() for word in ['abstract', 'author', 'date', 'copyright']):
                    return line
        return ""
    
    def extract_algorithm_pseudocode(self) -> List[str]:
        """从论文中提取伪代码/算法"""
        algorithms = []
        
        # 查找 Algorithm 环境
        algo_matches = re.findall(r'Algorithm\s*\d*[:：]?\s*(.+?)(?=Algorithm\s*\d|References|Bibliography|$)', 
                                  self.text, re.IGNORECASE | re.DOTALL)
        algorithms.extend(algo_matches)
        
        # 查找伪代码块（通常有 Input/Output）
        pseudocode_matches = re.findall(r'(Input:.*?Output:.*?)(?=\n\s*\n|\Z)', 
                                        self.text, re.IGNORECASE | re.DOTALL)
        algorithms.extend(pseudocode_matches)
        
        return algorithms
    
    def parse(self, pdf_path: str) -> PaperInfo:
        """完整解析论文"""
        if not self.load_pdf(pdf_path):
            return PaperInfo()
        
        paper = PaperInfo()
        paper.title = self.extract_title()
        paper.abstract = self.extract_abstract()
        paper.method = self.extract_method()
        paper.experiments = self.extract_experiments()
        paper.conclusion = self.extract_conclusion()
        paper.keywords = self.extract_keywords()
        paper.references = self.extract_references()
        
        return paper
    
    def get_summary(self, paper: PaperInfo, max_length: int = 500) -> str:
        """生成论文摘要总结"""
        summary_parts = []
        
        if paper.title:
            summary_parts.append(f"**标题**: {paper.title}")
        
        if paper.abstract:
            abstract = paper.abstract[:max_length] + "..." if len(paper.abstract) > max_length else paper.abstract
            summary_parts.append(f"**摘要**: {abstract}")
        
        if paper.method:
            method = paper.method[:200] + "..." if len(paper.method) > 200 else paper.method
            summary_parts.append(f"**方法**: {method}")
        
        if paper.conclusion:
            conclusion = paper.conclusion[:200] + "..." if len(paper.conclusion) > 200 else paper.conclusion
            summary_parts.append(f"**结论**: {conclusion}")
        
        return "\n\n".join(summary_parts)


def parse_paper(pdf_path: str) -> PaperInfo:
    """便捷函数：解析论文"""
    parser = PaperParser()
    return parser.parse(pdf_path)


if __name__ == "__main__":
    # 测试示例
    import sys
    if len(sys.argv) > 1:
        parser = PaperParser()
        paper = parser.parse(sys.argv[1])
        print(paper.to_json())
    else:
        print("用法：python paper_parser.py <pdf 文件路径>")
