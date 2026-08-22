# Interaction Safety Handbook

Mirage's interaction engine can like/follow/collect/comment on Xiaohongshu "like a real person". But **interaction and scraping are completely different in nature** — it has real external consequences (actually liking strangers' posts, actually posting comments), and it is the most sensitive area for risk control. Please read this handbook thoroughly.

## What this is / is not

- **Is**: a human-like, restrained interaction assistant — it gently interacts with content you're interested in like a real person, at a pace slower and more restrained than manual operation.
- **Is not**: a bulk engagement machine or zombie-account matrix tool. Mirage does not crack signatures, bypass CAPTCHAs, or farm zombie accounts.

## Security iron rules (written into the code, not just suggestions)

1. **dry-run is on by default**: by default it only moves the mouse into place and prints "what it would do", **does not actually click**. Real interaction must be explicitly enabled with `dry_run=False` / `--live`.
2. **Only use alt accounts; never touch your main account**. If interaction gets an account in trouble, the whole account is implicated.
3. **Conservative daily caps**: defaults are likes 150 / follows 30 / collects 80 / comments 20 (per day). For new accounts, enable `conservative=True` to cut these to 1/3.
4. **AI will never run live for you**: interaction has real consequences; live operations must be initiated by you personally.

## Risk by action (from high to low)

| Action | Risk | Notes |
|------|------|------|
| **Comment** | 🔴 Highest | Content risk control is strictest: repetition/advertising words/links/@ mentions are most likely to be judged as violations or even lead to a ban. Content must be natural, varied, and relevant to the note. |
| **Follow** | 🟠 High | Frequent follow/unfollow easily triggers throttling; accounts have an overall follow cap. Keep it restrained daily. |
| **Collect/Like** | 🟡 Medium | Relatively safe, but **instant likes and regular intervals are a major taboo** — Mirage avoids this with minimum interval + jitter + dwell first. |

## Pacing recommendations (already built into the ultimate loop)

- **Lots of browsing + little interaction** (`interact_prob` 0.1~0.2, i.e. out of every 10 items viewed, interact at most 1–2 times).
- No instant likes (dwell and read first), random order, natural intervals, occasional zoning out.
- Split daily usage into several sessions; don't hammer continuously; after several days in a row, rest 1–2 days.
- **Don't interact with multiple accounts under the same WiFi** — this is a characteristic Xiaohongshu heavily targets.

## What to do if warned / throttled

1. If the loop detects "CAPTCHA / operation too frequent / account abnormal", it will **automatically trip the circuit breaker and stop**.
2. Don't interact any more that day; let the account rest.
3. Next time switch to `conservative=True` and lower the volume further.
4. Confirm you're using an alt account; if you accidentally used your main account, stop immediately.
5. If you keep getting warnings, rest for a few days; don't push through.

## Honest disclaimer

- **Reduces the probability of being misjudged by risk control; does not guarantee zero bans**. Any automated interaction carries the risk of throttling or account bans; be mentally prepared.
- Interaction has **real external consequences** (actually liking other people's posts, actually posting comments); all consequences are the user's own responsibility.
- Please comply with Xiaohongshu's terms of use, **only operate your own account**, keep frequency reasonable, and do not use it for engagement manipulation, unfair competition, or any prohibited purpose.