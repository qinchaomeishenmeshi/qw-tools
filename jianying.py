#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
剪映特效搜索工具 - 修复版
支持输入关键词搜索剪映特效，并将结果保存为JSON文件
"""

import requests
import json
import os
import sys
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading


def get_base_path():
    """获取基础路径，用于访问打包后的资源文件"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的可执行文件
        return os.path.dirname(sys.executable)
    else:
        # 如果是作为普通脚本运行
        return os.path.dirname(os.path.abspath(__file__))


# 默认配置
DEFAULT_CONFIG = {
    "keywords": [],  # 默认搜索关键词列表
    "effect_type": 5,                   # 特效类型
    "count": 50,                        # 每个关键词返回的结果数量
    "save_full_result": True,           # 是否保存完整结果
    "save_video_urls": True,            # 是否保存视频URL
    "download_videos": False,           # 是否下载视频
    "max_workers": 5,                   # 最大并发下载数
    "save_dir": "data/results/jianying", # 结果保存目录
    "video_dir": "data/video",          # 视频保存目录
    "min_resolution": "1080p",          # 最低视频分辨率要求
    "cookies": {                        # 默认cookies配置
        "store-region": "cn-hb",
        "store-region-src": "uid",
        "n_mh": "8KAIYd9nMFxwSVPpy4XEJKhGL0nyfw_35Nxkilxelck",
        "passport_csrf_token": "311c279e13e613ecc67ce486d0ba89fc",
        "passport_csrf_token_default": "311c279e13e613ecc67ce486d0ba89fc",
        "sid_guard": "fd9ebaee83632608f1ea217f78e4e558%7C1747967643%7C5184000%7CTue%2C+22-Jul-2025+02%3A34%3A03+GMT",
        "uid_tt": "10740e0db45c09735197a4ace7e23f20",
        "uid_tt_ss": "10740e0db45c09735197a4ace7e23f20",
        "sid_tt": "fd9ebaee83632608f1ea217f78e4e558",
        "sessionid": "fd9ebaee83632608f1ea217f78e4e558",
        "sessionid_ss": "fd9ebaee83632608f1ea217f78e4e558",
        "is_staff_user": "false",
        "sid_ucp_v1": "1.0.0-KDMxMTBlNmMzOTA5NjZlNDkzNzNjN2JjNmRiMTM2MmEyM2ZmMTgxZmYKHwiD99C91czNBBCbvb_BBhifrR8gDDCQ-NWyBjgIQCYaAmxmIiBmZDllYmFlZTgzNjMyNjA4ZjFlYTIxN2Y3OGU0ZTU1OA",
        "ssid_ucp_v1": "1.0.0-KDMxMTBlNmMzOTA5NjZlNDkzNzNjN2JjNmRiMTM2MmEyM2ZmMTgxZmYKHwiD99C91czNBBCbvb_BBhifrR8gDDCQ-NWyBjgIQCYaAmxmIiBmZDllYmFlZTgzNjMyNjA4ZjFlYTIxN2Y3OGU0ZTU1OA",
        "_uetvid": "27f18f50f8ac11efafd0f56303409b7b",
        "odin_tt": "fbfde72c09ee8e595b07dcb2ee27f68f31e09d7d61b840ff3a7bb4dd065e3689e9537ceca06b0ec148b103f9f9c5e454d1ae7de4f9b7c2aef70b43499d3a54bc",
        "_tea_web_id": "7397668772687349298",
        "s_v_web_id": "verify_mcburg40_nEP4SLZm_jTgg_4ePs_AD3M_38lbBBofbVEm",
        "COOKIE_CONSENT_PROMPT_CONFIG": "{%22status%22:1%2C%22settings%22:{%22firstPartyAnalytics%22:true%2C%22GoogleAnalytics%22:true}%2C%22updatedTime%22:1750849795438}",
        "ttwid": "1|hMs1clJXG22twhi8wRvpoUzyeaPmKoVyCJxSeR6RhvM|1750849800|7057d47a4f646231d5082ba5d30f95e04f0c2d70bcb96a5ee3f4383fdcd00dab"
    },
    "headers": {                        # 默认headers配置
        "accept": "application/json, text/plain, */*",
        "accept-language": "zh-CN,zh;q=0.9",
        "content-type": "application/json",
        "origin": "https://www.jianying.com",
        "priority": "u=1, i",
        "referer": "https://www.jianying.com/ai-creator/storyboard/23608377858?workspaceId=7397267851037687849&spaceId=7373936382663721254&draftId=881FB5BA-F5DF-4C00-B28C-52E87BAFA205",
        "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    }
}


class JianyingEffectSearcher:
    """剪映特效搜索器"""

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化剪映特效搜索器
        
        Args:
            config: 配置字典，默认为None，使用DEFAULT_CONFIG
        """
        # 使用提供的配置或默认配置
        self.config = config if config is not None else DEFAULT_CONFIG
        
        # 设置保存目录
        self.save_dir = self.config.get("save_dir", "data/results/jianying")
        self.video_dir = self.config.get("video_dir", "data/video")
        self.base_url = "https://www.jianying.com/artist/v1/effect/search"
        
        # 确保保存目录存在
        os.makedirs(self.save_dir, exist_ok=True)
        os.makedirs(self.video_dir, exist_ok=True)
        
        # 从配置中获取cookies和headers
        self.cookies = self.config.get("cookies", DEFAULT_CONFIG["cookies"])
        self.headers = self.config.get("headers", DEFAULT_CONFIG["headers"])
        
        # 基本请求参数
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

    def search_single_page(self, 
                          keyword: str, 
                          effect_type: int = 5, 
                          count: int = 50, 
                          offset: int = 0, 
                          need_recommend: bool = True) -> Dict[str, Any]:
        """
        搜索剪映特效（单页）
        
        Args:
            keyword: 搜索关键词
            effect_type: 特效类型，默认为5
            count: 返回结果数量，默认为50
            offset: 分页偏移量，默认为0
            need_recommend: 是否需要推荐，默认为True
            
        Returns:
            搜索结果字典
        """
        if not keyword:
            raise ValueError("搜索关键词不能为空")
        
        try:
            # 构建请求数据
            json_data = {
                "effect_type": effect_type,
                "query": keyword,
                "from": "normal_search",
                "need_recommend": need_recommend,
                "search_option": {
                    "cc_web_use_new_search": True
                },
                "pack_optional": {
                    "need_thumb": True,
                    "thumb_opt": '{"is_support_webp":1}'
                },
                "count": count,
                "offset": offset
            }

            # 发送请求
            response = requests.post(
                self.base_url,
                params=self.params,
                cookies=self.cookies,
                headers=self.headers,
                json=json_data,
                timeout=30
            )
            
            # 检查响应状态
            response.raise_for_status()
            
            # 解析响应数据
            result = response.json()
            return result
            
        except requests.RequestException as e:
            print(f"请求异常: {e}")
            raise
        except ValueError as e:
            print(f"参数错误: {e}")
            raise
        except Exception as e:
            print(f"搜索特效时发生异常: {e}")
            raise

    def search_and_save(self, keyword: str, download_videos: bool = False) -> Dict[str, Any]:
        """
        搜索并保存结果的便捷方法
        
        Args:
            keyword: 搜索关键词
            download_videos: 是否下载视频
            
        Returns:
            保存的文件路径字典
        """
        try:
            print(f"开始搜索关键词 '{keyword}'")
            
            # 搜索特效
            result = self.search_single_page(keyword)
            
            # 保存结果
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"jianying_effect_{keyword}_{timestamp}.json"
            file_path = os.path.join(self.save_dir, file_name)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"搜索结果已保存到: {file_path}")
            
            # 如果需要下载视频，这里可以添加视频下载逻辑
            if download_videos:
                print(f"关键词 '{keyword}' 的视频下载功能暂未实现")
            
            return {'result_path': file_path}
            
        except Exception as e:
            print(f"搜索并保存结果时发生异常: {e}")
            raise


def load_config(config_file: str = "config.json") -> Dict[str, Any]:
    """
    从JSON文件加载配置
    
    Args:
        config_file: 配置文件路径，默认为config.json
        
    Returns:
        配置字典
    """
    config_path = os.path.join(get_base_path(), config_file)
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"已从 {config_path} 加载配置")
            return config
        else:
            print(f"配置文件 {config_path} 不存在，使用默认配置")
            return DEFAULT_CONFIG
    except Exception as e:
        print(f"加载配置文件 '{config_path}' 异常: {e}，将使用默认配置。")
        return DEFAULT_CONFIG


class TextRedirector:
    """一个将文本重定向到tkinter Text小部件的类"""
    def __init__(self, widget: scrolledtext.ScrolledText):
        self.widget = widget

    def write(self, text: str):
        """将文本写入小部件"""
        def update_text():
            self.widget.config(state='normal')
            self.widget.insert(tk.END, text)
            self.widget.see(tk.END)
            self.widget.config(state='disabled')
        
        # 确保在主线程中更新GUI
        self.widget.after(0, update_text)
    
    def flush(self):
        """flush方法，为了兼容sys.stdout接口"""
        pass


class JianyingSearchApp:
    """剪映特效搜索GUI应用"""

    def __init__(self, master):
        """
        初始化应用
        
        Args:
            master: 父Tkinter窗口
        """
        self.master = master
        self.master.title("剪映特效搜索工具 V1.2")
        self.master.geometry("900x700")
        
        # 创建主框架
        self.main_frame = ttk.Frame(master)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.download_var = tk.BooleanVar(value=False)  # 用于控制是否下载视频
        self.create_widgets()
        
        # 重定向标准输出到日志文本框
        self.text_redirector = TextRedirector(self.log_text)
        
    def create_widgets(self):
        """创建GUI组件"""
        # 标题
        title_label = ttk.Label(self.main_frame, text="剪映特效搜索工具", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 输入区域框架
        input_frame = ttk.LabelFrame(self.main_frame, text="搜索设置", padding=10)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 关键词输入行
        keyword_frame = ttk.Frame(input_frame)
        keyword_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(keyword_frame, text="关键词:").pack(side=tk.LEFT)
        self.keywords_entry = ttk.Entry(keyword_frame, width=50)
        self.keywords_entry.pack(side=tk.LEFT, padx=(10, 0), expand=True, fill=tk.X)
        
        # 说明文本
        help_label = ttk.Label(input_frame, text="多个关键词请用英文逗号分隔，例如：绿茶,咖啡,果汁", 
                              font=("Arial", 9), foreground="gray")
        help_label.pack(anchor=tk.W, pady=(0, 10))
        
        # 选项框架
        options_frame = ttk.Frame(input_frame)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 下载视频选项
        self.download_check = ttk.Checkbutton(options_frame, text="下载视频文件", 
                                             variable=self.download_var)
        self.download_check.pack(side=tk.LEFT)
        
        # 按钮框架
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X)
        
        # 搜索按钮
        self.search_button = ttk.Button(button_frame, text="开始搜索", 
                                       command=self.start_search_thread)
        self.search_button.pack(side=tk.LEFT)
        
        # 清除日志按钮
        self.clear_button = ttk.Button(button_frame, text="清除日志", 
                                      command=self.clear_log)
        self.clear_button.pack(side=tk.LEFT, padx=(10, 0))
        
        # 日志输出区域
        log_frame = ttk.LabelFrame(self.main_frame, text="运行日志", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # 创建日志文本框
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, 
                                                 state='disabled', height=25)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 初始化消息
        self.log_message("剪映特效搜索工具已启动，请输入关键词开始搜索。")
        
    def log_message(self, message: str):
        """向日志区域添加消息"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')
        
    def clear_log(self):
        """清除日志内容"""
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state='disabled')
        self.log_message("日志已清除。")

    def start_search_thread(self):
        """启动搜索线程，防止GUI阻塞"""
        keywords_str = self.keywords_entry.get().strip()
        if not keywords_str:
            messagebox.showerror("错误", "请输入至少一个关键词。")
            return
            
        keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
        
        if not keywords:
            messagebox.showerror("错误", "请输入有效的关键词。")
            return
        
        # 禁用按钮，防止重复点击
        self.search_button.config(state='disabled')
        
        # 创建并启动线程
        thread = threading.Thread(target=self.run_search, args=(keywords,), daemon=True)
        thread.start()

    def run_search(self, keywords: List[str]):
        """在线程中执行实际的搜索操作"""
        try:
            # 重定向输出
            original_stdout = sys.stdout
            original_stderr = sys.stderr
            sys.stdout = self.text_redirector
            sys.stderr = self.text_redirector
            
            print("正在加载配置...")
            config = load_config()
            
            searcher = JianyingEffectSearcher(config)
            print("配置加载成功，开始执行搜索任务...")

            should_download = self.download_var.get()
            
            success_count = 0
            for i, keyword in enumerate(keywords, 1):
                print(f"\n{'='*50}")
                print(f"[{i}/{len(keywords)}] 正在搜索关键词: {keyword}")
                print(f"{'='*50}")
                
                try:
                    result = searcher.search_and_save(keyword=keyword, download_videos=should_download)
                    print(f"✓ 关键词 '{keyword}' 搜索完成")
                    success_count += 1
                    
                except Exception as e:
                    print(f"✗ 搜索关键词 '{keyword}' 时发生错误: {e}")
            
            print(f"\n{'='*50}")
            print(f"所有任务已完成！成功: {success_count}/{len(keywords)}")
            print(f"{'='*50}")
            
            # 恢复原始输出
            sys.stdout = original_stdout
            sys.stderr = original_stderr

        except Exception as e:
            print(f"\n发生严重错误: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 恢复按钮状态
            self.master.after(0, lambda: self.search_button.config(state='normal'))


def main():
    """主函数，启动GUI应用"""
    try:
        root = tk.Tk()
        app = JianyingSearchApp(master=root)
        
        # 设置窗口居中
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        root.mainloop()
        
    except Exception as e:
        print(f"启动GUI应用时发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()