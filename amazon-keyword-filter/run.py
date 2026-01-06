#!/usr/bin/env python3
"""
Amazon Keyword Filter Skill - 统一入口点

此脚本是 amazon-keyword-filter skill 的主入口点，
设计为让 Claude Code 可以直接调用。

使用方法:
    python run.py analyze <keyword> <product_image>
    python run.py batch <excel_file> <product_image>
    python run.py generate-description <product_image>
    python run.py auto-filter <product_image> <excel_file>
    python run.py setup
"""

import sys
import os
import argparse
from pathlib import Path

# 添加 scripts 目录到 Python 路径
SKILL_DIR = Path(__file__).parent
SCRIPTS_DIR = SKILL_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def cmd_setup(args):
    """运行环境设置"""
    from setup_env import setup
    print("运行环境设置...")
    success = setup()
    return 0 if success else 1


def cmd_analyze(args):
    """单个关键词分析"""
    from analyze_keyword_with_ai import analyze_keyword_with_ai

    result = analyze_keyword_with_ai(
        keyword=args.keyword,
        product_image=args.product_image,
        amazon_domain=args.amazon_domain,
        max_products=args.max_products,
        grid_columns=args.columns,
        similarity_threshold=args.threshold,
        output_dir=args.output,
        debug=args.debug,
        headless=not args.no_headless,
        no_ssl_verify=args.no_ssl_verify
    )

    if result.get("error"):
        print(f"\n❌ 分析失败: {result['error']}")
        return 1

    print(f"\n✅ 分析完成")
    return 0


def cmd_batch(args):
    """批量关键词分析"""
    from batch_analyze_with_ai import batch_analyze, load_keywords_from_excel

    # 加载关键词
    try:
        keywords = load_keywords_from_excel(args.excel_file, args.column)
        print(f"✓ 从 Excel 加载了 {len(keywords)} 个关键词")
    except Exception as e:
        print(f"❌ 加载 Excel 失败: {e}")
        return 1

    # 执行批量分析
    results = batch_analyze(
        keywords=keywords,
        product_image=args.product_image,
        amazon_domain=args.amazon_domain,
        max_products=args.max_products,
        grid_columns=args.columns,
        similarity_threshold=args.threshold,
        output_dir=args.output,
        cache_file=args.cache,
        debug=args.debug,
        headless=not args.no_headless,
        no_ssl_verify=args.no_ssl_verify,
        concurrent_workers=args.workers,
        enable_filter=not args.no_filter
    )

    print(f"\n✅ 批量分析完成")
    return 0


def cmd_generate_description(args):
    """生成产品描述"""
    print(f"生成产品描述: {args.product_image}")

    # 导入并调用生成描述脚本
    script_path = SCRIPTS_DIR / "generate_product_description.py"

    if not script_path.exists():
        print(f"❌ 脚本不存在: {script_path}")
        return 1

    # 构建命令
    cmd = [
        sys.executable,
        str(script_path),
        args.product_image
    ]

    if args.output:
        cmd.extend(['-o', args.output])
    if args.format:
        cmd.extend(['--format', args.format])

    import subprocess
    result = subprocess.run(cmd)
    return result.returncode


def cmd_auto_filter(args):
    """自动化关键词过滤"""
    print(f"自动过滤关键词")

    script_path = SCRIPTS_DIR / "auto_filter_with_ai.py"

    if not script_path.exists():
        print(f"❌ 脚本不存在: {script_path}")
        return 1

    cmd = [
        sys.executable,
        str(script_path),
        args.product_image,
        args.excel_file
    ]

    if args.threshold:
        cmd.extend(['--threshold', str(args.threshold)])
    if args.column:
        cmd.extend(['--column', args.column])
    if args.output:
        cmd.extend(['-o', args.output])

    import subprocess
    result = subprocess.run(cmd)
    return result.returncode


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='Amazon Keyword Filter - 统一入口点',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 环境设置
  python run.py setup

  # 单个关键词分析
  python run.py analyze "wireless earbuds" product.jpg

  # 批量分析
  python run.py batch keywords.xlsx product.jpg

  # 生成产品描述
  python run.py generate-description product.jpg

  # 自动过滤关键词
  python run.py auto-filter product.jpg keywords.xlsx

更多信息: 查看 SKILL.md
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # ==================== setup 命令 ====================
    parser_setup = subparsers.add_parser('setup', help='运行环境设置')

    # ==================== analyze 命令 ====================
    parser_analyze = subparsers.add_parser('analyze', help='分析单个关键词')
    parser_analyze.add_argument('keyword', help='搜索关键词')
    parser_analyze.add_argument('product_image', help='基准产品图片路径')
    parser_analyze.add_argument('--amazon-domain', default='amazon.com', help='Amazon域名')
    parser_analyze.add_argument('--max-products', type=int, default=20, help='最多获取商品数')
    parser_analyze.add_argument('--columns', type=int, default=5, help='网格列数')
    parser_analyze.add_argument('--threshold', type=float, default=0.85, help='相似度阈值')
    parser_analyze.add_argument('-o', '--output', default='./ai_analysis_results', help='输出目录')
    parser_analyze.add_argument('--debug', action='store_true', help='调试模式')
    parser_analyze.add_argument('--no-headless', action='store_true', help='显示浏览器')
    parser_analyze.add_argument('--no-ssl-verify', action='store_true', help='禁用SSL验证')

    # ==================== batch 命令 ====================
    parser_batch = subparsers.add_parser('batch', help='批量分析关键词')
    parser_batch.add_argument('excel_file', help='Excel文件路径')
    parser_batch.add_argument('product_image', help='基准产品图片路径')
    parser_batch.add_argument('--column', default='关键词', help='关键词列名')
    parser_batch.add_argument('--amazon-domain', default='amazon.com', help='Amazon域名')
    parser_batch.add_argument('--max-products', type=int, default=20, help='最多获取商品数')
    parser_batch.add_argument('--columns', type=int, default=5, help='网格列数')
    parser_batch.add_argument('--threshold', type=float, default=0.85, help='相似度阈值')
    parser_batch.add_argument('-o', '--output', default='./ai_batch_results', help='输出目录')
    parser_batch.add_argument('--cache', help='进度缓存文件路径')
    parser_batch.add_argument('--workers', type=int, default=5, help='并发工作线程数')
    parser_batch.add_argument('--no-filter', action='store_true', help='禁用AI关键词过滤')
    parser_batch.add_argument('--debug', action='store_true', help='调试模式')
    parser_batch.add_argument('--no-headless', action='store_true', help='显示浏览器')
    parser_batch.add_argument('--no-ssl-verify', action='store_true', help='禁用SSL验证')

    # ==================== generate-description 命令 ====================
    parser_gen = subparsers.add_parser('generate-description', help='生成产品描述')
    parser_gen.add_argument('product_image', help='产品图片路径')
    parser_gen.add_argument('-o', '--output', help='输出文件路径')
    parser_gen.add_argument('--format', choices=['json', 'text'], default='json', help='输出格式')

    # ==================== auto-filter 命令 ====================
    parser_filter = subparsers.add_parser('auto-filter', help='自动化关键词过滤')
    parser_filter.add_argument('product_image', help='产品图片路径')
    parser_filter.add_argument('excel_file', help='关键词Excel文件路径')
    parser_filter.add_argument('--threshold', type=float, help='相似度阈值')
    parser_filter.add_argument('--column', help='关键词列名')
    parser_filter.add_argument('-o', '--output', help='输出文件路径')

    # 解析参数
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # 根据命令调用对应的函数
    commands = {
        'setup': cmd_setup,
        'analyze': cmd_analyze,
        'batch': cmd_batch,
        'generate-description': cmd_generate_description,
        'auto-filter': cmd_auto_filter
    }

    handler = commands.get(args.command)
    if handler:
        try:
            return handler(args)
        except Exception as e:
            print(f"\n❌ 执行失败: {e}")
            if args.debug if hasattr(args, 'debug') else False:
                import traceback
                traceback.print_exc()
            return 1
    else:
        print(f"❌ 未知命令: {args.command}")
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
