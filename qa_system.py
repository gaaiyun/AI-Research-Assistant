"""
智能问答系统模块
基于论文内容的 QA 系统，支持语义搜索和答案提取
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from collections import Counter


@dataclass
class QAResult:
    """问答结果"""
    question: str
    answer: str
    confidence: float
    source_section: str
    source_page: int
    relevant_text: str


class QASystem:
    """论文问答系统"""
    
    def __init__(self):
        self.paper_data = None
        self.chunks = []
        self.chunk_embeddings = None
    
    def load_paper(self, paper_data: Dict):
        """加载论文数据"""
        self.paper_data = paper_data
        self._create_chunks()
    
    def _create_chunks(self):
        """将论文内容分块"""
        if not self.paper_data:
            return
        
        self.chunks = []
        
        # 按章节分块
        sections = self.paper_data.get('sections', [])
        for section in sections:
            title = section.get('title', '')
            content = section.get('content', '')
            page = section.get('page_start', 0)
            
            # 将长内容进一步分块
            chunk_size = 500
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i + chunk_size]
                if chunk.strip():
                    self.chunks.append({
                        'text': chunk,
                        'section': title,
                        'page': page,
                        'start_pos': i
                    })
        
        # 添加摘要作为独立块
        abstract = self.paper_data.get('abstract', '')
        if abstract:
            self.chunks.append({
                'text': abstract,
                'section': 'Abstract',
                'page': 0,
                'start_pos': 0
            })
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 移除停用词
        stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
            'this', 'that', 'these', 'those', 'it', 'its', 'as', 'if', 'when',
            'than', 'because', 'while', 'although', 'though', 'after', 'before',
            'until', 'since', 'unless', 'where', 'which', 'who', 'whom', 'whose',
            'what', 'whatever', 'whether', 'such', 'so', 'very', 'just', 'only',
            'also', 'even', 'still', 'already', 'yet', 'again', 'further',
            '然后', '的', '了', '在', '是', '就', '都', '而', '及', '与', '着',
            '我们', '他们', '这个', '那个', '可以', '可能', '应该', '需要'
        }
        
        # 提取单词
        words = re.findall(r'\b[a-zA-Z]{3,}\b|\b[\u4e00-\u9fa5]{2,}\b', text.lower())
        
        # 过滤停用词
        keywords = [w for w in words if w.lower() not in stopwords]
        
        return keywords
    
    def _calculate_similarity(self, question: str, chunk_text: str) -> float:
        """计算问题和文本块的相似度"""
        question_keywords = set(self._extract_keywords(question))
        chunk_keywords = set(self._extract_keywords(chunk_text))
        
        if not question_keywords or not chunk_keywords:
            return 0.0
        
        # Jaccard 相似度
        intersection = question_keywords.intersection(chunk_keywords)
        union = question_keywords.union(chunk_keywords)
        
        jaccard_sim = len(intersection) / len(union) if union else 0.0
        
        # 考虑关键词权重
        question_word_counts = Counter(self._extract_keywords(question))
        chunk_word_counts = Counter(self._extract_keywords(chunk_text))
        
        # 计算加权相似度
        weighted_sim = 0.0
        total_weight = 0
        
        for word, count in question_word_counts.items():
            if word in chunk_word_counts:
                weighted_sim += count * min(count, chunk_word_counts[word])
                total_weight += count
        
        if total_weight > 0:
            weighted_sim = weighted_sim / total_weight
        else:
            weighted_sim = 0.0
        
        # 综合相似度
        return 0.5 * jaccard_sim + 0.5 * weighted_sim
    
    def _find_relevant_chunks(self, question: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """查找相关的文本块"""
        if not self.chunks:
            return []
        
        # 计算每个 chunk 的相似度
        chunk_scores = []
        for chunk in self.chunks:
            score = self._calculate_similarity(question, chunk['text'])
            chunk_scores.append((chunk, score))
        
        # 按相似度排序
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        
        return chunk_scores[:top_k]
    
    def _extract_answer(self, question: str, context: str) -> str:
        """从上下文中提取答案"""
        question_lower = question.lower()
        
        # 问题类型检测
        if any(word in question_lower for word in ['what', '哪些', '什么', 'which']):
            # 事实性问题
            return self._extract_factual_answer(question, context)
        elif any(word in question_lower for word in ['how', '如何', '怎样']):
            # 方法性问题
            return self._extract_method_answer(question, context)
        elif any(word in question_lower for word in ['why', '为什么', '原因']):
            # 原因性问题
            return self._extract_reason_answer(question, context)
        elif any(word in question_lower for word in ['when', '何时', '时间']):
            # 时间性问题
            return self._extract_time_answer(question, context)
        else:
            # 通用答案提取
            return self._extract_general_answer(question, context)
    
    def _extract_factual_answer(self, question: str, context: str) -> str:
        """提取事实性答案"""
        # 查找包含关键词的句子
        keywords = self._extract_keywords(question)
        sentences = re.split(r'[.!?。！？]', context)
        
        best_sentence = ""
        best_score = 0
        
        for sentence in sentences:
            sentence_keywords = set(self._extract_keywords(sentence))
            overlap = len(set(keywords).intersection(sentence_keywords))
            
            if overlap > best_score and len(sentence) > 20:
                best_score = overlap
                best_sentence = sentence.strip()
        
        return best_sentence if best_sentence else context[:200]
    
    def _extract_method_answer(self, question: str, context: str) -> str:
        """提取方法性答案"""
        # 查找方法相关的句子
        method_indicators = ['method', 'approach', 'technique', 'algorithm', 
                           '方法', '步骤', '流程', 'process', 'procedure']
        
        sentences = re.split(r'[.!?。！？]', context)
        method_sentences = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in method_indicators):
                method_sentences.append(sentence.strip())
        
        if method_sentences:
            return ' '.join(method_sentences[:3])
        
        return self._extract_factual_answer(question, context)
    
    def _extract_reason_answer(self, question: str, context: str) -> str:
        """提取原因性答案"""
        reason_indicators = ['because', 'therefore', 'thus', 'hence', 'due to',
                           '因为', '所以', '因此', '由于', 'reason', 'cause']
        
        sentences = re.split(r'[.!?。！？]', context)
        reason_sentences = []
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in reason_indicators):
                reason_sentences.append(sentence.strip())
        
        if reason_sentences:
            return ' '.join(reason_sentences[:3])
        
        return self._extract_factual_answer(question, context)
    
    def _extract_time_answer(self, question: str, context: str) -> str:
        """提取时间性答案"""
        # 查找日期和时间表达式
        date_patterns = [
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}'
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, context, re.IGNORECASE))
        
        if dates:
            return f"Found dates: {', '.join(dates[:3])}"
        
        return self._extract_factual_answer(question, context)
    
    def _extract_general_answer(self, question: str, context: str) -> str:
        """提取通用答案"""
        # 返回最相关的句子
        sentences = re.split(r'[.!?。！？]', context)
        
        if sentences:
            # 返回第一个完整的句子
            for sentence in sentences:
                if len(sentence.strip()) > 30:
                    return sentence.strip()
        
        return context[:200]
    
    def answer_question(self, question: str) -> Optional[QAResult]:
        """回答问题"""
        if not self.paper_data or not self.chunks:
            return None
        
        # 查找相关的 chunk
        relevant_chunks = self._find_relevant_chunks(question, top_k=3)
        
        if not relevant_chunks or relevant_chunks[0][1] < 0.1:
            return QAResult(
                question=question,
                answer="派蒙没有找到相关信息呢~ 请尝试换一种问法或者检查问题是否与论文内容相关。",
                confidence=0.0,
                source_section="N/A",
                source_page=0,
                relevant_text=""
            )
        
        # 从最相关的 chunk 中提取答案
        best_chunk, confidence = relevant_chunks[0]
        answer = self._extract_answer(question, best_chunk['text'])
        
        return QAResult(
            question=question,
            answer=answer,
            confidence=confidence,
            source_section=best_chunk['section'],
            source_page=best_chunk['page'],
            relevant_text=best_chunk['text'][:300]
        )
    
    def search_papers(self, query: str, top_k: int = 5) -> List[Dict]:
        """搜索相关内容"""
        if not self.chunks:
            return []
        
        relevant_chunks = self._find_relevant_chunks(query, top_k)
        
        results = []
        for chunk, score in relevant_chunks:
            if score > 0.1:
                results.append({
                    'text': chunk['text'][:200],
                    'section': chunk['section'],
                    'page': chunk['page'],
                    'relevance_score': score
                })
        
        return results
    
    def get_summary(self) -> str:
        """获取论文摘要"""
        if not self.paper_data:
            return ""
        
        return self.paper_data.get('abstract', 'No abstract available')
    
    def get_key_points(self) -> List[str]:
        """获取关键点"""
        if not self.paper_data:
            return []
        
        key_points = []
        
        # 从标题提取
        title = self.paper_data.get('title', '')
        if title:
            key_points.append(f"Title: {title}")
        
        # 从关键词提取
        keywords = self.paper_data.get('keywords', [])
        if keywords:
            key_points.append(f"Keywords: {', '.join(keywords[:5])}")
        
        # 从摘要提取关键句
        abstract = self.paper_data.get('abstract', '')
        if abstract:
            sentences = re.split(r'[.!?。！？]', abstract)
            for sentence in sentences[:3]:
                if len(sentence.strip()) > 30:
                    key_points.append(sentence.strip())
        
        return key_points


def create_qa_system(paper_data: Dict) -> QASystem:
    """便捷函数：创建 QA 系统"""
    qa = QASystem()
    qa.load_paper(paper_data)
    return qa


def answer_question(paper_data: Dict, question: str) -> Optional[QAResult]:
    """便捷函数：直接回答问题"""
    qa = create_qa_system(paper_data)
    return qa.answer_question(question)


if __name__ == "__main__":
    # 测试代码
    print("QA System Module")
    print("Use create_qa_system() to create a QA system for a paper")
    print("Use answer_question() to answer questions about a paper")
