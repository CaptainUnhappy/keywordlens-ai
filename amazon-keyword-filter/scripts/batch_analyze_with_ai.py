#!/usr/bin/env python3
"""
批量关键词 AI 分析脚本

流程：
1. 分析基准产品（第一步）
2. AI 过滤关键词（可选，默认开启）
3. 批量搜索亚马逊（浏览器复用）
4. 准备 MCP 请求（并发）
5. 并发 MCP 分析
"""

import sys
import json
import argparse
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Set
import pandas as pd

# 导入单个关键词分析
from analyze_keyword_with_ai import analyze_reference_product
from search_amazon import AmazonSearcher


def load_keywords_from_excel(excel_file: str, keyword_column: str = "关键词") -> List[str]:
    """从 Excel 加载关键词列表"""
    df = pd.read_excel(excel_file)

    if keyword_column not in df.columns:
        raise ValueError(f"未找到列: {keyword_column}\n可用列: {list(df.columns)}")

    keywords = df[keyword_column].dropna().unique().tolist()
    return keywords


def save_filtered_keywords(keywords: List[str], output_file: str):
    """保存过滤后的关键词到文本文件"""
    with open(output_file, 'w', encoding='utf-8') as f:
        for kw in keywords:
            f.write(f"{kw}\n")


# ==================== 并发安全的进度管理 ====================

class ProgressTracker:
    """并发安全的进度跟踪器"""

    def __init__(self, cache_file: str):
        self.cache_file = Path(cache_file)
        self.lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> Dict:
        """加载进度数据"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "completed_folders": [],      # 已完成的文件夹列表
            "current_folder": None,       # 当前处理的文件夹
            "failed_keywords": [],        # 失败的关键词列表
            "mcp_completed": [],          # MCP 分析完成的文件夹
            "mcp_pending": [],            # MCP 分析待处理的文件夹
            "status": "in_progress"       # 总体状态
        }

    def save(self):
        """保存进度数据（线程安全）"""
        with self.lock:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)

    def add_completed(self, folder_name: str):
        """添加已完成的文件夹"""
        with self.lock:
            if folder_name not in self._data["completed_folders"]:
                self._data["completed_folders"].append(folder_name)
            self._data["current_folder"] = folder_name

    def add_mcp_pending(self, folder_name: str):
        """添加到 MCP 待处理列表"""
        with self.lock:
            if folder_name not in self._data["mcp_pending"]:
                self._data["mcp_pending"].append(folder_name)

    def add_mcp_completed(self, folder_name: str):
        """添加到 MCP 已完成列表"""
        with self.lock:
            if folder_name in self._data["mcp_pending"]:
                self._data["mcp_pending"].remove(folder_name)
            if folder_name not in self._data["mcp_completed"]:
                self._data["mcp_completed"].append(folder_name)

    def add_failed(self, keyword: str, error: str):
        """添加失败的关键词"""
        with self.lock:
            self._data["failed_keywords"].append({"keyword": keyword, "error": error})

    def get_completed_folders(self) -> Set[str]:
        """获取已完成的文件夹集合"""
        with self.lock:
            return set(self._data.get("completed_folders", []))

    def get_mcp_pending(self) -> List[str]:
        """获取 MCP 待处理列表"""
        with self.lock:
            return self._data.get("mcp_pending", []).copy()

    def set_status(self, status: str):
        """设置总体状态"""
        with self.lock:
            self._data["status"] = status

    def get_summary(self) -> Dict:
        """获取进度摘要"""
        with self.lock:
            return self._data.copy()


# ==================== AI 过滤关键词 ====================

def filter_keywords_with_ai(
    keywords: List[str],
    reference_analysis: Dict,
    product_image: str,
    output_path: Path,
    debug: bool = False
) -> List[str]:
    """
    使用 AI 过滤关键词

    基于基准产品分析结果，使用 AI 判断哪些关键词与产品相关

    Args:
        keywords: 原始关键词列表
        reference_analysis: 基准产品分析结果
        product_image: 基准产品图片路径
        output_path: 输出目录
        debug: 调试模式

    Returns:
        过滤后的关键词列表
    """
    print(f"\n{'='*60}")
    print(f"阶段 1/4: AI 过滤关键词")
    print(f"{'='*60}")
    print(f"原始关键词数: {len(keywords)}")
    print(f"{'='*60}\n")

    # 生成 AI 过滤请求
    filter_request_file = output_path / "keyword_filter_request.json"

    # 提取产品特征
    features = reference_analysis.get("features", {})
    feature_text = f"""
颜色: {features.get('color', '未知')}
风格: {features.get('style', '未知')}
材质: {features.get('material', '未知')}
形状: {features.get('shape', '未知')}
用途: {features.get('usage', '未知')}
关键词: {features.get('keywords', [])}
"""

    # 创建过滤请求
    filter_request = {
        "product_image": product_image,
        "product_features": features,
        "original_keywords": keywords,
        "total_keywords": len(keywords),
        "instruction": f"""请分析这些关键词，判断哪些与基准产品相关。

基准产品特征：
{feature_text}

请从以下关键词中筛选出与基准产品相关的关键词：
{json.dumps(keywords, ensure_ascii=False, indent=2)}

返回 JSON 格式：
{{
  "relevant_keywords": ["关键词1", "关键词2", ...],
  "irrelevant_keywords": ["关键词3", "关键词4", ...],
  "reasons": {{
    "关键词1": "相关原因",
    "关键词2": "相关原因"
  }}
}}

筛选标准：
1. 产品的核心功能或用途
2. 相同或相似的颜色/风格
3. 相同的目标用户群体
4. 产品类型或类别相关
""",
        "output_file": str(output_path / "filtered_keywords.json")
    }

    # 保存过滤请求
    with open(filter_request_file, 'w', encoding='utf-8') as f:
        json.dump(filter_request, f, ensure_ascii=False, indent=2)

    print("\n📋 AI 关键词过滤请求已生成")
    print(f"请求文件: {filter_request_file}")
    print(f"\n{'='*60}")
    print("请使用以下提示进行 AI 过滤:")
    print(f"{'='*60}")
    print(f"\n请分析 {filter_request_file} 中的关键词，")
    print("判断哪些与基准产品相关，并将结果保存到:")
    print(f"  {output_path / 'filtered_keywords.json'}")
    print(f"\n{'='*60}\n")

    # 检查是否已有过滤结果
    filtered_file = output_path / "filtered_keywords.json"
    if filtered_file.exists():
        try:
            with open(filtered_file, 'r', encoding='utf-8') as f:
                filtered_data = json.load(f)
                filtered_keywords = filtered_data.get("relevant_keywords", [])

                if filtered_keywords:
                    print(f"✓ 已加载过滤结果: {len(filtered_keywords)}/{len(keywords)} 个相关关键词")
                    print(f"  过滤率: {100 * (1 - len(filtered_keywords)/len(keywords)):.1f}%")

                    # 保存到文本文件
                    txt_file = output_path / "filtered_keywords.txt"
                    save_filtered_keywords(filtered_keywords, str(txt_file))
                    print(f"✓ 已保存到: {txt_file}")

                    return filtered_keywords
        except Exception as e:
            print(f"⚠ 读取过滤结果失败: {e}")

    return []


def prepare_mcp_requests(
    keywords: List[str],
    search_results_cache: Dict,
    product_image: str,
    reference_analysis: Dict,
    output_path: Path,
    grid_columns: int,
    progress: ProgressTracker,
    no_ssl_verify: bool = False,
    debug: bool = False,
    max_workers: int = 5
) -> List[Dict]:
    """
    为所有关键词准备 MCP 请求（并发处理）

    这个函数会：
    1. 并发下载并合并所有关键词的图片
    2. 为每个关键词生成 MCP 请求文件
    3. 返回所有待处理的 MCP 任务列表
    """
    from merge_images import merge_images_grid
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import time

    mcp_tasks = []

    print(f"\n{'='*60}")
    print(f"阶段 3/4: 准备 MCP 请求（并发处理，{max_workers}线程）")
    print(f"{'='*60}\n")

    def process_keyword(keyword_info):
        """并发处理单个关键词"""
        idx, keyword = keyword_info
        safe_keyword = keyword.replace(" ", "_").replace("/", "_")[:50]

        # 检查是否已有结果
        existing_folders = list(output_path.glob(f"*_{safe_keyword}"))
        if existing_folders:
            keyword_dir = sorted(existing_folders, reverse=True)[0]
            result_file = keyword_dir / "analysis_result.json"
            if result_file.exists():
                return {
                    "status": "skipped",
                    "keyword": keyword,
                    "message": "已有分析结果"
                }

        # 获取搜索结果
        if keyword not in search_results_cache or search_results_cache[keyword]["count"] == 0:
            return {
                "status": "skipped",
                "keyword": keyword,
                "message": "无搜索结果"
            }

        image_urls = search_results_cache[keyword]["image_urls"]

        # 创建文件夹（关键词在前，使用微秒级时间戳避免冲突）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        keyword_dir = output_path / f"{safe_keyword}_{timestamp}"
        keyword_dir.mkdir(exist_ok=True)

        # 合并图片
        merged_path = keyword_dir / "merged_grid.jpg"
        try:
            merge_images_grid(
                image_urls=image_urls,
                output_path=str(merged_path),
                columns=grid_columns,
                img_size=(200, 200),
                debug=debug,
                no_ssl_verify=no_ssl_verify
            )
        except Exception as e:
            progress.add_failed(keyword, f"合并图片失败: {e}")
            progress.save()
            return {
                "status": "failed",
                "keyword": keyword,
                "error": str(e)
            }

        # 保存搜索结果
        json_path = keyword_dir / "search_result.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({"keyword": keyword, "image_urls": image_urls, "count": len(image_urls)},
                      f, ensure_ascii=False, indent=2)

        # 更新进度
        progress.add_completed(keyword_dir.name)
        progress.save()

        return {
            "status": "success",
            "keyword": keyword,
            "merged_image": str(merged_path),
            "keyword_dir": keyword_dir,
            "image_count": len(image_urls)
        }

    # 使用线程池并发处理关键词
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        futures = {executor.submit(process_keyword, (i+1, kw)): i+1
                   for i, kw in enumerate(keywords)}

        # 收集结果
        completed = 0
        for future in as_completed(futures):
            idx = futures[future]
            result = future.result()
            completed += 1

            if result["status"] == "success":
                mcp_tasks.append({
                    "keyword": result["keyword"],
                    "merged_image": result["merged_image"],
                    "keyword_dir": result["keyword_dir"]
                })
                print(f"[{completed}/{len(keywords)}] ✓ {result['keyword']} ({result['image_count']}张)")
            elif result["status"] == "skipped":
                print(f"[{completed}/{len(keywords)}] ⏭ {result['keyword']}: {result['message']}")
            elif result["status"] == "failed":
                print(f"[{completed}/{len(keywords)}] ✗ {result['keyword']}: {result['error']}")

    print(f"\n✓ 并发处理完成: 成功 {len(mcp_tasks)} 个")

    return mcp_tasks


def generate_concurrent_mcp_prompts(
    mcp_tasks: List[Dict],
    product_image: str,
    reference_analysis: Dict,
    output_path: Path,
    progress: ProgressTracker
) -> str:
    """
    生成并发 MCP 调用的提示信息

    返回一个包含所有 MCP 请求的提示字符串
    """
    print(f"\n{'='*60}")
    print(f"阶段 4/4: 并发 MCP 分析提示")
    print(f"{'='*60}\n")

    # 生成批量 MCP 请求文件
    batch_mcp_file = output_path / "batch_mcp_requests.json"
    batch_requests = []

    for task in mcp_tasks:
        keyword = task["keyword"]
        merged_image = task["merged_image"]
        keyword_dir = task["keyword_dir"]

        # 为每个任务生成详细的 MCP 请求
        mcp_request = {
            "step": 2,
            "keyword": keyword,
            "image": str(merged_image),
            "tool": "zai-mcp-server__analyze_image",
            "prompt": f"""分析合并图中所有产品与参考产品的相似度。

参考产品特征：
颜色: {reference_analysis.get('features', {}).get('color', '未知')}
风格: {reference_analysis.get('features', {}).get('style', '未知')}
材质: {reference_analysis.get('features', {}).get('material', '未知')}
形状: {reference_analysis.get('features', {}).get('shape', '未知')}

请返回 JSON 格式：
{{
  "keyword": "{keyword}",
  "products": [
    {{"position": "1-1", "similarity": 0.9, "reason": "...", "recommended": true}},
    ...
  ]
}}""",
            "result_file": str(keyword_dir / "analysis_result.json")
        }

        batch_requests.append(mcp_request)
        progress.add_mcp_pending(keyword_dir.name)

    # 保存批量请求文件
    with open(batch_mcp_file, 'w', encoding='utf-8') as f:
        json.dump({
            "product_image": product_image,
            "reference_analysis": reference_analysis,
            "total_requests": len(batch_requests),
            "requests": batch_requests,
            "timestamp": datetime.now().isoformat()
        }, f, ensure_ascii=False, indent=2)

    progress.save()

    # 生成提示信息
    prompt = f"""
{'='*60}
批量 MCP 并发分析请求
{'='*60}

总计 {len(batch_requests)} 个关键词需要 MCP 分析

方式 1 - 批量并发调用（推荐）:
  将以下内容复制给 Claude，一次性处理所有请求：

  "请对 {output_path / 'batch_mcp_requests.json'} 中的 {len(batch_requests)} 个关键词进行并发 MCP 分析"

方式 2 - 逐个调用:
  查看各关键词文件夹中的 mcp_request.json

{'='*60}
"""

    print(prompt)
    return str(batch_mcp_file)


# ==================== 主批处理函数 ====================

def _load_reference_analysis(output_path: Path, product_image: str, debug: bool) -> Optional[Dict]:
    """加载或创建基准产品分析"""
    ref_path = output_path / "reference_analysis.json"

    if ref_path.exists():
        with open(ref_path, 'r', encoding='utf-8') as f:
            saved_ref = json.load(f)
            if saved_ref.get("analyzed"):
                print("✓ 已加载保存的基准产品分析结果")
                return saved_ref

    # 创建新的分析
    reference_analysis = analyze_reference_product(product_image, debug)

    if not reference_analysis.get("analyzed"):
        print("\n⚠ 需要先通过 MCP 分析基准产品")
        print(f"\n{'='*60}")
        print("MCP 调用提示 (基准产品分析):")
        print(f"{'='*60}")
        print(reference_analysis.get("mcp_prompt", ""))
        print(f"\n{'='*60}")
        print("\n请完成以下步骤:")
        print("1. 使用上述提示调用 MCP: zai-mcp-server__analyze_image")
        print(f"2. 将 MCP 返回的 JSON 保存到: {ref_path}")
        print("3. 重新运行此脚本\n")

        if not ref_path.exists():
            with open(ref_path, 'w', encoding='utf-8') as f:
                json.dump(reference_analysis, f, ensure_ascii=False, indent=2)

        return None

    return reference_analysis


def _filter_keywords_stage(
    keywords: List[str],
    reference_analysis: Dict,
    product_image: str,
    output_path: Path,
    enable_filter: bool,
    debug: bool
) -> List[str]:
    """阶段1：AI过滤关键词"""
    if not enable_filter:
        print("\n⏭ AI 过滤已禁用，使用所有关键词")
        return keywords

    filtered_keywords = filter_keywords_with_ai(
        keywords=keywords,
        reference_analysis=reference_analysis,
        product_image=product_image,
        output_path=output_path,
        debug=debug
    )

    if not filtered_keywords:
        print("\n⚠ 未找到过滤结果，使用原始关键词")
        return keywords

    print(f"\n✓ AI 过滤完成: {len(filtered_keywords)}/{len(keywords)} 个关键词")

    if not filtered_keywords:
        print("\n✗ 没有相关关键词，停止处理")
        return []

    return filtered_keywords


def _batch_search_stage(
    keywords: List[str],
    progress: ProgressTracker,
    output_path: Path,
    amazon_domain: str,
    max_products: int,
    headless: bool,
    debug: bool
) -> Dict[str, Dict]:
    """阶段2：批量搜索Amazon"""
    search_results_cache = {}

    print(f"\n{'='*60}")
    print(f"阶段 2/4: 批量搜索 (浏览器复用)")
    print(f"{'='*60}\n")

    completed_folders = progress.get_completed_folders()

    with AmazonSearcher(amazon_domain=amazon_domain, headless=headless, debug=debug) as searcher:
        for i, keyword in enumerate(keywords, 1):
            # 检查缓存
            safe_keyword = keyword.replace(" ", "_").replace("/", "_")[:50]
            existing_folders = list(output_path.glob(f"*_{safe_keyword}"))

            if existing_folders:
                keyword_dir = sorted(existing_folders, reverse=True)[0]
                result_file = keyword_dir / "analysis_result.json"
                if result_file.exists() and str(keyword_dir.name) in completed_folders:
                    print(f"[{i}/{len(keywords)}] ✓ 缓存: {keyword}")
                    _load_cached_search_result(keyword, keyword_dir, search_results_cache)
                    continue

            # 搜索关键词
            _search_single_keyword(
                keyword, i, len(keywords), searcher, max_products,
                search_results_cache, progress
            )

            # 定期休息
            if i % 10 == 0 and i < len(keywords):
                print(f"\n  休息 2 秒...\n")
                import time
                time.sleep(2)

    return search_results_cache


def _load_cached_search_result(keyword: str, keyword_dir: Path, cache: Dict):
    """加载缓存的搜索结果"""
    search_file = keyword_dir / "search_result.json"
    if search_file.exists():
        try:
            with open(search_file, 'r', encoding='utf-8') as f:
                search_data = json.load(f)
                cache[keyword] = {
                    "count": search_data.get("count", 0),
                    "image_urls": search_data.get("image_urls", [])
                }
        except Exception as e:
            print(f"  ⚠ 加载缓存失败: {e}")


def _search_single_keyword(
    keyword: str, index: int, total: int,
    searcher, max_products: int,
    cache: Dict, progress: ProgressTracker
):
    """搜索单个关键词"""
    print(f"[{index}/{total}] 🔍 搜索: {keyword}")
    try:
        search_result = searcher.search(keyword, max_products=max_products)
        cache[keyword] = search_result

        if search_result["count"] == 0:
            print(f"  ⚠ 未找到商品")
            progress.add_failed(keyword, "未找到商品")
        else:
            print(f"  ✓ 找到 {search_result['count']} 个商品")
        progress.save()
    except Exception as e:
        print(f"  ✗ 搜索失败: {e}")
        progress.add_failed(keyword, str(e))
        progress.save()


def _save_batch_summary(
    output_path: Path,
    keywords: List[str],
    enable_filter: bool,
    search_results_cache: Dict,
    mcp_tasks: List,
    progress: ProgressTracker
):
    """保存批处理汇总"""
    summary_path = output_path / "batch_summary.json"
    summary_data = progress.get_summary()
    summary_data.update({
        "total_keywords": len(keywords),
        "filtered": enable_filter,
        "searched": len(search_results_cache),
        "prepared_mcp": len(mcp_tasks),
        "timestamp": datetime.now().isoformat()
    })

    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"批量处理完成")
    print(f"{'='*60}")
    print(f"原始关键词数: {summary_data.get('total_keywords', 0)}")
    if enable_filter:
        print(f"AI 过滤: 启用")
    print(f"成功搜索: {len(search_results_cache)}")
    print(f"准备 MCP: {len(mcp_tasks)}")
    print(f"失败: {len(summary_data.get('failed_keywords', []))}")
    print(f"汇总已保存: {summary_path}")
    print(f"{'='*60}\n")

    if summary_data.get("failed_keywords"):
        print("失败的关键词:")
        for item in summary_data["failed_keywords"]:
            print(f"  - {item['keyword']}: {item['error']}")


def batch_analyze(
    keywords: List[str],
    product_image: str,
    amazon_domain: str = "amazon.com",
    max_products: int = 20,
    grid_columns: int = 5,
    similarity_threshold: float = 0.85,
    output_dir: str = "./ai_batch_results",
    cache_file: Optional[str] = None,
    debug: bool = False,
    headless: bool = True,
    no_ssl_verify: bool = False,
    concurrent_workers: int = 5,
    enable_filter: bool = True
) -> List[Dict]:
    """
    高效批量分析 - 完整流程

    四阶段处理：
    1. 分析基准产品（第一步）
    2. AI 过滤关键词（可选）
    3. 批量搜索（浏览器复用）
    4. 准备 MCP 请求（并发下载合并）
    5. 并发 MCP 分析

    Args:
        keywords: 关键词列表
        product_image: 基准产品图片
        enable_filter: 是否启用 AI 过滤（默认 True）

    Returns:
        list: 所有分析结果
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    cache_file = cache_file or str(output_path / "batch_progress.json")
    progress = ProgressTracker(cache_file)

    print(f"\n{'='*60}")
    print(f"高效批量 AI 分析 (完整流程)")
    print(f"{'='*60}")
    print(f"总关键词数: {len(keywords)}")
    print(f"AI 过滤: {'启用' if enable_filter else '禁用'}")
    print(f"并发数: {concurrent_workers}")
    print(f"{'='*60}\n")

    # 阶段 0: 分析基准产品
    print("=" * 60)
    print("阶段 0/4: 分析基准产品")
    print("=" * 60)

    reference_analysis = _load_reference_analysis(output_path, product_image, debug)
    if not reference_analysis:
        return []

    # 阶段 1: AI 过滤关键词
    keywords = _filter_keywords_stage(
        keywords, reference_analysis, product_image,
        output_path, enable_filter, debug
    )
    if not keywords:
        return []

    # 阶段 2: 批量搜索
    search_results_cache = _batch_search_stage(
        keywords, progress, output_path, amazon_domain,
        max_products, headless, debug
    )

    # 阶段 3: 准备 MCP 请求
    mcp_tasks = prepare_mcp_requests(
        keywords=keywords,
        search_results_cache=search_results_cache,
        product_image=product_image,
        reference_analysis=reference_analysis,
        output_path=output_path,
        grid_columns=grid_columns,
        progress=progress,
        no_ssl_verify=no_ssl_verify,
        debug=debug,
        max_workers=concurrent_workers
    )

    # 阶段 4: 生成并发 MCP 提示
    if mcp_tasks:
        batch_mcp_file = generate_concurrent_mcp_prompts(
            mcp_tasks=mcp_tasks,
            product_image=product_image,
            reference_analysis=reference_analysis,
            output_path=output_path,
            progress=progress
        )
        progress.set_status("等待MCP分析")
        progress.save()
    else:
        print("\n所有关键词已有分析结果或无需处理")

    # 保存汇总
    _save_batch_summary(output_path, keywords, enable_filter, search_results_cache, mcp_tasks, progress)

    print("\n下一步:")
    print("查看 batch_mcp_requests.json，并发调用 MCP 完成分析\n")

    return []


# ==================== 命令行入口 ====================

def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description='批量关键词 AI 分析 (完整流程)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法（启用 AI 过滤）
  python batch_analyze_with_ai.py keywords.xlsx product.jpg

  # 禁用 AI 过滤，使用所有关键词
  python batch_analyze_with_ai.py keywords.xlsx product.jpg --no-filter

  # 指定关键词列名
  python batch_analyze_with_ai.py keywords.xlsx product.jpg --column "Search Term"

  # 自定义输出目录
  python batch_analyze_with_ai.py keywords.xlsx product.jpg -o ./my_results

  # 调试模式
  python batch_analyze_with_ai.py keywords.xlsx product.jpg --debug
        """
    )

    parser.add_argument('excel_file', help='Excel 文件路径')
    parser.add_argument('product_image', help='基准产品图片路径')
    parser.add_argument('--column', default='关键词', help='关键词列名 (默认: 关键词)')
    parser.add_argument('--amazon-domain', default='amazon.com', help='亚马逊域名')
    parser.add_argument('--max-products', type=int, default=20, help='每个关键词最多获取多少商品')
    parser.add_argument('--columns', type=int, default=5, help='网格列数')
    parser.add_argument('--threshold', type=float, default=0.85, help='相似度阈值')
    parser.add_argument('-o', '--output', default='./ai_batch_results', help='输出目录')
    parser.add_argument('--cache', help='进度缓存文件路径')
    parser.add_argument('--workers', type=int, default=5, help='并发工作线程数 (默认: 5)')
    parser.add_argument('--no-filter', action='store_true', help='禁用 AI 关键词过滤（使用所有关键词）')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    parser.add_argument('--no-headless', action='store_true', help='显示浏览器窗口')
    parser.add_argument('--no-ssl-verify', action='store_true', help='禁用 SSL 验证')

    args = parser.parse_args()

    # 检查文件是否存在
    if not Path(args.excel_file).exists():
        print(f"[错误] Excel 文件不存在: {args.excel_file}")
        sys.exit(1)

    if not Path(args.product_image).exists():
        print(f"[错误] 产品图片不存在: {args.product_image}")
        sys.exit(1)

    # 加载关键词
    try:
        keywords = load_keywords_from_excel(args.excel_file, args.column)
        print(f"✓ 从 Excel 加载了 {len(keywords)} 个关键词")
    except Exception as e:
        print(f"[错误] 加载 Excel 失败: {e}")
        sys.exit(1)

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

    if not results:
        print("\n[提示] 请完成 MCP 分析后重新运行以查看结果")
        sys.exit(0)


if __name__ == "__main__":
    main()
