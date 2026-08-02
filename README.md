<div align="center">

<a href="https://www.youtube.com/@RoboTraderGuy"><img src="docs/robotraderguy.png" alt="RoboTraderGuy — build trading bots with AI" width="540"></a>

# 📡 TradingView Alerts → Broker Orders

**A validated, passphrase-guarded, repeat-protected bridge from TradingView alert webhooks to Tradier sandbox (paper)
orders — built entirely with AI.**

![Python](https://img.shields.io/badge/Python-3.13-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.1-000000?logo=flask&logoColor=white)
![Tradier](https://img.shields.io/badge/Broker-Tradier%20Sandbox-6f42c1)
![Render](https://img.shields.io/badge/Deploy-Render-46E3B7)
![Built With](https://img.shields.io/badge/Built%20With-Claude%20Code-cc785c)
![License](https://img.shields.io/badge/License-MIT-green)

<!-- PLACEHOLDER: swap the channel URL below for the direct video URL once the video is published. -->
🎬 **Watch this get built:** **[▶️ YouTube — video coming soon](https://www.youtube.com/@RoboTraderGuy)** — every line
written by AI, directed on camera.

</div>

---

## 📋 Table of Contents

- [📋 Overview](#-overview)
- [🌿 Which branch? (`start` vs `main`)](#-which-branch-start-vs-main)
- [🏗️ Architecture](#%EF%B8%8F-architecture)
- [🚀 Quick Start](#-quick-start)
- [⚙️ Configuration](#%EF%B8%8F-configuration)
- [🔌 Webhook API](#-webhook-api)
- [📊 Dashboard Pages](#-dashboard-pages)
- [📈 The TradingView Strategy](#-the-tradingview-strategy)
- [🧩 The Skills](#-the-skills)
- [🧱 What It Does / Doesn't Do](#-what-it-does--doesnt-do)
- [☁️ Deployment](#%EF%B8%8F-deployment)
- [👤 Author & Contact](#-author--contact)
- [⚠️ Disclaimer](#%EF%B8%8F-disclaimer)
- [📄 License](#-license)

---

## 📋 Overview

If you trade off TradingView indicators, the alert fires — and then it's you, hand-entering the order minutes after the level is gone.

This project closes that gap. A Flask app receives TradingView alert JSON, checks it, and places the matching market
order on a Tradier **sandbox** (paper) account. A five-page read-only dashboard shows what happened.

Every line of code was written by Claude Code, directed by short plain-English instructions that invoke the reusable
**skills** in [`.claude/skills/`](.claude/skills/). The human contribution is the direction: what to validate, what
must never fail silently, and where the scope ends.

> **Re-running these commands produces a slightly different build — and that's the point, not a flaw.** AI is
> non-deterministic, so no two runs are byte-identical. That is exactly why the skill matters more than any single
> output: you're learning to *direct* a build, not copy one frozen answer. The requirements are pinned in the skills,
> so every run lands on the same working app — just assembled its own way. This branch is one working result —
> **build spec: model claude-opus-5 · reasoning effort high · date 2026-07-26** — and the closer your model and
> effort match, the closer your build lands to it.

---

## 🌿 Which branch? (`start` vs `main`)

This repo has two branches, for two different goals. Ask Claude Code to clone whichever fits — you don't run git yourself.

| | `start` — **build it yourself** | `main` — **one finished build** |
|---|---|---|
| **What's in it** | The skills (the full spec), the machine bootstrap (`install/`), `.env.example`, and a README. **No app code.** | The complete working app: `webhook_app.py`, `tradier.py`, templates, the strategy, the deploy blueprint. |
| **Use it to** | *Reproduce* the build — run the skills in order and watch the app get generated in front of you. This is the teaching path. | *Run or deploy* the app as-is. Also a build to compare your own against — one that works, not the right answer. |
| **Who it's for** | Anyone following along, learning to direct the AI. | Anyone who wants the result, or a working baseline to modify. |

> 🧭 **This branch is not the gold standard.** It's one build that works — what came out of one session, on one day,
> from one model. Not a reference answer, and not a grading key. If your build satisfies the requirements and runs, it
> is exactly as valid, and it may well be better. The **requirements** are the standard.

---

## 🏗️ Architecture

```
tradingview-webhooks/
├── webhook_app.py        # The application: creates the Flask app, receives alerts, serves the 5 pages
├── config.py             # Every setting read from the environment, in one place
├── tradier.py            # Tradier sandbox module (orders out; account, orders and positions back)
├── templates/            # base.html (shared nav) + accounts / alerts / orders / positions / settings
├── static/dashboard.css  # Dashboard styling — dark theme, one :root block of CSS custom properties
├── pinescript/           # supertrend_webhook_strategy.pine (+ .txt copy) — the strategy that fires the alerts
├── install/              # The machine bootstrap (bootstrap.bat / .ps1 / .sh / -linux.sh) — audited before it runs
├── .claude/skills/       # The skills that DROVE the build — personal skills carry the spec, vendor skills stay pristine
│   ├── skill-init/  ├── skill-install/  ├── skill-pinescript/  ├── skill-webhook/
│   ├── skill-broker-api/  ├── skill-dashboard/  ├── skill-deploy-cloud/  ├── skill-end/  (personal)
│   ├── skill-frontend-design/  ├── skill-creator/  (vendor — unmodified)
├── .env.example          # Every variable the app reads, with placeholder values
├── requirements.txt      # Flask, python-dotenv, requests, gunicorn
├── render.yaml           # The deploy blueprint for the host
└── .python-version       # Pinned interpreter (3.13.14)
```

<details>
<summary><b>Request flow</b></summary>

```
TradingView alert ──POST──▶ /webhook   (the path is configurable)
                              │ 1. body parses as JSON?              → 400 with the reason
                              │ 2. ticker / action / quantity valid? → 400 with the exact reason
                              │ 3. passphrase matches?               → 400 (constant-time compare)
                              │ 4. identical alert within 5s?        → 400 (a re-fire is not a second position)
                              ▼
                        tradier.place_order ──▶ Tradier sandbox account
                              │ success → 200 {"status": "accepted", "order_id", "order_status", ...}
                              └ refusal → 502 {"status": "order_failed", "order_error": "<broker's words>", ...}
```

Every one of those outcomes — accepted or rejected — is written to the log as a single line, with its reason.

</details>

<details>
<summary><b>Why two modules, and no database</b></summary>

The alert receiver and the dashboard live together in `webhook_app.py`, because they are the same web app. Everything
that talks to the broker lives in `tradier.py` beside it, so the broker's quirks stay in one place.

There is no database. The log file is the audit trail, and the Alerts page is built by reading it back. One user and
one stream of alerts is not a database problem.

</details>

---

## 🚀 Quick Start

### 📋 The one thing you paste

Everything else in this build is a slash command, but the repo has to reach
your machine before any skill can run — skills live *inside* it. So this is the
only paste, and it is the same text as the one in the video description:

```text
Set this folder up to build along with the video.

1. Check whether git is installed, and install it if it isn't. Tell me what
   you installed.
2. Clone the `start` branch of
   https://github.com/robotraderguy/tradingview-alerts-to-broker INTO THIS
   FOLDER - `.claude/` and `install/` must end up directly here, NOT inside a
   new subfolder. If a subfolder gets created anyway, move the contents up and
   remove it.

Then stop. Don't run any of the skills you find - I invoke those myself, one
at a time. Don't build anything yet and don't plan the build.
```

> The "INTO THIS FOLDER" wording matters. If the files land one level down, no
> skill loads — and no skill can diagnose that, because the skills are exactly
> what is missing.


**You don't run build commands yourself — you install one tool, then direct the AI.** That is the whole point: the
code here was written by Claude Code, and you reproduce it the same way.

1. **Install the two tools by hand** — [VS Code](https://code.visualstudio.com/download) and
   [Claude Code](https://docs.anthropic.com/en/docs/claude-code/setup). Everything after that installs itself.
2. **Get your accounts** (browser, one-time): Tradier **sandbox** credentials, and a **Render** account
   with GitHub authorized.
3. **Open Claude Code in an empty folder and direct it.** Clone the `start` branch, then run the skills
   in order — Claude installs the dependencies, builds each piece, and deploys for you.
4. **Point a TradingView alert at your deployed URL** — the deploy step prints it at the end.

<details>
<summary><b>Running it on your own machine</b></summary>

Ask Claude Code to install the dependencies and start the app. It reads a local `.env` if there is one, and falls back
to working defaults for everything except the broker credentials.

The app listens on port 5000 unless `PORT` says otherwise, and the dashboard's front door is `/`.

</details>

<details>
<summary><b>The alert message</b></summary>

The strategy fills this in for you. To fire one by hand, this is the shape:

```json
{"ticker": "AAPL", "action": "buy", "quantity": 1, "passphrase": "your_secret_here"}
```

`token` is accepted as an alias for `passphrase`, since that is the name `.env.example` uses.

</details>

---

## ⚙️ Configuration

Every setting comes from the environment, and there is no settings file. A cloud host freezes the files it deployed
and rebuilds the container on each restart, so a file the app wrote would vanish. Environment variables are the one
thing you can change without republishing.

Copy `.env.example` to `.env` and fill it in. Everything except the credentials has a working default.

| Variable | Default | Purpose |
|---|---|---|
| `TRADIER_TOKEN` | — | Tradier **sandbox** access token |
| `TRADIER_ACCOUNT_ID` | — | Tradier **sandbox** account id |
| `TRADIER_TIMEOUT_SECONDS` | `8` | How long to wait on the broker before giving up |
| `WEBHOOK_TOKEN` | *(unset)* | **Optional** shared secret; when set, every alert must carry a matching passphrase |
| `WEBHOOK_PATH` | `/webhook` | The address alerts are posted to — set it to something long and random |
| `ALERT_LOG_FILE` | `webhook.log` | The audit trail, and the source of the Alerts page |
| `ALLOWED_ACTIONS` | `buy,sell` | What the strategy is allowed to ask for |
| `DUPLICATE_WINDOW_SECONDS` | `5` | An identical alert inside this window is rejected; `0` disables the guard |
| `PORT` | `5000` | The port to listen on |

> 🔒 **The URL is your primary safety measure.** The webhook address is unguessable, so treat it like a password:
> never share it, post it, or leave it visible in a screenshot. Anyone who has it can send orders to your account.
> The passphrase is defence on top of that, not a substitute for it.

---

## 🔌 Webhook API

### `POST /webhook`

The path is whatever `WEBHOOK_PATH` is set to. TradingView does not send a JSON content type, so the body is parsed
directly rather than trusting the header.

| Outcome | Status | Body |
|---|---|---|
| Order placed | `200` | `{"status": "accepted", "order_id", "order_status", ...}` |
| Rejected before the broker | `400` | `{"status": "rejected", "reason": "<exact reason>"}` |
| Broker refused, or unreachable | `502` | `{"status": "order_failed", "order_error": "<broker's own words>", ...}` |

<details>
<summary><b>Validation rules</b></summary>

- **`ticker`** — required and non-empty; upper-cased before use.
- **`action`** — required, and must be one of `ALLOWED_ACTIONS`.
- **`quantity`** — required, numeric, and greater than zero; whole shares.
- **`passphrase`** — required only when `WEBHOOK_TOKEN` is set. Compared in constant time, so a wrong guess cannot be narrowed down by how long the comparison took.
- **Unknown extra fields are ignored, not rejected.** TradingView attaches its own metadata, and a validator that refuses anything unexpected passes every hand-written test and then turns away the first real alert.

Each rejection names what was wrong. "Rejected" on its own is useless at 3am; the reason is the entire point of keeping the log.

</details>

<details>
<summary><b>The repeat guard</b></summary>

TradingView can re-fire the same alert, and a duplicate order is a real position that has to be unwound. An identical
ticker, action and quantity arriving inside `DUPLICATE_WINDOW_SECONDS` is rejected.

The guard remembers recent alerts in memory, which is why the app runs a single worker in production. With two
workers, a repeat could land on the one that has not seen it.

</details>

---

## 📊 Dashboard Pages

Five read-only pages, listed alphabetically in the top menu exactly as they appear here. Nothing is clickable and
nothing can be edited — this is a window onto the app, not a control panel.

| Page | Shows |
|---|---|
| **Accounts** | Account number, status, equity, cash, buying power, currency |
| **Alerts** | One row per alert received, newest first — time, ticker, side, quantity, and what happened to it |
| **Orders** | Recent orders, newest first — time, ticker, side, quantity, type, status, fill price |
| **Positions** | Current holdings — ticker, shares, cost, entry time |
| **Settings** | A read-only summary of the configuration, including whether each secret is set |

The front door (`/`) lands on Alerts.

<details>
<summary><b>Two rules every page holds to</b></summary>

**Every page always loads.** If the broker cannot be reached, or the log file is missing, the page says so in words.
No stack trace, no blank screen, whatever the broker or the filesystem does.

**No secret value is ever rendered.** The Settings page reports whether a credential is set, never what it is.

</details>

<details>
<summary><b>Static by design</b></summary>

Each page renders its data fresh on load, and you reload for new data. There is no JavaScript, no polling, and no auto-refresh.

A page that only displays data does not need a client runtime, so the whole frontend stays plain HTML and one CSS file.

</details>

---

## 📈 The TradingView Strategy

[`pinescript/supertrend_webhook_strategy.pine`](pinescript/supertrend_webhook_strategy.pine) is a Pine Script v6 **strategy**
built on **Supertrend** — a widely used ATR-based trend follower, popular because it gives one unambiguous line and
one unambiguous flip.

It draws the indicator, labels every entry and exit on the bar it happened (buys below, sells above), and pre-wires
the webhook JSON into its alert messages.

| Input | What it does |
|---|---|
| **Sensitivity** | How twitchy the signal is — loosen it for a fast 1-minute demo, tighten it for the 30-minute chart |
| **Shares** | How many whole shares each alert asks for |
| **Reverse direction** | Bet the other way |
| **Alert password** | The passphrase written into every alert message; starts empty |
| **Show labels / Show line** | Chart display toggles |

A byte-identical `.txt` copy sits beside it, because chat and mobile preview apps render an unfamiliar extension as a
blank page and the reader concludes the file is broken.

> The alert message carries exactly four values — ticker, action, quantity, passphrase — and they reflect what the
> strategy is actually holding at the moment it fires. This is a demo configuration, not trading advice.

---

## 🧩 The Skills

The build was driven by short plain-English instructions that invoke the skills in
[`.claude/skills/`](.claude/skills/). You don't paste a wall of requirements: this project's exact spec already lives
inside each **personal** skill's **"Local adaptations (this project)"** section.

Two skills are **vendor** — a public design skill and the skill-authoring tool. They stay byte-identical to their
downloads, and they are the two without the `Personal skill` note at the top of the file.

| Skill | Kind | Role in the build |
|---|---|---|
| `/skill-init` | personal | **Run FIRST, every session.** Loads what the project is, which branch you're on, and the rules — writes no app code |
| `/skill-install` | personal | **Once per machine.** Audits `install/` for anything malicious and explains it in plain English *before* running it |
| `/skill-pinescript` | personal | The TradingView strategy, and the alert-message contract |
| `/skill-webhook` | personal | The receiver — validation, the optional passphrase check, the repeat guard, the audit trail |
| `/skill-broker-api` | personal | The Tradier sandbox module, **and** the wiring that turns an accepted alert into a real order |
| `/skill-dashboard` + `/skill-frontend-design` | personal + **vendor** | The five pages — the personal skill carries the brief, the vendor skill supplies the look. Named together |
| `/skill-deploy-cloud` | personal | The host blueprint and the deploy, ending in the public URL |
| `/skill-end` | personal | The wrap-up — folds what the session taught back into the skills |
| `/skill-creator` | vendor | The tooling used to author the personal skills; not run during the build |

<details>
<summary><b>Reproduce the build from scratch</b></summary>

The skills carry the *entire* specification, so the app can be rebuilt from the ordered list below and nothing else.

> ⚠️ **Build in a clean folder.** If the finished app is sitting in the working directory, both you and the AI will be
> tempted to consult it — and the skills are written to refuse, because a spec that only produces the app while the
> answer is visible is a broken spec. Build from `start`, get it running, and *then* compare.

**First, the one-time accounts:** Tradier sandbox credentials, and a Render account with GitHub authorized.

Then, in Claude Code. You type each one yourself, and wait for it to finish:

1. `/skill-init`
2. `/skill-install`
3. `/skill-pinescript`
4. `/skill-webhook`
5. `/skill-broker-api`
6. `use /skill-frontend-design to build out /skill-dashboard`
7. `/skill-deploy-cloud`
8. `/skill-end`

Point a TradingView alert at the URL the deploy step prints, and you're live.

</details>

---

## 🧱 What It Does / Doesn't Do

**It does:**

- Receive TradingView alerts at a secret address, and check every field before acting on one.
- Place whole-share market orders on a Tradier **paper** account.
- Record every alert, accepted or rejected, with the reason — one line per alert.
- Pass the broker's refusal back word for word, in the response and in the log.
- Show accounts, alerts, orders, positions and settings on pages that render even when the broker is down.

**It doesn't:**

- Touch real money. The sandbox environment is deliberate and permanent.
- Manage positions, handle partial fills, retry failed orders, or place anything other than a market order.
- Update by itself — you reload the page.
- Support more than one broker, or more than one user.

Those absences are scope, not oversights. Each one is a decision recorded in the skills.

---

## ☁️ Deployment

The app deploys to **Render** from a private GitHub repo, described by [`render.yaml`](render.yaml).

| Setting | Value | Why |
|---|---|---|
| Runtime | Python | `.python-version` pins 3.13.14 |
| Start command | `gunicorn webhook_app:app` | A production web server, not Flask's development one |
| Workers | **1** | The repeat guard lives in memory, and memory is per worker |
| Health check | `/` | The dashboard's front door |
| Plan | **Starter**, not Free | See below |

> ⚠️ **Why not the free plan.** A free service is put to sleep after about 15 minutes with no traffic, and takes
> roughly a minute to wake up. TradingView sends an alert once and never retries, so a sleeping service simply loses
> the signal — the trade is gone before the app is awake to hear about it.

Secrets are set directly on the service, never written into `render.yaml` and never committed. The real `.env` stays out of git entirely.

**Getting your copy into a repo Render can read.** Render deploys from *your* GitHub account, so the code has to be
committed, pushed there, and then read by Render — three accounts' worth of one-time setup:

```bash
# 1. git won't commit until it knows who you are (there is no "git login")
git config --global user.name "Your Name"
git config --global user.email "you@example.com"

# 2. GitHub — the flags skip the four prompts the bare command asks
gh auth login --hostname github.com --git-protocol https --web

# 3. Render — opens the dashboard to authorise the CLI
render login
```

Step 2 also installs `gh` as git's credential helper, so `git push` needs no separate sign-in afterwards. If your
Render account belongs to several workspaces, pick the active one with `render workspace set`.

> ⚠️ The email in step 1 is stamped on every commit and is publicly readable on GitHub. Use GitHub's private
> forwarding address (**Settings → Emails → Keep my email address private**) if you'd rather not publish a personal one.

---

## 👤 Author & Contact

**Tyler** — trading-bot developer (Upwork Top Rated Plus, 100% Job Success). I build automated trading systems for a
living; on [RoboTraderGuy](https://www.youtube.com/@RoboTraderGuy) I build them with AI instead of hand-coding.

- 🌐 Custom software inquiries: [tnttrading.net/contact](https://tnttrading.net/contact)
- 💼 Upwork: [upwork.com/freelancers/robotraderguy](https://www.upwork.com/freelancers/robotraderguy)
- 🔗 LinkedIn: [tyler-potts](https://www.linkedin.com/in/tyler-potts-022b6573/)

---

## ⚠️ Disclaimer

Educational content only — **not financial advice**. Trading involves substantial risk of loss, and past performance
does not guarantee future results.

This project targets **paper trading** on purpose. Automating a strategy does not make it profitable, and a live
deployment needs the risk controls this build deliberately omits.

No sponsorships or affiliations: the brokers, services, and tools used do not compensate me in any way.

---

## 📄 License

MIT — the code from every video on the channel is free to use, modify, and learn from. See [LICENSE](LICENSE).

---

<div align="center">

**Built with ❤️ (and directed AI) by RoboTraderGuy**

*I don't write the code — I direct it.*

</div>
