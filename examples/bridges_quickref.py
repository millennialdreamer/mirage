# -*- coding: utf-8 -*-
"""
Bridge quick reference —— minimal correct template for the **actively maintained clean-API stack** targeting mainstream platforms at
home and abroad.

Principles (consistent with douyin_signature_bridge.py):
  - Only write templates for **actively maintained + clean API** stacks (yt-dlp / PRAW / Telethon / instagrapi).
  - Domestic e-commerce/Meituan/recruitment and other **outdated crack libraries are not given fake templates** (see freshness
  annotations in docs/platform-coverage.md, verify before use).
  - These all belong to the request layer **outside** the MediaCrawler/Mirage behavior layer; Mirage only provides templates, does not
  take over, does not guarantee upstream compatibility.

Prerequisites: `pip install yt-dlp praw telethon instagrapi` as needed.
This file is fully lazy-loaded; it can be imported/run __main__ without the libraries (only prints instructions). To actually run,
supply your own credentials and run manually (AI does not run on your behalf, does not proactively trigger risk control).
"""
from __future__ import annotations


def youtube_or_cnvideo(url: str) -> dict:
    """Long video: yt-dlp one shot, public content has zero account risk.
    ⚠️ extract_info may return None/raise; wrap in try; some sites (Bilibili etc.) require cookies;
       Youku/Mango TV have DRM, yt-dlp support is poor — mainly YouTube/iQIYI/Tencent partially usable, don't over-rely on domestic long video."""
    import yt_dlp
    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
        return ydl.extract_info(url, download=False)      # metadata only; download=True actually downloads


def reddit_hot(subreddit: str, client_id: str, client_secret: str, ua: str, limit: int = 10):
    """Reddit: official API wrapper PRAW. Passing only id/secret/ua = read-only mode, enough for public subreddits.
    ⚠️ Register a script app first at reddit.com/prefs/apps; from 2026 rate limits for unauthenticated calls are stricter, prepare exponential backoff."""
    import praw
    reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=ua)
    return [(p.title, p.score, p.url) for p in reddit.subreddit(subreddit).hot(limit=limit)]


async def telegram_channel_messages(channel: str, api_id: int, api_hash: str, limit: int = 100):
    """Telegram: official MTProto library Telethon (get api_id/api_hash from my.telegram.org). Async.
    ⚠️ First run will stall at interactive login (requires phone number + verification code) — **run once manually** to generate
    mirage_session.session,
       only then can it be automated. Don't expect this snippet to run unattended directly."""
    from telethon import TelegramClient
    async with TelegramClient("mirage_session", api_id, api_hash) as client:
        return [m.text async for m in client.iter_messages(channel, limit=limit)]


def instagram_user_medias(username: str, login_user: str, login_pw: str, amount: int = 20):
    """Instagram: instagrapi (private API, actively maintained, still released as of 2026-07; use alt account only, low frequency).
    ⚠️ **Must** persist login state with cl.dump_settings()/load_settings() — frequent login will trigger challenge (verification
    code/email) or even ban;
       production should configure cl.challenge_code_handler. This is a minimal example, don't use raw."""
    from instagrapi import Client
    cl = Client()
    cl.login(login_user, login_pw)                        # preferably combine with session persistence, don't log in every time
    return cl.user_medias(cl.user_id_from_username(username), amount)


# —— Music / image collections: use CLI tools directly, no bridge needed ——
#   Music (NetEase Cloud/QQ/Kugou... dozens of sites): pip install musicdl  →  musicdl command-line search & download
#   Image collections (Pinterest etc.): pip install gallery-dl        →  gallery-dl <url>


if __name__ == "__main__":
    print(__doc__)
    print(">> Minimal correct templates. pip install what you need, supply your own")
    print(">> credentials, check each library's current docs, and call them **manually**.")
    print(">> Outdated domestic crack libraries (Taobao/Meituan/recruitment) are not templated here — see docs/platform-coverage.md.")
