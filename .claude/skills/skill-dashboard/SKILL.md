---
name: skill-dashboard
description: Build this project's read-only monitoring dashboard — the pages, their fields, the always-loads resilience rule, and the look. Holds the app's UI brief so it can be invoked bare, and composes with a visual-design skill the user names alongside it for the aesthetic direction. Use when building or updating the app's dashboard pages.
---

# Dashboard

> **Personal skill** — written for this project. Its requirements are part of
> the build, and folding lessons back into it is encouraged.

Builds the project's server-rendered monitoring dashboard: a small set of
**read-only** pages that show what the app is doing, resilient enough to
render even when its data sources are down.

**This skill composes with a design skill.** It owns WHAT the dashboard contains
(pages, fields, behavior, resilience); a visual-design skill owns HOW it looks
(typography, layout, the signature element). The user names both in the same
instruction — e.g. `/skill-dashboard` alongside a design skill — and when they
do, this brief supplies the content while the design skill supplies the
aesthetic judgment. If only this one was named, build to this brief and say the
design skill exists; don't reach for it yourself. This skill never edits the
design skill; that skill stays exactly as downloaded.

## Local adaptations (this project)

### Bare invocation

**With no arguments, `/skill-dashboard` builds or updates this project's
dashboard to the spec below — it does not ask for a brief, and does not stop at
a proposal.**

- **If the pages do not exist yet** — build them from scratch, exactly as
  specified below.
- **If they already exist** — update them in place so they satisfy every rule as
  this skill currently reads. Edit what's there; never duplicate a page. Leave
  working behavior alone and change only what the current rules require. Report
  what changed and what was already correct.

Treat this section as the complete specification — the user will type only the
slash command and pass no requirements.

### Stack

Plain **Flask + Jinja**, single user, **no database**, server-rendered. No
Dash, no React, no build step. Data comes from three places only:

- The **Tradier sandbox** API — accounts, orders, positions.
- The local **`webhook.log`** file — the alert history, parsed into rows.
- **Environment variables** — the Settings page (no settings file; all
  config is environment-based).

### Pages

- Five pages: **Accounts, Alerts, Orders, Positions, Settings.**
- Top menu lists them **alphabetically** and highlights the current page.
- The front door (`/`) lands on **Alerts**.
- Everything is **view-only** — nothing to click or edit.

### Static by design — no JavaScript, no auto-refresh

- Each page renders its data fresh on load from Jinja; the viewer reloads for
  new data.
- **Do NOT add** `<meta http-equiv="refresh">`, polling, websockets, or SSE.
- Live updating is beyond the scope of this build. Pages that only display data
  don't need a client runtime, so the whole frontend stays plain HTML and one
  CSS file.

### What each page shows

- **Accounts:** account number, status, equity, cash, buying power, currency.
- **Alerts:** one row per alert received, newest first — time, ticker,
  buy/sell, quantity, and what happened to it (accepted, or rejected with the
  reason). Where an alert became an order, show that, so a row can be followed
  through to the order it produced. **This is a table of alerts, not a view of
  the log file** — the log is where the rows come from, not what the page
  looks like. Same shape as Orders: one row per thing that happened, not one
  row per line written.
- **Orders:** recent orders, newest first — time, ticker, buy/sell, quantity,
  order type, status, fill price.
- **Positions:** current holdings — ticker, shares, cost, entry time.
- **Settings:** read-only summary — practice-mode-only, whether the webhook
  token is set (if not, a reminder to keep the URL secret), allowed actions,
  the duplicate-blocking window, whether broker credentials are filled in, the
  log file name.

### Settings sourcing

- Read every value from the environment (code defaults as fallback).
- **Never render a secret's VALUE** — show only whether it is set.
- If a listed setting doesn't exist in this build yet, say so plainly rather
  than inventing a value.

### Never let a page break

- If the broker can't be reached, the page says so plainly.
- **Every page always loads** — no unhandled exception, no blank screen, no
  stack trace, whatever the broker or log file does.

### Look (hand these constraints to the design skill)

- **Dark theme** — something a trader leaves open on a second monitor, not a
  bare-bones default table.
- **Tradier's signature purple** as the accent, on a near-black background
  with off-white text; brighten the purple until it's readable on the dark
  background (check contrast, don't eyeball).
- Trading conventions: **green only means gains, red only means losses or
  errors** — never decorative.
- Theme colors as CSS custom properties in one `:root` block, so re-theming
  later is a one-place edit.

---

## Getting it right

These are the things that bite a dashboard like this one, and none of them show
up while everything is working.

- **The always-loads rule is invisible until it fails.** Every page renders fine
  with a reachable broker and a populated log; that proves nothing. Check the
  failure states deliberately — wrong credentials, broker unreachable, missing
  log file, and a log file with zero rows — and confirm each page still draws
  with a plain message rather than a stack trace.
- **An empty table is a state, not a bug.** Before any alert has arrived, most of
  these pages have nothing to show. "No alerts yet" reads as working; a blank
  panel or a crash reads as broken.
- **A log file is a source, not a layout.** The temptation is to dump lines onto
  the page because that's the shape the data arrives in. One row per thing that
  happened is what a person can actually scan.
- **Check the contrast, don't trust your eye.** A brand purple that looks fine on
  a bright monitor can be unreadable on a dim one. Measure it against the
  background rather than judging it by eye.
- **Nothing here is worth a client runtime.** If a requirement seems to call for
  live updates, re-read the spec — a reload is the refresh mechanism, and adding
  polling is the easiest way to drift out of scope without noticing.

# END
