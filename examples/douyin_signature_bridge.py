# -*- coding: utf-8 -*-
"""
抖音签名层桥接参考 —— 不自己逆向，桥接到 F2（活跃维护、已解决四重门）。

⚠️ 定位：这是 MediaCrawler 的【请求 / 签名层】参考模板，**不是 Mirage 的行为层加固范围**
   （边界说明见 docs/signature-layer.md）。Mirage 不接管、不保证 F2 上游兼容。

抖音四重门 → F2 对应解法（对着 F2 当前真实 API 写）：
  ① 拿不到 video/user id（首页 SSR 空壳）→ SecUserIdFetcher.get_sec_user_id(分享/主页链接)
  ② msToken 动态生成（不在 cookie 里）     → TokenManager.gen_real_msToken() / gen_false_msToken()
  ③ a_bogus + ttwid                        → ABogusManager.model_2_endpoint() + TokenManager.gen_ttwid()
  ④ webid / verifyFp / 参数                 → TokenManager.gen_webid() / VerifyFpManager.gen_verify_fp()
  ⑤ JA3 传输层指纹（httpx 会暴露）          → curl_cffi requests(impersonate="chrome")  # 见 docs/tls-fingerprint.md

前置：  pip install f2 curl_cffi        （F2 = Apache-2.0，仅供学习研究）

本文件是**结构正确的参考模板**，按 F2 当前 API 写。F2 会随抖音改版更新——用前请对照
F2 最新源码/文档核对方法签名，并自备有效 cookie。真跑由你手动（AI 不代跑、不主动触发风控）。
"""
from __future__ import annotations

# 与签名绑定的 UA 必须和真实浏览器一致（a_bogus 对 UA 敏感）
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def resolve_sec_user_id(share_or_profile_url: str) -> str:
    """① 从分享/主页链接反解 sec_user_id，绕开"首页 SSR 空壳拿不到 id"。
    若你已在 async 上下文，请直接 await SecUserIdFetcher.get_sec_user_id(url)。"""
    import asyncio

    from f2.apps.douyin.utils import SecUserIdFetcher
    return asyncio.run(SecUserIdFetcher.get_sec_user_id(share_or_profile_url))


def build_signed_request(base_endpoint: str, params: dict, cookie: str) -> tuple[str, dict]:
    """把一个抖音 web 接口补齐四重门签名，返回 (signed_url, headers)。

    base_endpoint 例：'https://www.douyin.com/aweme/v1/web/aweme/post/'
    params        例：{'sec_user_id': ..., 'count': 18, 'max_cursor': 0}
    """
    from f2.apps.douyin.utils import ABogusManager, TokenManager

    # ② msToken：动态生成（gen_real 联网拿真 token / gen_false 纯本地兜底）
    ms_token = TokenManager.gen_real_msToken()
    params = {**params, "msToken": ms_token}

    # ③ a_bogus：把带 msToken 的 params 一起签，F2 返回补好 a_bogus 的完整 URL
    signed_url = ABogusManager.model_2_endpoint(UA, base_endpoint, params)

    # ③ ttwid + cookie 拼装
    ttwid = TokenManager.gen_ttwid()
    headers = {
        "User-Agent": UA,
        "Referer": "https://www.douyin.com/",
        "Cookie": f"{cookie}; ttwid={ttwid}; msToken={ms_token}",
    }
    return signed_url, headers


def fetch_with_ja3(url: str, headers: dict):
    """⑤ 用 curl_cffi 发请求：JA3 伪装成 Chrome（httpx 的 JA3 会暴露，见 docs/tls-fingerprint.md）。"""
    from curl_cffi import requests
    return requests.get(url, headers=headers, impersonate="chrome", timeout=15)


def demo(cookie: str, share_url: str):
    """端到端示范（需自备 cookie + 已 pip install f2 curl_cffi；请你手动跑）。"""
    sec_uid = resolve_sec_user_id(share_url)                          # ①
    base = "https://www.douyin.com/aweme/v1/web/aweme/post/"
    params = {"sec_user_id": sec_uid, "count": 18, "max_cursor": 0}
    url, headers = build_signed_request(base, params, cookie)          # ②③④
    resp = fetch_with_ja3(url, headers)                                # ⑤
    return resp


if __name__ == "__main__":
    print(__doc__)
    print(">> 这是参考模板。请先 `pip install f2 curl_cffi`、自备 cookie，")
    print(">> 对照 F2 最新文档核对 API 后，手动调用 demo(cookie, share_url)。")
