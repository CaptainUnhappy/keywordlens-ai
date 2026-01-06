#!/usr/bin/env python3
"""
图片合并脚本
将亚马逊搜索结果的多张图片合并为一张网格大图（5列）
用于一次性对比分析，减少多次调用MCP
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    from io import BytesIO
except ImportError:
    print("错误: 需要安装 Pillow 和 requests 库")
    print("请运行: pip install Pillow requests urllib3")
    sys.exit(1)


def create_session(retries=3, verify_ssl=True):
    """创建带重试机制的requests会话"""
    session = requests.Session()

    # 设置重试策略
    retry_strategy = Retry(
        total=retries,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # SSL验证设置
    if not verify_ssl:
        session.verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    return session


def download_image(url, session=None, timeout=10, verify_ssl=True):
    """下载单张图片，带重试机制"""
    if session is None:
        session = create_session(verify_ssl=verify_ssl)

    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return Image.open(BytesIO(response.content))
    except requests.exceptions.SSLError as e:
        # SSL错误，尝试禁用SSL验证
        if verify_ssl:
            if session is None:
                session = create_session(verify_ssl=False)
            else:
                session.verify = False
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            try:
                response = session.get(url, timeout=timeout)
                response.raise_for_status()
                return Image.open(BytesIO(response.content))
            except Exception as e2:
                print(f"[警告] SSL重试失败: {url[:50]}... - {e2}")
                return None
        else:
            print(f"[警告] SSL错误: {url[:50]}... - {e}")
            return None
    except Exception as e:
        print(f"[警告] 下载失败: {url[:50]}... - {e}")
        return None


def merge_images_grid(image_urls, output_path, columns=5, img_size=(200, 200),
                      debug=False, no_ssl_verify=False, border_size=2, max_workers=10):
    """
    将多张图片合并为网格大图

    Args:
        image_urls: 图片URL列表
        output_path: 输出文件路径
        columns: 列数（默认5列）
        img_size: 每张图片的尺寸
        add_numbers: 是否添加序号（已废弃，保留参数兼容性）
        debug: 调试模式
        no_ssl_verify: 是否禁用SSL验证
        border_size: 边框大小（像素）
        max_workers: 并发下载线程数（默认10）

    Returns:
        str: 输出文件路径，失败返回None
    """
    if not image_urls:
        print("[错误] 没有图片需要合并")
        return None

    print(f"[信息] 开始并发下载并合并 {len(image_urls)} 张图片（{max_workers}线程）...")

    # 创建会话（带重试机制）
    session = create_session(retries=3, verify_ssl=not no_ssl_verify)

    # 并发下载所有图片
    images = []
    failed_urls = []

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def download_and_process(idx_url):
        """下载并处理单张图片"""
        idx, url = idx_url
        if debug:
            print(f"[调试] 下载中 {idx}/{len(image_urls)}: {url[:60]}...")

        img = download_image(url, session=session, verify_ssl=not no_ssl_verify)
        if img:
            # 转换为RGB模式（处理RGBA等模式）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            # 调整大小
            img = img.resize(img_size, Image.Resampling.LANCZOS)
            return (idx, img, None)
        else:
            return (idx, None, url)

    # 使用线程池并发下载
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有下载任务
        futures = {executor.submit(download_and_process, (i+1, url)): i
                   for i, url in enumerate(image_urls)}

        # 收集结果
        for future in as_completed(futures):
            idx, img, failed_url = future.result()
            if img is not None:
                images.append((idx, img))
            else:
                failed_urls.append((idx, failed_url))

    if failed_urls:
        print(f"[警告] {len(failed_urls)} 张图片下载失败")
        if debug:
            for idx, url in failed_urls:
                print(f"  - #{idx}: {url[:60]}...")

    if not images:
        print("[错误] 没有成功下载任何图片")
        return None

    print(f"[信息] 成功下载 {len(images)}/{len(image_urls)} 张图片")

    # 计算网格尺寸（不包含边框）
    rows = (len(images) + columns - 1) // columns  # 向上取整
    width = columns * img_size[0]
    height = rows * img_size[1]

    print(f"[信息] 网格布局: {rows}行 x {columns}列")
    print(f"[信息] 合并后尺寸: {width}x{height}")

    # 创建空白画布（白色背景）
    merged = Image.new('RGB', (width, height), color=(255, 255, 255))

    # 粘贴图片并绘制边框
    for idx, img in images:
        row = (idx - 1) // columns
        col = (idx - 1) % columns
        x = col * img_size[0]
        y = row * img_size[1]

        # 粘贴图片
        merged.paste(img, (x, y))

        # 绘制边框（向内画在图片边缘）
        draw = ImageDraw.Draw(merged)
        border = border_size
        # 上边
        draw.line([(x, y), (x + img_size[0] - 1, y)], fill=(180, 180, 180), width=border)
        # 下边
        draw.line([(x, y + img_size[1] - 1), (x + img_size[0] - 1, y + img_size[1] - 1)], fill=(180, 180, 180), width=border)
        # 左边
        draw.line([(x, y), (x, y + img_size[1] - 1)], fill=(180, 180, 180), width=border)
        # 右边
        draw.line([(x + img_size[0] - 1, y), (x + img_size[0] - 1, y + img_size[1] - 1)], fill=(180, 180, 180), width=border)

    # 确保输出目录存在
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 保存图片
    merged.save(output_path, 'JPEG', quality=95)
    print(f"[成功] 合并图片已保存: {output_path}")

    return str(output_path)


def main():
    """命令行入口"""
    # 生成默认输出文件名（带时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_output = f'merged_images_{timestamp}.jpg'

    parser = argparse.ArgumentParser(
        description='将亚马逊搜索结果图片合并为一张大图',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从JSON文件读取
  python merge_images.py result.json

  # 指定输出文件
  python merge_images.py result.json -o merged.jpg

  # 自定义列数和尺寸
  python merge_images.py result.json --columns 4 --size 300

  # 从URL列表直接合并
  python merge_images.py --urls "url1,url2,url3" -o output.jpg

  # 禁用SSL验证（解决SSL错误）
  python merge_images.py result.json --no-ssl-verify
        """
    )

    parser.add_argument('input', nargs='?',
                        help='输入JSON文件路径（search_amazon.py的输出）')
    parser.add_argument('-o', '--output', default=default_output,
                        help=f'输出文件路径（默认: merged_images_YYYYMMDD_HHMMSS.jpg）')
    parser.add_argument('--columns', type=int, default=5,
                        help='列数（默认: 5）')
    parser.add_argument('--size', type=int, default=200,
                        help='每张图片的尺寸（默认: 200px）')
    parser.add_argument('--urls',
                        help='直接指定URL列表（逗号分隔）')
    parser.add_argument('--debug', action='store_true',
                        help='调试模式')
    parser.add_argument('--no-ssl-verify', action='store_true',
                        help='禁用SSL验证（解决SSL连接错误）')

    args = parser.parse_args()

    # 获取图片URL列表
    image_urls = []

    if args.urls:
        # 从命令行参数直接获取
        image_urls = [url.strip() for url in args.urls.split(',') if url.strip()]
    elif args.input:
        # 从JSON文件读取
        input_path = Path(args.input)
        if not input_path.exists():
            print(f"[错误] 文件不存在: {input_path}")
            sys.exit(1)

        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                image_urls = data.get('image_urls', [])
        except json.JSONDecodeError as e:
            print(f"[错误] JSON解析失败: {e}")
            sys.exit(1)
    else:
        parser.print_help()
        print("\n[错误] 请指定输入JSON文件或使用 --urls 参数")
        sys.exit(1)

    if not image_urls:
        print("[错误] 没有找到图片URL")
        sys.exit(1)

    print(f"[信息] 共 {len(image_urls)} 张图片待合并")

    # 合并图片
    output_path = merge_images_grid(
        image_urls=image_urls,
        output_path=args.output,
        columns=args.columns,
        img_size=(args.size, args.size),
        debug=args.debug,
        no_ssl_verify=args.no_ssl_verify
    )

    if output_path:
        print(f"\n完成! 可以使用该文件进行相似度对比分析")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
