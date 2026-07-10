# -*- coding: utf-8 -*-
"""
桥接快速参考 —— 对接海内外主流平台的**活维护 clean-API 栈**最小正确模板。

原则（和 douyin_signature_bridge.py 一致）：
  - 只给**活维护 + API 干净**的栈写模板（yt-dlp / PRAW / Telethon / instagrapi）。
  - 国内电商/美团/招聘那些**偏旧 crack 库不写虚模板**（见 docs/platform-coverage.md 的新鲜度标注，用前自核对）。
  - 这些都属 MediaCrawler/Mirage 行为层**之外**的请求层；Mirage 只给模板，不接管、不保证上游兼容。

前置：按需 `pip install yt-dlp praw telethon instagrapi`。
本文件全懒加载，无库也能 import/跑 __main__（只打印说明）。真跑需自备凭证、自己手动跑（AI 不代跑、不主动触发风控）。
"""
from __future__ import annotations


def youtube_or_cnvideo(url: str) -> dict:
    """长视频（YouTube/爱奇艺/腾讯/优酷/B站…1800 站）：yt-dlp 一把梭，公开内容零账号风险。"""
    import yt_dlp
    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        return ydl.extract_info(url, download=False)      # 只取元数据；download=True 才下


def reddit_hot(subreddit: str, client_id: str, client_secret: str, ua: str, limit: int = 10):
    """Reddit：官方 API wrapper PRAW（需注册 app 拿 client_id/secret，限流 100/min）。"""
    import praw
    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=ua)
    return [(p.title, p.score, p.url) for p in reddit.subreddit(subreddit).hot(limit=limit)]


async def telegram_channel_messages(channel: str, api_id: int, api_hash: str, limit: int = 100):
    """Telegram：官方 MTProto 库 Telethon（api_id/api_hash 从 my.telegram.org 拿）。异步。"""
    from telethon import TelegramClient
    async with TelegramClient("mirage_session", api_id, api_hash) as client:
        return [m.text async for m in client.iter_messages(channel, limit=limit)]


def instagram_user_medias(username: str, login_user: str, login_pw: str, amount: int = 20):
    """Instagram：instagrapi（private API，活维护到 2026；只用小号、低频，封号风险自负）。"""
    from instagrapi import Client
    cl = Client()
    cl.login(login_user, login_pw)                        # 建议配合 session 持久化，别每次登
    return cl.user_medias(cl.user_id_from_username(username), amount)


# —— 音乐 / 图集：CLI 工具直接用，无需写桥接 ——
#   音乐（网易云/QQ/酷狗…数十家）：pip install musicdl  →  musicdl 命令行搜索下载
#   图集（Pinterest 等）：pip install gallery-dl        →  gallery-dl <url>


if __name__ == "__main__":
    print(__doc__)
    print(">> 这是最小正确模板。按需 pip install，自备凭证，对照各库最新文档核对后**手动**调用。")
    print(">> 偏旧的国内 crack 库（淘宝/美团/招聘）不在此写模板 —— 见 docs/platform-coverage.md。")
