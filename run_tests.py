#!/usr/bin/env python
"""
测试运行脚本
使用方法：python run_tests.py [--coverage]
"""

import subprocess
import sys
import os
from pathlib import Path


def run_tests(with_coverage=False):
    """运行测试"""
    # 切换到项目目录
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # 构建 pytest 命令
    cmd = [sys.executable, "-m", "pytest", "tests/", "-v"]
    
    if with_coverage:
        cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])
    
    print(f"运行命令：{' '.join(cmd)}")
    print("=" * 60)
    
    # 运行测试
    result = subprocess.run(cmd)
    
    print("=" * 60)
    
    if result.returncode == 0:
        print("✅ 所有测试通过！")
        if with_coverage:
            print(f"📊 覆盖率报告已生成：{project_dir / 'htmlcov' / 'index.html'}")
    else:
        print("❌ 部分测试失败")
    
    return result.returncode


def run_single_test(test_file):
    """运行单个测试文件"""
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    cmd = [sys.executable, "-m", "pytest", test_file, "-v", "-s"]
    result = subprocess.run(cmd)
    
    return result.returncode


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="运行 AI 研究助手测试")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--test", type=str, help="运行单个测试文件")
    
    args = parser.parse_args()
    
    if args.test:
        returncode = run_single_test(args.test)
    else:
        returncode = run_tests(with_coverage=args.coverage)
    
    sys.exit(returncode)


if __name__ == "__main__":
    main()
