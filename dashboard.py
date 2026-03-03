"""
AI 研究助手 - 主界面
AI Research Assistant Dashboard

基于 Streamlit 的学术论文辅助研究工具
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import json
import os

# 导入自定义模块
from paper_parser import PaperParser, PaperInfo
from comparison_analyzer import ComparisonAnalyzer
from trend_analyzer import TrendAnalyzer

# 页面配置
st.set_page_config(
    page_title="AI 研究助手",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .paper-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# 初始化 session state
if 'papers' not in st.session_state:
    st.session_state.papers = []
if 'comparison_results' not in st.session_state:
    st.session_state.comparison_results = None


def main():
    """主函数"""
    
    # 标题
    st.markdown('<div class="main-header">📚 AI 研究助手</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">基于 LLM 的学术论文辅助研究工具</div>', unsafe_allow_html=True)
    
    # 侧边栏导航
    with st.sidebar:
        st.header("🧭 导航")
        page = st.radio(
            "选择功能",
            ["📄 论文解析", "📊 对比分析", "📈 趋势分析", "🕸️ 引用网络", "⚙️ 设置"],
            label_visibility="collapsed"
        )
        
        st.divider()
        
        # 已加载论文统计
        st.subheader("📊 当前状态")
        st.metric("已加载论文", len(st.session_state.papers))
        
        if len(st.session_state.papers) > 0:
            st.info(f"已加载 {len(st.session_state.papers)} 篇论文")
            if st.button("清空所有论文"):
                st.session_state.papers = []
                st.rerun()
    
    # 根据选择显示不同页面
    if page == "📄 论文解析":
        show_paper_parser()
    elif page == "📊 对比分析":
        show_comparison()
    elif page == "📈 趋势分析":
        show_trend_analysis()
    elif page == "🕸️ 引用网络":
        show_citation_network()
    elif page == "⚙️ 设置":
        show_settings()


def show_paper_parser():
    """论文解析页面"""
    st.header("📄 论文智能解析")
    st.markdown("上传 PDF 论文，自动提取摘要、方法、实验、结论等关键信息")
    
    # 文件上传
    uploaded_file = st.file_uploader(
        "上传 PDF 论文",
        type=["pdf"],
        help="支持 PDF 格式的学术论文"
    )
    
    if uploaded_file:
        # 保存临时文件
        temp_path = Path("temp_papers")
        temp_path.mkdir(exist_ok=True)
        temp_file = temp_path / uploaded_file.name
        
        with open(temp_file, "wb") as f:
            f.write(uploaded_file.getvalue())
        
        # 解析论文
        with st.spinner("正在解析论文..."):
            parser = PaperParser()
            paper = parser.parse(str(temp_file))
        
        if paper.title or paper.abstract:
            st.success("✅ 论文解析成功！")
            
            # 添加到 session state
            st.session_state.papers.append(paper)
            
            # 显示论文信息
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.subheader("📝 基本信息")
                
                if paper.title:
                    st.markdown(f"**标题**: {paper.title}")
                
                if paper.abstract:
                    with st.expander("📋 摘要", expanded=True):
                        st.write(paper.abstract)
                
                if paper.method:
                    with st.expander("🔬 方法"):
                        st.write(paper.method[:1000] + "..." if len(paper.method) > 1000 else paper.method)
                
                if paper.experiments:
                    with st.expander("📊 实验"):
                        st.write(paper.experiments[:1000] + "..." if len(paper.experiments) > 1000 else paper.experiments)
                
                if paper.conclusion:
                    with st.expander("✅ 结论"):
                        st.write(paper.conclusion)
            
            with col2:
                st.subheader("📊 统计信息")
                
                st.metric("摘要长度", f"{len(paper.abstract)} 字符")
                st.metric("方法长度", f"{len(paper.method)} 字符")
                st.metric("实验长度", f"{len(paper.experiments)} 字符")
                
                if paper.keywords:
                    st.markdown("**关键词**:")
                    for kw in paper.keywords[:10]:
                        st.caption(f"🏷️ {kw}")
                
                st.metric("参考文献", f"{len(paper.references)} 篇")
                
                # 提取的算法
                algorithms = parser.extract_algorithm_pseudocode()
                if algorithms:
                    with st.expander(f"🧮 提取的算法 ({len(algorithms)})"):
                        for i, algo in enumerate(algorithms, 1):
                            st.code(algo[:500], language="text")
            
            # 导出选项
            st.divider()
            st.subheader("💾 导出")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("导出为 JSON", use_container_width=True):
                    json_str = paper.to_json()
                    st.download_button(
                        label="📥 下载 JSON",
                        data=json_str,
                        file_name=f"{paper.title[:50]}.json",
                        mime="application/json"
                    )
            
            with col2:
                if st.button("导出为 Markdown", use_container_width=True):
                    md_content = f"# {paper.title}\n\n"
                    md_content += f"## 摘要\n{paper.abstract}\n\n"
                    md_content += f"## 方法\n{paper.method}\n\n"
                    md_content += f"## 实验\n{paper.experiments}\n\n"
                    md_content += f"## 结论\n{paper.conclusion}\n"
                    
                    st.download_button(
                        label="📥 下载 Markdown",
                        data=md_content,
                        file_name=f"{paper.title[:50]}.md",
                        mime="text/markdown"
                    )
            
            with col3:
                if st.button("复制摘要", use_container_width=True):
                    st.code(paper.abstract, language="text")
        else:
            st.error("❌ 解析失败，请检查 PDF 文件")
    
    # 显示已解析的论文列表
    if st.session_state.papers:
        st.divider()
        st.subheader(f"📚 已解析的论文 ({len(st.session_state.papers)})")
        
        for i, paper in enumerate(st.session_state.papers):
            with st.expander(f"{i+1}. {paper.title[:100] if paper.title else '未知标题'}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**摘要**: {paper.abstract[:200]}..." if len(paper.abstract) > 200 else f"**摘要**: {paper.abstract}")
                with col2:
                    st.write(f"**关键词**: {', '.join(paper.keywords[:5])}" if paper.keywords else "**关键词**: 无")


def show_comparison():
    """对比分析页面"""
    st.header("📊 跨论文对比分析")
    st.markdown("对多篇论文进行方法、结果、优缺点对比")
    
    if len(st.session_state.papers) < 2:
        st.warning(f"⚠️ 需要至少 2 篇论文才能进行对比，当前已加载 {len(st.session_state.papers)} 篇")
        st.info("💡 请先在「论文解析」页面上传论文")
        return
    
    # 选择要对比的论文
    st.subheader("选择对比的论文")
    selected_papers = st.multiselect(
        "选择论文",
        options=range(len(st.session_state.papers)),
        format_func=lambda i: f"{i+1}. {st.session_state.papers[i].title[:80]}" if st.session_state.papers[i].title else f"论文 {i+1}",
        default=range(min(2, len(st.session_state.papers)))
    )
    
    if len(selected_papers) >= 2:
        if st.button("开始对比分析", type="primary"):
            with st.spinner("正在分析..."):
                # 创建对比分析器
                analyzer = ComparisonAnalyzer()
                
                for idx in selected_papers:
                    analyzer.add_paper(st.session_state.papers[idx])
                
                # 生成对比结果
                result = analyzer.generate_full_comparison()
                st.session_state.comparison_results = result
            
            # 显示对比表格
            st.subheader("📋 基本信息对比")
            if result.comparison_table is not None and not result.comparison_table.empty:
                st.dataframe(result.comparison_table, use_container_width=True)
            
            # 方法对比
            st.subheader("🔬 方法论对比")
            st.markdown(result.method_comparison)
            
            # 结果对比
            st.subheader("📊 实验结果对比")
            st.markdown(result.result_comparison)
            
            # 优缺点分析
            st.subheader("⭐ 优缺点分析")
            
            for paper_title, analysis in result.strengths_weaknesses.items():
                with st.expander(f"📄 {paper_title}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("#### ✅ 优点")
                        for strength in analysis["strengths"]:
                            st.success(f"✓ {strength}")
                    
                    with col2:
                        st.markdown("#### ⚠️ 不足")
                        for weakness in analysis["weaknesses"]:
                            st.warning(f"✗ {weakness}")
            
            # 导出报告
            st.divider()
            st.subheader("💾 导出报告")
            
            if st.button("导出 Markdown 报告"):
                output_path = analyzer.export_to_markdown("comparison_report.md")
                with open(output_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                st.download_button(
                    label="📥 下载报告",
                    data=content,
                    file_name="comparison_report.md",
                    mime="text/markdown"
                )
    else:
        st.info("👆 请选择至少 2 篇论文进行对比")


def show_trend_analysis():
    """趋势分析页面"""
    st.header("📈 研究趋势分析")
    st.markdown("基于 arXiv 数据的研究热点分析")
    
    # 选择研究领域
    st.subheader("选择研究领域")
    
    research_areas = {
        "LLM (大语言模型)": "large language model",
        "Computer Vision (计算机视觉)": "computer vision",
        "NLP (自然语言处理)": "natural language processing",
        "Reinforcement Learning (强化学习)": "reinforcement learning",
        "Generative AI (生成式 AI)": "generative AI",
        "AI Safety (AI 安全)": "AI safety",
        "Multimodal (多模态)": "multimodal learning",
        "自定义": "custom"
    }
    
    selected_area = st.selectbox("研究领域", list(research_areas.keys()))
    
    if selected_area == "自定义":
        keyword = st.text_input("输入关键词", "transformer")
    else:
        keyword = research_areas[selected_area]
        st.info(f"搜索关键词：`{keyword}`")
    
    # 时间范围
    months = st.slider("分析时间范围 (月)", 3, 24, 12)
    
    if st.button("开始分析", type="primary"):
        with st.spinner(f"正在分析 {keyword} 的研究趋势..."):
            analyzer = TrendAnalyzer()
            trend_data = analyzer.analyze_trend(keyword, months)
        
        if trend_data.paper_count > 0:
            st.success(f"✅ 找到 {trend_data.paper_count} 篇相关论文")
            
            # 时间序列图
            st.subheader("📊 月度论文数量趋势")
            
            if trend_data.time_series is not None and not trend_data.time_series.empty:
                fig = px.line(
                    trend_data.time_series,
                    x="month",
                    y="count",
                    title=f"{keyword} 月度论文发表趋势",
                    markers=True
                )
                fig.update_layout(xaxis_title="月份", yaxis_title="论文数量")
                st.plotly_chart(fig, use_container_width=True)
            
            # 热点论文
            st.subheader("🔥 代表性论文")
            
            for i, paper in enumerate(trend_data.top_papers[:5], 1):
                with st.expander(f"{i}. {paper['title'][:100]}"):
                    st.markdown(f"**作者**: {', '.join(paper['authors'][:3])}{' et al.' if len(paper['authors']) > 3 else ''}")
                    st.markdown(f"**发布时间**: {paper['published']}")
                    st.markdown(f"**分类**: {', '.join(paper['categories'])}")
                    st.markdown(f"**摘要**: {paper['summary_preview']}")
                    
                    # arXiv 链接
                    arxiv_url = f"https://arxiv.org/abs/{paper['arxiv_id']}"
                    st.markdown(f"[📄 查看 arXiv 原文]({arxiv_url})")
            
            # 相关关键词
            st.subheader("🏷️ 相关技术关键词")
            
            if trend_data.related_keywords:
                cols = st.columns(2)
                for i, kw in enumerate(trend_data.related_keywords):
                    with cols[i % 2]:
                        st.caption(f"🔹 {kw}")
            else:
                st.info("未提取到相关关键词")
        else:
            st.warning("⚠️ 未找到相关论文，请尝试其他关键词")


def show_citation_network():
    """引用网络页面"""
    st.header("🕸️ 引用网络分析")
    st.markdown("论文引用关系可视化（功能开发中）")
    
    st.info("""
    ### 即将上线的功能：
    
    - 📊 引用关系图谱可视化
    - 🔍 关键论文识别
    - 📈 引用趋势分析
    - 🌐 研究社区发现
    
    当前版本支持基础的参考文献提取，完整的引用网络分析功能将在后续版本中推出。
    """)
    
    if st.session_state.papers:
        st.subheader("已加载论文的参考文献统计")
        
        data = []
        for i, paper in enumerate(st.session_state.papers):
            data.append({
                "论文": f"{i+1}. {paper.title[:50]}" if paper.title else f"论文 {i+1}",
                "参考文献数量": len(paper.references)
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True)
        
        # 简单的柱状图
        if len(data) > 0:
            fig = px.bar(
                df,
                x="论文",
                y="参考文献数量",
                title="各论文参考文献数量对比"
            )
            st.plotly_chart(fig, use_container_width=True)


def show_settings():
    """设置页面"""
    st.header("⚙️ 设置")
    
    st.subheader("📁 数据管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("清空所有数据", use_container_width=True):
            st.session_state.papers = []
            st.session_state.comparison_results = None
            st.success("✅ 数据已清空")
            st.rerun()
    
    with col2:
        st.metric("已加载论文数", len(st.session_state.papers))
    
    st.divider()
    
    st.subheader("ℹ️ 关于")
    st.markdown("""
    **AI 研究助手** v1.0
    
    基于 LLM 的学术论文辅助研究工具
    
    **功能特性**:
    - 📄 论文智能解析
    - 📊 跨论文对比分析
    - 📈 研究趋势分析
    - 🕸️ 引用网络分析（开发中）
    
    **技术栈**:
    - Streamlit
    - PyPDF2
    - Pandas & NumPy
    - Plotly
    - arXiv API
    
    **作者**: AI Research Team
    """)


if __name__ == "__main__":
    main()
