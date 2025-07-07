#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪映特效搜索工具 - 最终优化版
"""

import os
import sys
import json
import io
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any
import requests
import gradio as gr

# ========================
# 配置日志
# ========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("jianying_search")


# ========================
# 工具函数
# ========================
def get_base_path() -> str:
    """
    获取当前执行文件的路径
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# ========================
# 默认配置
# ========================
DEFAULT_CONFIG: Dict[str, Any] = {
    "effect_type": 5,
    "count": 50,
    "save_full_result": True,
    "save_video_urls": True,
    "download_videos": False,
    "max_workers": 5,
    "save_dir": "data/results/jianying",
    "video_dir": "data/video",
    "min_resolution": "1080p",
    "cookies": {},
    "headers": {
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json",
        "origin": "https://www.jianying.com",
        "user-agent": "Mozilla/5.0",
    },
}


# ========================
# 核心类
# ========================
class JianyingEffectSearcher:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.save_dir = config.get("save_dir", DEFAULT_CONFIG["save_dir"])
        self.video_dir = config.get("video_dir", DEFAULT_CONFIG["video_dir"])

        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)

        self.cookies = config.get("cookies", DEFAULT_CONFIG["cookies"])
        self.headers = config.get("headers", DEFAULT_CONFIG["headers"])

        self.base_url = "https://www.jianying.com/artist/v1/effect/search"

        self.params = {
            "aid": "3704",
            "version_name": "18.1.0",
            "version_code": "11.0.0",
            "sdk_version": "18.1.0",
            "effect_sdk_version": "18.1.0",
            "device_platform": "web",
            "language": "zh-Hans",
            "device_type": "web",
            "channel": "online",
        }

    def search_effects(self, keyword: str) -> Dict[str, Any]:
        """
        搜索剪映特效
        """
        payload = {
            "effect_type": self.config["effect_type"],
            "query": keyword,
            "from": "normal_search",
            "need_recommend": True,
            "search_option": {"cc_web_use_new_search": True},
            "pack_optional": {
                "need_thumb": True,
                "thumb_opt": '{"is_support_webp":1}',
            },
            "count": self.config["count"],
            "offset": 0,
        }

        try:
            response = requests.post(
                self.base_url,
                params=self.params,
                cookies=self.cookies,
                headers=self.headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(f"✓ 搜索关键词 '{keyword}' 成功，共 {len(data.get('data', {}).get('effect_item_list', []))} 条")
            return data
        except Exception as e:
            logger.error(f"✗ 搜索关键词 '{keyword}' 失败: {e}")
            raise

    def save_result(self, keyword: str, result: Dict[str, Any]) -> str:
        """
        保存结果到json
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{keyword}_{timestamp}.json"
        file_path = os.path.join(self.save_dir, file_name)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ 搜索结果已保存到 {file_path}")
        return file_path

    def download_video(self, url: str, save_path: str) -> bool:
        """
        下载视频
        """
        try:
            headers = {
                "User-Agent": self.headers.get("user-agent", "Mozilla/5.0"),
                "Referer": "https://www.jianying.com/",
            }
            with requests.get(url, headers=headers, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(save_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            logger.info(f"✓ 视频下载完成: {save_path}")
            return True
        except Exception as e:
            logger.error(f"✗ 下载视频失败 {url}: {e}")
            return False

    def download_videos(self, result: Dict[str, Any], keyword: str) -> List[str]:
        """
        并发下载所有视频
        """
        downloaded = []
        effects = result.get("data", {}).get("effect_item_list", [])
        if not effects:
            logger.warning(f"关键词 '{keyword}' 无搜索结果")
            return downloaded

        keyword_dir = os.path.join(self.video_dir, keyword)
        os.makedirs(keyword_dir, exist_ok=True)

        with ThreadPoolExecutor(max_workers=self.config["max_workers"]) as pool:
            future_map = {}
            for effect in effects:
                video_data = effect.get("video", {}).get("origin_video", {})
                url = video_data.get("video_url")
                definition = video_data.get("definition", "unknown")
                if url:
                    filename = f"{effect.get('common_attr', {}).get('id', 'unknown')}_{definition}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
                    path = os.path.join(keyword_dir, filename)
                    future_map[pool.submit(self.download_video, url, path)] = path

            for future in as_completed(future_map):
                if future.result():
                    downloaded.append(future_map[future])

        logger.info(f"✓ 关键词 '{keyword}' 下载完成 {len(downloaded)} 个视频")
        return downloaded

    def search_and_save(self, keyword: str, download: bool) -> Dict[str, Any]:
        """
        搜索+保存+可选下载
        """
        result = self.search_effects(keyword)
        path = self.save_result(keyword, result)
        videos = []
        if download:
            videos = self.download_videos(result, keyword)
        return {"json": path, "videos": videos}


# ========================
# 配置加载
# ========================
def load_config(config_file="config.json") -> Dict[str, Any]:
    path = os.path.join(get_base_path(), config_file)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                conf = json.load(f)
                logger.info(f"✓ 配置文件已加载: {path}")
                return conf
        except Exception as e:
            logger.warning(f"✗ 配置文件读取失败: {e}")
    return DEFAULT_CONFIG


# ========================
# 任务执行
# ========================
def run_task(keywords_str: str, download: bool) -> str:
    """
    Gradio接口调用
    """
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    try:
        keywords = [k.strip() for k in keywords_str.split(",") if k.strip()]
        if not keywords:
            return "请输入至少一个关键词"

        config = load_config()
        searcher = JianyingEffectSearcher(config)

        success = 0
        for idx, kw in enumerate(keywords, 1):
            logger.info(f"\n{'='*20} [{idx}/{len(keywords)}] {kw} {'='*20}")
            try:
                searcher.search_and_save(kw, download)
                success += 1
            except Exception as e:
                logger.error(f"✗ 关键词 '{kw}' 执行出错: {e}")

        logger.info(f"\n全部任务完成，成功 {success}/{len(keywords)}")
    finally:
        logger.removeHandler(handler)

    return buffer.getvalue()


# ========================
# 主入口
# ========================
def main():
    with gr.Blocks(title="剪映特效搜索工具") as app:
        gr.Markdown("# ✂️ 剪映特效搜索工具")
        gr.Markdown("输入关键词（用英文逗号分隔），可选择是否下载视频文件。")

        with gr.Row():
            keyword_box = gr.Textbox(
                label="关键词", placeholder="例如: 春天, 美食, 旅行", scale=4
            )
            download_box = gr.Checkbox(label="下载视频", value=False)
            submit_btn = gr.Button("开始搜索", variant="primary")

        log_output = gr.Textbox(label="运行日志", lines=20, interactive=False)

        submit_btn.click(
            run_task,
            inputs=[keyword_box, download_box],
            outputs=log_output,
        )

    logger.info("已启动 Web 界面")
    app.launch()


if __name__ == "__main__":
    main()
