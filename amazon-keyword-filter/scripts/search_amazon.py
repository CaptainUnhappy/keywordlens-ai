#!/usr/bin/env python3
"""
亚马逊搜索脚本
在亚马逊搜索关键词并返回前N个商品图片URL
"""

import sys
import time
import json
import os
from datetime import datetime
from urllib.parse import quote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def init_driver(headless=False):
    """初始化浏览器驱动"""
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    return webdriver.Chrome(options=options)


def hide_clutter_elements(driver, debug=False):
    """
    隐藏页面上的干扰元素（导航栏、侧边栏、广告等）

    Args:
        driver: WebDriver实例
        debug: 是否输出调试信息
    """
    # 定义要隐藏的元素选择器 - 只隐藏明确的外围元素
    hide_selectors = [
        # ========== 顶部导航栏 ==========
        "#nav-belt",
        "#nav-main",
        "#navbar",
        ".nav-left",
        ".nav-right",

        # ========== 侧边栏和筛选器 ==========
        "#s-refinements",
        ".s-refinements",

        # ========== 页脚 ==========
        "#navFooter",
        ".footer",

        # ========== 其他干扰元素 ==========
        "#nav-tools",
        "#nav-search-wrapper",
    ]

    # 使用 JavaScript 隐藏元素
    hide_script = ""
    for selector in hide_selectors:
        hide_script += f"""
        try {{
            document.querySelectorAll("{selector}").forEach(el => {{
                el.style.display = 'none';
            }});
        }} catch(e) {{}}
        """

    driver.execute_script(hide_script)

    if debug:
        print("[调试] 已隐藏干扰元素（导航栏、侧边栏、页脚）")


def save_screenshot(driver, keyword, output_path=None, debug=False):
    """
    保存页面截图

    Args:
        driver: WebDriver实例
        keyword: 搜索关键词（用于生成文件名）
        output_path: 自定义输出路径
        debug: 是否输出调试信息

    Returns:
        str: 保存的截图文件路径
    """
    # 生成文件名
    safe_keyword = keyword.replace(" ", "_").replace("/", "_")[:30]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if output_path:
        # 如果是目录，在目录下生成文件名
        if os.path.isdir(output_path):
            filename = f"amazon_search_{safe_keyword}_{timestamp}.png"
            filepath = os.path.join(output_path, filename)
        else:
            filepath = output_path
            # 确保目录存在
            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    else:
        # 默认保存到当前目录
        filepath = f"amazon_search_{safe_keyword}_{timestamp}.png"

    # 设置窗口大小（获得更好的截图效果）
    original_size = driver.get_window_size()
    driver.set_window_size(1920, 1080)

    try:
        driver.save_screenshot(filepath)

        if debug:
            print(f"[调试] 截图已保存: {filepath}")

        return filepath

    finally:
        # 恢复原始窗口大小
        driver.set_window_size(original_size['width'], original_size['height'])


def search_amazon(keyword, amazon_domain="amazon.com", max_products=20,
                  debug=False, headless=True, wait_before_close=5, silent=False,
                  screenshot=False, screenshot_path=None, hide_clutter=False):
    """
    搜索亚马逊并获取商品图片URL

    Args:
        keyword: 搜索关键词
        amazon_domain: 亚马逊域名
        max_products: 最多获取多少个商品图片
        debug: 调试模式，显示详细信息
        headless: 无头模式
        wait_before_close: 关闭前等待秒数（非无头模式）
        screenshot: 是否保存截图
        screenshot_path: 截图保存路径
        hide_clutter: 是否隐藏干扰元素（导航栏、侧边栏等）

    Returns:
        dict: 包含image_urls列表和screenshot_path（如果有）的字典
    """
    driver = init_driver(headless=headless)

    try:
        search_url = f"https://www.{amazon_domain}/s?k={quote(keyword)}"

        if debug:
            print(f"[调试] 访问URL: {search_url}")

        driver.get(search_url)
        time.sleep(2)

        # 等待图片加载
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "s-image")))

        if debug:
            print(f"[调试] 页面标题: {driver.title}")
            print(f"[调试] 当前URL: {driver.current_url}")

        # 滚动页面，触发懒加载
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(0.5)
        driver.execute_script("window.scrollTo(0, 1000);")
        time.sleep(0.5)

        # 获取商品图片（排除logo和其他非商品图片）
        # 方法1: 使用data-image-latency属性（更精确）
        product_images = driver.find_elements(
            By.CSS_SELECTOR,
            "img[data-image-latency='s-product-image']"
        )

        if debug:
            print(f"[调试] 找到 {len(product_images)} 个产品图片（精确选择器）")

        # 如果精确选择器没找到，回退到通用选择器
        if len(product_images) == 0:
            if debug:
                print("[调试] 使用备选选择器...")
            product_images = driver.find_elements(By.CLASS_NAME, "s-image")
            if debug:
                print(f"[调试] 找到 {len(product_images)} 个图片（通用选择器）")

        # 提取URL并过滤
        image_urls = []
        for i, img in enumerate(product_images[:max_products * 2]):  # 多取一些以防过滤
            try:
                src = img.get_attribute('src')
                alt = img.get_attribute('alt') or ""

                # 过滤条件：
                # 1. URL必须存在且是http开头
                # 2. 排除明显的logo（包含amazon-logo等）
                # 3. 排除太小的图片（logo通常很小）
                if src and src.startswith('http'):
                    # 排除logo
                    if 'amazon-logo' in src.lower() or 'logo' in alt.lower():
                        if debug:
                            print(f"[调试] 跳过logo: {alt[:50]}")
                        continue

                    # 排除广告图片
                    if 'ad-feedback' in src.lower():
                        if debug:
                            print(f"[调试] 跳过广告: {alt[:50]}")
                        continue

                    image_urls.append(src)

                    if debug:
                        print(f"[调试] 图片 {len(image_urls)}: {alt[:50]}")
                        print(f"      URL: {src}")

                    # 达到目标数量就停止
                    if len(image_urls) >= max_products:
                        break

            except Exception as e:
                if debug:
                    print(f"[调试] 获取图片失败: {e}")
                continue

        if debug:
            print(f"[调试] 成功获取 {len(image_urls)} 个有效产品图片")

        # 截图功能
        saved_screenshot = None
        if screenshot:
            if hide_clutter:
                hide_clutter_elements(driver, debug)

            saved_screenshot = save_screenshot(
                driver, keyword,
                output_path=screenshot_path,
                debug=debug
            )

        # 非无头模式下，等待一段时间再关闭（让用户看清楚）
        if not headless and wait_before_close > 0 and not silent:
            print(f"\n浏览器将在 {wait_before_close} 秒后关闭...")
            for i in range(wait_before_close, 0, -1):
                print(f"  {i}秒...", end='\r')
                time.sleep(1)
            print("\n关闭浏览器")

        return {
            "image_urls": image_urls,
            "screenshot_path": saved_screenshot
        }

    except Exception as e:
        if debug:
            print(f"[错误] {e}")
            import traceback
            traceback.print_exc()
        return {
            "image_urls": [],
            "screenshot_path": None
        }

    finally:
        driver.quit()


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python search_amazon.py <keyword> [amazon_domain] [max_products] [选项]")
        print()
        print("选项:")
        print("  --debug              调试模式，显示详细信息")
        print("  --no-headless        显示浏览器窗口")
        print("  --wait=N             关闭前等待N秒（非无头模式）")
        print("  --json-only          仅输出JSON格式")
        print("  --screenshot         保存页面截图")
        print("  --screenshot-path=PATH  截图保存路径")
        print("  --hide-clutter       隐藏干扰元素（导航、价格、购物车、星级、推广等）")
        print()
        print("示例:")
        print('  python search_amazon.py "wireless earbuds"')
        print('  python search_amazon.py "wireless earbuds" amazon.com 10')
        print('  python search_amazon.py "test" --debug')
        print('  python search_amazon.py "test" --screenshot')
        print('  python search_amazon.py "test" --screenshot --hide-clutter')
        print('  python search_amazon.py "test" --screenshot --screenshot-path=./screenshots')
        print()
        sys.exit(1)

    # 解析参数
    keyword = sys.argv[1]
    amazon_domain = "amazon.com"
    max_products = 20
    debug = False
    headless = True  # 默认无头模式
    wait_before_close = 5
    json_only = False  # 仅输出JSON格式
    screenshot = False  # 是否截图
    screenshot_path = None  # 截图保存路径
    hide_clutter = False  # 是否隐藏干扰元素

    # 处理可选参数
    for arg in sys.argv[2:]:
        if arg.startswith('--'):
            if arg == '--debug':
                debug = True
            elif arg == '--no-headless':
                headless = False
            elif arg == '--json-only':
                json_only = True
            elif arg == '--screenshot':
                screenshot = True
            elif arg == '--hide-clutter':
                hide_clutter = True
            elif arg.startswith('--wait='):
                wait_before_close = int(arg.split('=')[1])
            elif arg.startswith('--screenshot-path='):
                screenshot_path = arg.split('=', 1)[1]
        elif '.' in arg and 'amazon' in arg:
            amazon_domain = arg
        elif arg.isdigit():
            max_products = int(arg)

    if not json_only:
        print("=" * 60)
        print("Amazon 商品图片搜索")
        print("=" * 60)
        print(f"搜索关键词: {keyword}")
        print(f"亚马逊站点: {amazon_domain}")
        print(f"最多获取: {max_products}个商品")
        print(f"调试模式: {'开启' if debug else '关闭'}")
        print(f"无头模式: {'开启' if headless else '关闭'}")
        print(f"截图: {'开启' if screenshot else '关闭'}")
        if screenshot:
            print(f"  隐藏干扰元素: {'是' if hide_clutter else '否'}")
            if screenshot_path:
                print(f"  保存路径: {screenshot_path}")
        if not headless:
            print(f"等待时间: {wait_before_close}秒")
        print("=" * 60)
        print()

    # 执行搜索
    search_result = search_amazon(
        keyword=keyword,
        amazon_domain=amazon_domain,
        max_products=max_products,
        debug=debug,
        headless=headless,
        wait_before_close=wait_before_close,
        silent=json_only,
        screenshot=screenshot,
        screenshot_path=screenshot_path,
        hide_clutter=hide_clutter
    )

    image_urls = search_result["image_urls"]
    saved_screenshot = search_result["screenshot_path"]

    # 输出结果
    result = {
        "keyword": keyword,
        "amazon_domain": amazon_domain,
        "image_urls": image_urls,
        "count": len(image_urls)
    }

    # 添加截图路径到结果
    if saved_screenshot:
        result["screenshot_path"] = saved_screenshot

    if json_only:
        # 仅输出JSON
        print(json.dumps(result, ensure_ascii=False))
    else:
        # 正常输出格式
        print()
        print("=" * 60)
        print("搜索结果")
        print("=" * 60)

        print(json.dumps(result, indent=2, ensure_ascii=False))

        if len(image_urls) > 0:
            print()
            print(f"✓ 成功获取 {len(image_urls)} 个产品图片")
        else:
            print()
            print("✗ 未获取到图片")
            print("建议: 使用 --debug 参数查看详细信息")

        if saved_screenshot:
            print(f"✓ 截图已保存: {saved_screenshot}")


class AmazonSearcher:
    """
    亚马逊搜索器 - 支持浏览器复用，提升批量处理效率

    使用示例:
        searcher = AmazonSearcher(headless=True)
        try:
            result1 = searcher.search("keyword1")
            result2 = searcher.search("keyword2")
            # 浏览器保持打开，无需重复启动
        finally:
            searcher.close()
    """

    def __init__(self, amazon_domain="amazon.com", headless=True, debug=False):
        """
        初始化搜索器

        Args:
            amazon_domain: 亚马逊域名
            headless: 无头模式
            debug: 调试模式
        """
        self.amazon_domain = amazon_domain
        self.headless = headless
        self.debug = debug
        self.driver = None
        self._initialized = False

    def _ensure_driver(self):
        """确保浏览器已初始化"""
        if not self._initialized or self.driver is None:
            if self.debug:
                print("[调试] 初始化浏览器...")
            self.driver = init_driver(headless=self.headless)
            self._initialized = True

    def search(self, keyword, max_products=20, hide_clutter=False):
        """
        搜索关键词（复用浏览器）

        Args:
            keyword: 搜索关键词
            max_products: 最多获取多少个商品
            hide_clutter: 是否隐藏干扰元素

        Returns:
            dict: {"image_urls": [...], "count": N}
        """
        self._ensure_driver()

        try:
            search_url = f"https://www.{self.amazon_domain}/s?k={quote(keyword)}"

            if self.debug:
                print(f"[调试] 访问URL: {search_url}")

            self.driver.get(search_url)
            time.sleep(2)

            # 等待图片加载
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "s-image")))

            # 滚动页面，触发懒加载
            self.driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(0.3)
            self.driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(0.3)

            # 获取商品图片
            product_images = self.driver.find_elements(
                By.CSS_SELECTOR,
                "img[data-image-latency='s-product-image']"
            )

            if len(product_images) == 0:
                product_images = self.driver.find_elements(By.CLASS_NAME, "s-image")

            # 提取URL并过滤
            image_urls = []
            for img in product_images[:max_products * 2]:
                try:
                    src = img.get_attribute('src')
                    alt = img.get_attribute('alt') or ""

                    if src and src.startswith('http'):
                        if 'amazon-logo' in src.lower() or 'logo' in alt.lower():
                            continue
                        if 'ad-feedback' in src.lower():
                            continue

                        image_urls.append(src)

                        if len(image_urls) >= max_products:
                            break

                except Exception:
                    continue

            if self.debug:
                print(f"[调试] 获取 {len(image_urls)} 个图片")

            return {
                "image_urls": image_urls,
                "count": len(image_urls)
            }

        except Exception as e:
            if self.debug:
                print(f"[错误] 搜索失败: {e}")
            return {
                "image_urls": [],
                "count": 0
            }

    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self._initialized = False
            if self.debug:
                print("[调试] 浏览器已关闭")

    def __enter__(self):
        """支持 with 语句"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """支持 with 语句"""
        self.close()


if __name__ == "__main__":
    main()
