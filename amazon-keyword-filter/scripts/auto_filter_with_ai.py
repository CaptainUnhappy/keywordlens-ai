#!/usr/bin/env python3
"""
自动化关键词过滤流程：
1. 使用 MCP AI 分析产品图片生成描述
2. 使用智谱 AI Embedding 过滤关键词

需要在 Claude Code 环境中运行以访问 MCP 工具

使用方法:
    python auto_filter_with_ai.py <product_image.jpg> <keywords.xlsx> [--threshold 0.6]
"""

import json
import sys
import os
import argparse
import requests
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd
from pathlib import Path


# ==================== MCP 分析提示词 ====================

MCP_ANALYSIS_PROMPT = """Analyze this product image and provide a comprehensive description optimized for semantic keyword matching.

Include:
1. Product category (e.g., headband, earbuds, backpack)
2. Visual features (colors, materials, textures, shape)
3. Purpose/use case (occasions, target audience)
4. Style/theme (e.g., festive, minimalist, holiday-specific)
5. Key distinguishing features
6. Related search terms (both generic and specific)

Provide a detailed, flowing description using varied vocabulary that covers different ways people might search for this product. Focus on objective, observable features.
"""


# ==================== 配置 ====================

# 智谱AI API配置
ZHIPU_API_KEY = "REDACTED_ZHIPU_KEY"
ZHIPU_API_URL = "https://open.bigmodel.cn/api/paas/v4/embeddings"
EMBEDDING_DIMENSIONS = 1024


# ==================== 步骤 1: MCP 图片分析 ====================


def analyze_product_with_mcp(image_path: str) -> str:
    """
    使用 MCP AI 分析产品图片

    这个函数在 Claude Code 环境中会调用真实的 MCP 工具
    在普通 Python 环境中会返回 None，需要手动提供描述

    Args:
        image_path: 产品图片路径

    Returns:
        AI 生成的产品描述（在 Claude Code 环境中）
        None（在普通 Python 环境中）
    """
    print(f"\n🤖 步骤 1/3: 使用 MCP AI 分析产品图片...")
    print(f"   图片: {image_path}")

    # 在 Claude Code 环境中，这里会被自动替换为真实的 MCP 调用
    # 用户需要确保在 Claude Code 中运行此脚本

    # 提示用户
    print(f"\n⚠️  此脚本需要在 Claude Code 环境中运行")
    print(f"   请将以下内容发送给 Claude Code:\n")
    print(f"   '使用 mcp__zai-mcp-server__analyze_image 分析 {image_path}'")
    print(f"   '使用提示词: {MCP_ANALYSIS_PROMPT[:100]}...'")

    return None


def load_product_description_from_json(json_file: str = "product_description.json") -> str:
    """从 JSON 文件加载产品描述"""
    if not os.path.exists(json_file):
        return None

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data.get('description', '')


def create_product_description_interactive(image_path: str) -> str:
    """交互式创建产品描述（备用方案）"""
    print(f"\n📝 请提供产品描述（用于语义匹配）:")
    print(f"   参考图片: {image_path}\n")

    description_parts = []

    # 基本信息
    category = input("1. 产品类别 (e.g., headband, shoes, earbuds): ").strip()
    if category:
        description_parts.append(f"This is a {category}")

    # 颜色
    colors = input("2. 主要颜色 (e.g., green, blue, black): ").strip()
    if colors:
        description_parts.append(f"featuring {colors} color")

    # 主题/风格
    theme = input("3. 主题/风格 (e.g., St. Patrick's Day, minimalist, sports): ").strip()
    if theme:
        description_parts.append(f"with {theme} theme")

    # 用途
    occasion = input("4. 使用场合 (e.g., party, daily use, sports): ").strip()
    if occasion:
        description_parts.append(f"suitable for {occasion}")

    # 关键特征
    features = input("5. 关键特征 (e.g., shamrock, wireless, waterproof): ").strip()
    if features:
        description_parts.append(f"Key features: {features}")

    description = ". ".join(description_parts) + "."

    print(f"\n✓ 生成的描述:\n{description}\n")

    return description


# ==================== 步骤 2: 关键词加载 ====================


def load_keywords_from_excel(file_path: str, column_name: str = "关键词") -> list:
    """从 Excel 文件加载关键词"""
    print(f"\n📂 步骤 2/3: 加载关键词...")
    print(f"   文件: {file_path}")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"找不到 Excel 文件: {file_path}")

    df = pd.read_excel(file_path)

    if column_name not in df.columns:
        raise ValueError(
            f"Excel 中没有列 '{column_name}'，可用列: {list(df.columns)}"
        )

    keywords = df[column_name].dropna().str.strip().tolist()
    keywords = [kw for kw in keywords if kw]

    print(f"   ✓ 加载了 {len(keywords)} 个关键词")

    return keywords


# ==================== 步骤 3: 智谱 AI 语义过滤 ====================


def get_embedding(texts: list) -> np.ndarray:
    """调用智谱 AI API 获取文本向量（自动分批）"""
    headers = {
        "Authorization": f"Bearer {ZHIPU_API_KEY}",
        "Content-Type": "application/json",
    }

    BATCH_SIZE = 64
    all_embeddings = []
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(texts), BATCH_SIZE):
        batch_num = i // BATCH_SIZE + 1
        batch_texts = texts[i : i + BATCH_SIZE]

        print(
            f"   📡 调用智谱 API (批次 {batch_num}/{total_batches}, 数量: {len(batch_texts)})"
        )

        data = {
            "model": "embedding-3",
            "input": batch_texts,
            "dimensions": EMBEDDING_DIMENSIONS,
        }

        response = requests.post(ZHIPU_API_URL, headers=headers, json=data)

        if response.status_code != 200:
            raise Exception(f"API 调用失败: {response.status_code}\n{response.text}")

        result = response.json()
        embeddings = [item["embedding"] for item in result["data"]]
        all_embeddings.extend(embeddings)

        usage = result.get("usage", {})
        print(f"      ✓ 消耗 tokens: {usage.get('total_tokens', 'N/A')}")

    return np.array(all_embeddings)


def filter_keywords_with_zhipu(
    keywords: list, product_description: str, threshold: float = 0.6
) -> dict:
    """使用智谱 AI Embedding 过滤关键词"""
    print(f"\n🔍 步骤 3/3: 使用智谱 AI 进行语义过滤...")
    print(f"   阈值: {threshold}")
    print(f"   向量维度: {EMBEDDING_DIMENSIONS}")

    # 获取产品描述向量
    print(f"\n   📝 产品描述预览:\n   {product_description[:200]}...\n")
    product_vec = get_embedding([product_description])[0]

    # 获取关键词向量
    print(f"\n   🔄 编码关键词...")
    keyword_vecs = get_embedding(keywords)

    # 计算相似度
    print(f"\n   📊 计算语义相似度...")
    similarities = cosine_similarity([product_vec], keyword_vecs)[0]

    # 排序
    keyword_scores = list(zip(keywords, similarities))
    keyword_scores.sort(key=lambda x: x[1], reverse=True)

    # 过滤
    filtered = [(kw, score) for kw, score in keyword_scores if score >= threshold]

    # 统计
    stats = {
        "total": len(keywords),
        "filtered": len(filtered),
        "removed": len(keywords) - len(filtered),
        "filter_rate": 1 - len(filtered) / len(keywords),
        "pass_rate": len(filtered) / len(keywords),
        "avg_score": float(np.mean(similarities)),
        "max_score": float(similarities.max()),
        "min_score": float(similarities.min()),
        "threshold": threshold,
    }

    return {
        "filtered_keywords": [kw for kw, _ in filtered],
        "all_scores": {kw: float(score) for kw, score in keyword_scores},
        "ranked_keywords": keyword_scores,
        "stats": stats,
    }


# ==================== 结果输出 ====================


def print_results(result: dict):
    """打印格式化结果"""
    stats = result["stats"]
    ranked = result["ranked_keywords"]

    print("\n" + "="*70)
    print("✅ 智谱 AI 语义过滤完成")
    print("="*70)

    # 统计信息
    print(f"\n📊 过滤结果:")
    print(f"   总关键词数:   {stats['total']}")
    print(f"   ✓ 通过筛选:   {stats['filtered']} ({stats['pass_rate']:.1%})")
    print(f"   ✗ 被过滤:     {stats['removed']} ({stats['filter_rate']:.1%})")
    print(f"   相似度范围:   {stats['min_score']:.3f} - {stats['max_score']:.3f}")
    print(f"   平均分数:     {stats['avg_score']:.3f}")

    # Top 10
    print(f"\n🏆 Top 10 相关关键词:")
    for i, (kw, score) in enumerate(ranked[:10], 1):
        status = "✓" if score >= stats["threshold"] else "✗"
        print(f"   {i:2d}. {status} {score:.4f}  {kw}")

    # 过滤关键词示例
    if stats['removed'] > 0:
        print(f"\n❌ 被过滤关键词示例 (前5个):")
        removed = [(kw, s) for kw, s in ranked if s < stats['threshold']]
        for i, (kw, score) in enumerate(removed[:5], 1):
            print(f"   {i}. ✗ {score:.4f}  {kw}")


def save_results(
    result: dict,
    excel_file: str,
    keyword_column: str = "关键词",
    output_file: str = None
):
    """保存结果到 Excel"""
    if output_file is None:
        name, ext = os.path.splitext(excel_file)
        output_file = f"{name}_filtered{ext}"

    df = pd.read_excel(excel_file)

    # 添加得分列
    all_scores = result["all_scores"]
    threshold = result["stats"]["threshold"]

    df["相似度得分"] = df[keyword_column].map(lambda x: all_scores.get(x, np.nan))
    df["状态"] = df["相似度得分"].apply(
        lambda x: "✓ 通过" if not pd.isna(x) and x >= threshold else "✗ 过滤"
    )

    # 排序（按得分降序）
    df = df.sort_values("相似度得分", ascending=False, na_position='last')

    # 保存
    df.to_excel(output_file, index=False)

    print(f"\n💾 结果已保存: {output_file}")

    # 同时保存 JSON
    json_file = output_file.replace(".xlsx", ".json").replace(".xls", ".json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"💾 JSON 已保存: {json_file}")


# ==================== 主函数 ====================


def main():
    parser = argparse.ArgumentParser(
        description="自动化关键词过滤：MCP图片分析 + 智谱AI语义过滤"
    )
    parser.add_argument("image", help="产品图片路径")
    parser.add_argument("keywords_excel", help="关键词 Excel 文件")
    parser.add_argument(
        "--threshold", type=float, default=0.6, help="相似度阈值 (默认 0.6)"
    )
    parser.add_argument(
        "--column", default="关键词", help="Excel 中的关键词列名 (默认 '关键词')"
    )
    parser.add_argument(
        "--description", help="直接提供产品描述（跳过 MCP 分析）"
    )
    parser.add_argument(
        "--description-file", help="从 JSON 文件加载产品描述"
    )

    args = parser.parse_args()

    print("\n" + "="*70)
    print("🚀 自动化关键词语义过滤流程")
    print("="*70)

    # 步骤 1: 获取产品描述
    product_description = None

    if args.description:
        # 直接使用命令行提供的描述
        product_description = args.description
        print(f"\n✓ 使用命令行提供的产品描述")

    elif args.description_file:
        # 从文件加载
        product_description = load_product_description_from_json(args.description_file)
        if product_description:
            print(f"\n✓ 从文件加载产品描述: {args.description_file}")

    if not product_description:
        # 尝试 MCP 分析（需要在 Claude Code 中运行）
        print(f"\n⚠️  自动分析模式需要在 Claude Code 环境中运行")
        print(f"   或使用 --description 参数直接提供描述\n")

        choice = input("是否手动输入产品描述? (y/n): ").strip().lower()
        if choice == 'y':
            product_description = create_product_description_interactive(args.image)
        else:
            print("\n❌ 未提供产品描述，退出")
            sys.exit(1)

    # 步骤 2: 加载关键词
    try:
        keywords = load_keywords_from_excel(args.keywords_excel, args.column)
    except Exception as e:
        print(f"\n❌ 加载关键词失败: {e}")
        sys.exit(1)

    # 步骤 3: 语义过滤
    try:
        result = filter_keywords_with_zhipu(
            keywords, product_description, args.threshold
        )

        # 打印结果
        print_results(result)

        # 保存结果
        save_results(result, args.keywords_excel, args.column)

        print("\n✅ 流程完成！")
        print(f"\n💡 下一步: 使用过滤后的关键词进行 Amazon 搜索")
        print(f"   通过的关键词数: {result['stats']['filtered']}")
        print(f"   预计节省搜索: {result['stats']['filter_rate']:.1%}")

    except Exception as e:
        print(f"\n❌ 过滤失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
