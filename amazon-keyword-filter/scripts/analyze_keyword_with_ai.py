#!/usr/bin/env python3
"""
基于 MCP 视觉 AI 的关键词分析脚本

流程:
1. 搜索亚马逊 → 获取图片 URL (JSON)
2. 下载并合并图片 → 网格大图
3. MCP 分析基准产品 → 提取特征元素用于加权
4. MCP 分析合并图片 → 识别相似产品
5. 加权评分并汇总

优势:
- 减少 MCP 调用次数 (10+ 次 → 2 次)
- AI 视觉理解比哈希值更智能
- 可提取语义特征 (颜色、形状、风格等)
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


def check_environment():
    """检查运行环境，如果需要则提示初始化"""
    # 检查虚拟环境
    in_venv = sys.prefix != sys.base_prefix

    # 检查关键依赖
    missing = []
    try:
        import selenium
    except ImportError:
        missing.append('selenium')

    try:
        import pandas
    except ImportError:
        missing.append('pandas')

    try:
        from PIL import Image
    except ImportError:
        missing.append('Pillow')

    if missing or not in_venv:
        print("=" * 60)
        print("⚠ 环境未就绪")
        print("=" * 60)

        if not in_venv:
            print("✗ 未检测到虚拟环境")

        if missing:
            print(f"✗ 缺少依赖: {', '.join(missing)}")

        print()
        print("请先运行环境初始化:")
        print("  python .claude/skills/amazon-keyword-filter/scripts/setup_env.py")
        print()
        print("或手动安装依赖:")
        print(f"  pip install {' '.join(missing)}")
        print("=" * 60)
        sys.exit(1)


# 运行环境检查
check_environment()

# 导入其他脚本
from search_amazon import search_amazon
from merge_images import merge_images_grid


def analyze_reference_product(product_image_path: str, debug: bool = False) -> Dict:
    """
    Step 3: 分析基准产品图片，提取特征元素

    这一步需要调用 MCP (zai-mcp-server__analyze_image)
    在实际使用时，由 Claude 调用 MCP 工具

    Args:
        product_image_path: 基准产品图片路径
        debug: 调试模式

    Returns:
        dict: 特征分析结果
        {
            "main_color": "蓝色",
            "style": "现代简约",
            "key_features": ["无线", "入耳式", "充电盒"],
            "material": "塑料",
            "shape": "椭圆形",
            "weights": {
                "color": 0.3,
                "style": 0.2,
                "features": 0.4,
                "shape": 0.1
            }
        }
    """
    if debug:
        print(f"[调试] 分析基准产品: {product_image_path}")

    # 这里返回一个占位符结果
    # 实际使用时，这一步由 Claude 通过 MCP 调用完成
    return {
        "image_path": product_image_path,
        "analyzed": False,
        "message": "需要通过 MCP 调用 zai-mcp-server__analyze_image",
        "mcp_prompt": f"""请分析这个产品图片，提取以下特征用于后续对比:

1. **主要颜色**: 产品的主色调
2. **风格**: 现代/经典/运动/商务等
3. **关键特征**: 列出 3-5 个最显著的特征
4. **材质**: 塑料/金属/布料等
5. **形状**: 整体形状描述

请以 JSON 格式返回，包含:
- main_color: 主要颜色
- style: 风格
- key_features: 关键特征列表
- material: 材质
- shape: 形状
- weights: 各特征的权重 (总和为 1.0)

图片路径: {product_image_path}"""
    }


def analyze_merged_grid(merged_image_path: str, reference_features: Dict,
                       grid_info: Dict, debug: bool = False) -> Dict:
    """
    Step 4: 分析合并的网格图片，识别与基准产品相似的商品

    这一步需要调用 MCP (zai-mcp-server__analyze_image)
    在实际使用时，由 Claude 调用 MCP 工具

    Args:
        merged_image_path: 合并后的网格图片路径
        reference_features: 基准产品的特征分析结果
        grid_info: 网格信息 (行数、列数)
        debug: 调试模式

    Returns:
        dict: 相似度分析结果
        {
            "total_products": 20,
            "similar_products": [
                {"position": 1, "similarity_score": 0.92, "reasons": ["颜色匹配", "形状相似"]},
                {"position": 5, "similarity_score": 0.85, "reasons": ["风格一致"]}
            ],
            "match_count": 2,
            "avg_similarity": 0.885
        }
    """
    if debug:
        print(f"[调试] 分析合并图片: {merged_image_path}")
        print(f"[调试] 网格信息: {grid_info}")

    # 生成 MCP 调用提示词
    mcp_prompt = f"""这是一个包含 {grid_info.get('total_images', 'N')} 个亚马逊商品的网格图片。
网格布局: {grid_info.get('rows', 'N')} 行 x {grid_info.get('columns', 5)} 列

**基准产品特征**:
{json.dumps(reference_features, indent=2, ensure_ascii=False)}

**任务**:
请逐个分析网格中的商品图片，判断哪些与基准产品相似。

**评分标准**:
- 颜色相似度: {reference_features.get('weights', {}).get('color', 0.3) * 100}%
- 风格相似度: {reference_features.get('weights', {}).get('style', 0.2) * 100}%
- 特征相似度: {reference_features.get('weights', {}).get('features', 0.4) * 100}%
- 形状相似度: {reference_features.get('weights', {}).get('shape', 0.1) * 100}%

**输出格式** (JSON):
{{
  "total_products": 数量,
  "similar_products": [
    {{"position": 位置序号(1-N), "similarity_score": 相似度(0-1), "reasons": ["匹配原因1", "原因2"]}},
    ...
  ],
  "match_count": 相似商品数量,
  "avg_similarity": 平均相似度
}}

**阈值**: 相似度 >= 0.85 才算匹配

图片路径: {merged_image_path}"""

    # 返回占位符结果
    return {
        "merged_image": merged_image_path,
        "analyzed": False,
        "message": "需要通过 MCP 调用 zai-mcp-server__analyze_image",
        "mcp_prompt": mcp_prompt
    }


def analyze_keyword_with_ai(
    keyword: str,
    product_image: str,
    reference_analysis: Optional[Dict] = None,
    amazon_domain: str = "amazon.com",
    max_products: int = 20,
    grid_columns: int = 5,
    similarity_threshold: float = 0.85,
    output_dir: str = "./ai_analysis_results",
    debug: bool = False,
    headless: bool = True,
    no_ssl_verify: bool = False
) -> Dict:
    """
    使用 AI 视觉分析处理单个关键词

    Args:
        keyword: 搜索关键词
        product_image: 基准产品图片路径
        reference_analysis: 预先分析的基准产品特征 (可选，避免重复分析)
        amazon_domain: 亚马逊域名
        max_products: 最多获取多少个商品
        grid_columns: 网格列数
        similarity_threshold: 相似度阈值
        output_dir: 输出目录
        debug: 调试模式
        headless: 无头模式
        no_ssl_verify: 禁用 SSL 验证

    Returns:
        dict: 分析结果
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # 为当前关键词创建子目录 (关键词在前，方便查找)
    safe_keyword = keyword.replace(" ", "_").replace("/", "_")[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    keyword_dir = output_path / f"{safe_keyword}_{timestamp}"
    keyword_dir.mkdir(exist_ok=True)

    result = {
        "keyword": keyword,
        "timestamp": timestamp,
        "output_dir": str(keyword_dir),
        "steps": {}
    }

    print(f"\n{'='*60}")
    print(f"分析关键词: {keyword}")
    print(f"{'='*60}\n")

    # ========== Step 1: 搜索亚马逊，获取图片 URL ==========
    print("[1/5] 搜索亚马逊...")
    search_result = search_amazon(
        keyword=keyword,
        amazon_domain=amazon_domain,
        max_products=max_products,
        debug=debug,
        headless=headless,
        wait_before_close=0,
        silent=True
    )

    image_urls = search_result["image_urls"]

    if not image_urls:
        result["error"] = "未找到商品图片"
        result["steps"]["search"] = {"success": False, "count": 0}
        return result

    result["steps"]["search"] = {
        "success": True,
        "count": len(image_urls),
        "urls": image_urls
    }

    # 保存 JSON
    json_path = keyword_dir / "search_result.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump({"keyword": keyword, "image_urls": image_urls, "count": len(image_urls)},
                  f, ensure_ascii=False, indent=2)

    print(f"  ✓ 找到 {len(image_urls)} 个商品")
    print(f"  ✓ JSON 已保存: {json_path}")

    # ========== Step 2: 下载并合并图片 ==========
    print("\n[2/5] 下载并合并图片...")
    merged_path = keyword_dir / "merged_grid.jpg"

    merge_result = merge_images_grid(
        image_urls=image_urls,
        output_path=str(merged_path),
        columns=grid_columns,
        img_size=(200, 200),
        debug=debug,
        no_ssl_verify=no_ssl_verify
    )

    if not merge_result:
        result["error"] = "图片合并失败"
        result["steps"]["merge"] = {"success": False}
        return result

    # 计算网格信息
    rows = (len(image_urls) + grid_columns - 1) // grid_columns
    grid_info = {
        "total_images": len(image_urls),
        "rows": rows,
        "columns": grid_columns,
        "merged_path": str(merged_path)
    }

    result["steps"]["merge"] = {
        "success": True,
        "path": str(merged_path),
        "grid_info": grid_info
    }

    print(f"  ✓ 合并完成: {merged_path}")
    print(f"  ✓ 网格: {rows}行 x {grid_columns}列")

    # ========== Step 3: 分析基准产品 (如果未提供) ==========
    if reference_analysis is None:
        print("\n[3/5] 分析基准产品...")
        reference_analysis = analyze_reference_product(product_image, debug)

        result["steps"]["reference_analysis"] = reference_analysis

        if reference_analysis.get("analyzed"):
            print("  ✓ 特征提取完成")
        else:
            print("  ⚠ 需要通过 MCP 完成分析")
            print(f"\n{'='*60}")
            print("MCP 调用提示:")
            print(f"{'='*60}")
            print(reference_analysis.get("mcp_prompt", ""))
    else:
        print("\n[3/5] 使用预先分析的基准产品特征")
        result["steps"]["reference_analysis"] = {
            "reused": True,
            "features": reference_analysis
        }

    # ========== Step 4: 分析合并图片 ==========
    print("\n[4/5] 分析合并图片...")
    similarity_analysis = analyze_merged_grid(
        merged_image_path=str(merged_path),
        reference_features=reference_analysis,
        grid_info=grid_info,
        debug=debug
    )

    result["steps"]["similarity_analysis"] = similarity_analysis

    if similarity_analysis.get("analyzed"):
        print("  ✓ 相似度分析完成")
    else:
        print("  ⚠ 需要通过 MCP 完成分析")
        print(f"\n{'='*60}")
        print("MCP 调用提示:")
        print(f"{'='*60}")
        print(similarity_analysis.get("mcp_prompt", ""))

    # ========== Step 5: 加权评分并汇总 ==========
    print("\n[5/5] 汇总结果...")

    # 这里假设 MCP 已经返回了分析结果
    # 实际使用时，需要等待 MCP 调用完成后再计算
    if similarity_analysis.get("analyzed"):
        similar_products = similarity_analysis.get("similar_products", [])
        match_count = len([p for p in similar_products if p["similarity_score"] >= similarity_threshold])
        avg_similarity = similarity_analysis.get("avg_similarity", 0)

        result["summary"] = {
            "total_products": len(image_urls),
            "match_count": match_count,
            "avg_similarity": round(avg_similarity, 4),
            "max_similarity": round(max([p["similarity_score"] for p in similar_products], default=0), 4),
            "is_qualified": match_count >= 2,  # 可配置
            "threshold": similarity_threshold
        }

        print(f"  ✓ 总商品数: {len(image_urls)}")
        print(f"  ✓ 匹配数量: {match_count}")
        print(f"  ✓ 平均相似度: {avg_similarity:.2%}")
        print(f"  ✓ 是否合格: {'是' if result['summary']['is_qualified'] else '否'}")
    else:
        result["summary"] = {
            "pending_mcp": True,
            "message": "等待 MCP 分析完成"
        }
        print("  ⚠ 等待 MCP 分析完成后计算")

    # 保存完整结果
    result_path = keyword_dir / "analysis_result.json"
    with open(result_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n  ✓ 结果已保存: {result_path}")

    return result


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='基于 MCP 视觉 AI 的关键词分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 分析单个关键词
  python analyze_keyword_with_ai.py "wireless earbuds" my_product.jpg

  # 指定输出目录
  python analyze_keyword_with_ai.py "wireless earbuds" my_product.jpg -o ./results

  # 调试模式
  python analyze_keyword_with_ai.py "test" product.jpg --debug --no-headless

  # 自定义参数
  python analyze_keyword_with_ai.py "earbuds" product.jpg --max-products 10 --columns 5
        """
    )

    parser.add_argument('keyword', help='搜索关键词')
    parser.add_argument('product_image', help='基准产品图片路径')
    parser.add_argument('--amazon-domain', default='amazon.com', help='亚马逊域名 (默认: amazon.com)')
    parser.add_argument('--max-products', type=int, default=20, help='最多获取多少个商品 (默认: 20)')
    parser.add_argument('--columns', type=int, default=5, help='网格列数 (默认: 5)')
    parser.add_argument('--threshold', type=float, default=0.85, help='相似度阈值 (默认: 0.85)')
    parser.add_argument('-o', '--output', default='./ai_analysis_results', help='输出目录')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    parser.add_argument('--no-headless', action='store_true', help='显示浏览器窗口')
    parser.add_argument('--no-ssl-verify', action='store_true', help='禁用 SSL 验证')

    args = parser.parse_args()

    # 检查产品图片是否存在
    if not Path(args.product_image).exists():
        print(f"[错误] 产品图片不存在: {args.product_image}")
        sys.exit(1)

    # 执行分析
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

    print(f"\n{'='*60}")
    print("分析完成")
    print(f"{'='*60}\n")

    if result.get("error"):
        print(f"[错误] {result['error']}")
        sys.exit(1)

    if result.get("summary", {}).get("pending_mcp"):
        print("⚠ 需要完成 MCP 调用才能获得最终结果")

        # 输出 MCP 请求块供 Claude 自动识别
        ref_step = result.get("steps", {}).get("reference_analysis", {})
        sim_step = result.get("steps", {}).get("similarity_analysis", {})

        print("\n" + "="*60)
        print(">>> CLAUDE: 请自动完成以下 MCP 调用 <<<")
        print("="*60)

        # 保存 MCP 请求到文件
        mcp_requests = []
        output_dir = Path(result.get("output_dir", "./ai_analysis_results"))
        result_file = output_dir / "analysis_result.json"

        # 基准产品分析请求
        if ref_step.get("mcp_prompt"):
            product_img = ref_step.get('image_path', args.product_image)
            mcp_requests.append({
                "step": 1,
                "image": product_img,
                "tool": "zai-mcp-server__analyze_image",
                "prompt": ref_step.get("mcp_prompt", "")
            })
            print(f"\n[步骤 1/2] 分析基准产品: {product_img}")
            print(f">>> 请调用: mcp__zai-mcp-server__analyze_image({product_img}, prompt)")

        # 合并图片分析请求
        if sim_step.get("mcp_prompt"):
            merged_img = sim_step.get("merged_image", "")
            grid_info = result.get("steps", {}).get("merge", {}).get("grid_info", {})
            mcp_requests.append({
                "step": 2,
                "image": merged_img,
                "tool": "zai-mcp-server__analyze_image",
                "grid_info": grid_info,
                "reference_features": ref_step
            })
            print(f"[步骤 2/2] 分析合并图片: {merged_img}")
            print(f">>> 请调用: mcp__zai-mcp-server__analyze_image({merged_img}, grid_prompt)")

        # 保存 MCP 请求到 JSON
        mcp_request_file = output_dir / "mcp_requests.json"
        with open(mcp_request_file, 'w', encoding='utf-8') as f:
            json.dump({
                "keyword": args.keyword,
                "product_image": args.product_image,
                "requests": mcp_requests,
                "result_file": str(result_file)
            }, f, ensure_ascii=False, indent=2)

        print(f"\n✓ MCP 请求已保存: {mcp_request_file}")
        print(f"✓ 结果将保存到: {result_file}")
        print("\n" + "="*60 + "\n")
    else:
        summary = result.get("summary", {})
        print(f"关键词: {result['keyword']}")
        print(f"匹配数量: {summary.get('match_count', 0)}/{summary.get('total_products', 0)}")
        print(f"平均相似度: {summary.get('avg_similarity', 0):.2%}")
        print(f"是否合格: {'✓ 是' if summary.get('is_qualified') else '✗ 否'}")


if __name__ == "__main__":
    main()
