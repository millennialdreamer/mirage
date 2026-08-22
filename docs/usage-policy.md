# Usage Policy and Ethical Boundaries

Mirage is a suite of **anti-detection hardening tools + security methodology**, not a traffic-farming / black-market tool. This document defines its usage boundaries—both as constraints on users and as the precondition for this project's long-term survival in the open-source community.

## ✅ Allowed Use

- Learning the **technical principles** of crawler anti-detection and risk-control evasion
- Running compliant scraping / interaction **tests** on **your own alt accounts**
- Academic research, security research, and personal-project data collection (within the scope allowed by platform terms)

## ❌ Explicitly Prohibited

- **Commercial traffic farming / follower farming / like farming / comment manipulation**—Mirage's interaction engine is a "human-like restraint assistant", not a bulk marketing machine
- **Operating main accounts / production accounts / other people's accounts**—use only disposable alt accounts
- **Breaking CAPTCHAs / bypassing login authentication**—stop immediately when encountering a CAPTCHA, never fight human verification
- **Bulk account warming/selling, commercializing account matrices**
- **Any use that violates the target platform's terms of service or local laws**

## 🛡️ Built-in Guardrails (Safe by Default)

| Guardrail | Description |
|------|------|
| `dry_run` on by default | The interaction engine only demonstrates and does not actually click by default; you must explicitly set `dry_run=False` for real interactions |
| Conservative quotas + minimum intervals | Daily caps are more conservative than manual human behavior, eliminating instant likes / overuse |
| Automatic circuit breaker on risk control | Immediately stops when CAPTCHA / rate limiting / anomalies are detected; no bypassing, no forcing through |
| AI never runs it for you | Interactions have real external consequences and must be initiated by you personally on an alt account |

## ⚖️ User Responsibility

- The **legality** of scraped data and compliance with **platform terms and robots rules** are the user's own responsibility
- Control frequency reasonably, respect the target platform and other users
- All consequences arising from use of this tool are borne by the user

## Why So Restrained?

The essence of "human-like" behavior at the behavior layer is **respecting the platform and using it gently, like a real person**, not attacking. The more restrained you are, the more sustainable it is—both respect for the platform and protection for your account. Use the tool for learning and research, and it can help you for a long time; use it for traffic farming or black-market operations, and sooner or later the account gets banned, and this project will be reported and taken down.

---

> In short: Mirage helps your automation be "more human and gentler", not help you "farm faster". Please use it well.