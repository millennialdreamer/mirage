# -*- coding: utf-8 -*-
"""
Douyin signature layer bridge reference — don't reverse-engineer it yourself, bridge to F2 (actively maintained, already solved the four
gates).

⚠️ Positioning: This is MediaCrawler's [request / signature layer] reference template, **not Mirage's behavior-layer hardening scope**
   (boundary notes see docs/signature-layer.md). Mirage does not take over or guarantee F2 upstream compatibility.

Douyin four gates → F2 corresponding solutions (written against F2's current real API):
  ① Can't get video/user id (homepage SSR shell) → SecUserIdFetcher.get_sec_user_id(share/profile link)
  ② msToken dynamic generation (not in cookie)     → TokenManager.gen_real_msToken() / gen_false_msToken()
  ③ a_bogus + ttwid                        → ABogusManager.model_2_endpoint() + TokenManager.gen_ttwid()
  ④ webid / verifyFp / params                 → TokenManager.gen_webid() / VerifyFpManager.gen_verify_fp()
  ⑤ JA3 transport-layer fingerprint (httpx will expose it)          → curl_cffi requests(impersonate="chrome")  # see docs/tls-
  fingerprint.md

Prerequisites:  pip install f2 curl_cffi        (F2 = Apache-2.0, for study/research only)

This file is a **structurally-correct reference template**, written against F2's current API. F2 will update as Douyin changes — before
use, check
the latest F2 source/docs for method signatures, and prepare valid cookies. Actually running is manual (AI does not run it for you and
does not proactively trigger risk control).
"""
from __future__ import annotations

# The UA bound to the signature must match a real browser (a_bogus is UA-sensitive)
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def resolve_sec_user_id(share_or_profile_url: str) -> str:
    """① Resolve sec_user_id from share/profile link, bypassing the "homepage SSR shell can't get id".
    If you are already in an async context, please directly await SecUserIdFetcher.get_sec_user_id(url)."""
    import asyncio

    from f2.apps.douyin.utils import SecUserIdFetcher
    return asyncio.run(SecUserIdFetcher.get_sec_user_id(share_or_profile_url))


def build_signed_request(base_endpoint: str, params: dict, cookie: str) -> tuple[str, dict]:
    """Complete the four-gate signing for a Douyin web endpoint, returning (signed_url, headers).

    base_endpoint example: 'https://www.douyin.com/aweme/v1/web/aweme/post/'
    params        example: {'sec_user_id': ..., 'count': 18, 'max_cursor': 0}
    """
    from f2.apps.douyin.utils import ABogusManager, TokenManager

    # ② msToken: generated dynamically (gen_real fetches a real token over the network / gen_false is a pure local fallback)
    ms_token = TokenManager.gen_real_msToken()
    params = {**params, "msToken": ms_token}

    # ③ a_bogus: sign the params including msToken together, F2 returns the full URL with a_bogus filled in
    signed_url = ABogusManager.model_2_endpoint(UA, base_endpoint, params)

    # ③ ttwid + cookie assembly
    ttwid = TokenManager.gen_ttwid()
    headers = {
        "User-Agent": UA,
        "Referer": "https://www.douyin.com/",
        "Cookie": f"{cookie}; ttwid={ttwid}; msToken={ms_token}",
    }
    return signed_url, headers


def fetch_with_ja3(url: str, headers: dict):
    """⑤ Use curl_cffi to make the request: JA3 impersonates Chrome (httpx's JA3 will be exposed, see docs/tls-fingerprint.md)."""
    from curl_cffi import requests
    return requests.get(url, headers=headers, impersonate="chrome", timeout=15)


def demo(cookie: str, share_url: str):
    """End-to-end demo (requires your own cookie + already pip install f2 curl_cffi; please run it manually)."""
    sec_uid = resolve_sec_user_id(share_url)                          # ①
    base = "https://www.douyin.com/aweme/v1/web/aweme/post/"
    params = {"sec_user_id": sec_uid, "count": 18, "max_cursor": 0}
    url, headers = build_signed_request(base, params, cookie)          # ②③④
    resp = fetch_with_ja3(url, headers)                                # ⑤
    return resp


if __name__ == "__main__":
    print(__doc__)
    print(">> This is a reference template. Please first `pip install f2 curl_cffi`, prepare your own cookie,")
    print(">> and after checking the API against the latest F2 docs, manually call demo(cookie, share_url).")
