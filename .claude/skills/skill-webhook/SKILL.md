---
name: skill-webhook
description: Build this project's inbound webhook receiver — the endpoint that takes TradingView alerts, validates them, authenticates them, and records every one. Use when the alert receiver needs building, fixing, or extending.
---

# Webhook Receivers

> **Personal skill** — written for this project. Its requirements are part of
> the build, and folding lessons back into it is encouraged.

Add the inbound endpoint that lets an outside service push signals into this app. Covers the address, the checks each alert must pass, the optional shared secret, and the audit
trail every alert lands in.

## Local adaptations (this project)

### Bare invocation

**With no arguments, `/skill-webhook` builds or updates this project's receiver
to the spec below — it does not audit, and does not stop at a proposal.**

- **If the receiver does not exist yet** — build it from scratch, exactly as
  specified in "What to build" below.
- **If it already exists** — update it in place so it satisfies every rule as
  this skill currently reads, including any rule added since the receiver was
  written. Edit what's there; never rebuild from scratch, never create a
  parallel second receiver, never duplicate a route, parser, or log helper that
  already exists. Leave working behavior alone and change only what the current
  rules require. Report what changed and what was already correct.

Typed arguments change that: `audit` reports on the existing receiver instead of
changing it, `remove` takes the receiver out. Empty is never an audit here.

Treat this section as the complete specification — the user will type only the
slash command and pass no requirements.

### The stack here

This is a lightweight single-user **Flask** build with **no database** —
adapt the general guidance accordingly:
- Plain Flask: routes register with `@app.route` directly (no Dash, no
  `app.server` indirection, no blueprints needed at this size).
- **Every alert is logged to a file** — that file IS the audit trail. This
  project has no database and doesn't need one.
- One route only (`POST /webhook`, TradingView shape) plus the `GET /`
  status page; no payment or broker callback receivers.
- The shared-secret token is OPTIONAL (enforced only when the token is
  set) — URL secrecy is the primary safety measure at this tier.

### Configuration: environment variables only — no settings file

**Every setting comes from the environment.** Not from a JSON file, not
from any other file in the project.

- Secrets from the environment: the webhook token, and anything else
  secret. Never in the repository.
- Ordinary tunables from the environment too: how long to ignore a
  repeated alert, which actions are allowed, the log file name.
- **Sensible defaults in code** for anything unset, so the app runs with
  nothing configured.
- **Ship a committed example listing every variable name the app reads**,
  with placeholder values, so anyone else knows what to fill in.

**Why no settings file — this is the part that bites people.** Once the app
is deployed to a cloud host, the files on that host are whatever was last
published from the repository. They are effectively frozen: the app cannot
rewrite them (containers are ephemeral — an edit vanishes on the next
restart or redeploy), and the owner cannot edit them from the host's
dashboard. A "settings file" therefore becomes a file you must edit, commit,
and redeploy to change, which is not configuration at all. Environment
variables are the one thing a host lets the owner edit without republishing.
Reach for a config file only for values that genuinely ship WITH the code
and never vary per deployment.

### What to build (the spec)

A small web server whose whole job is receiving TradingView alerts.

- Written in Python, built with a widely used web **framework** — Flask is
  a good pick. (Framework, not server: the production web *server*,
  gunicorn, is a separate concern handled at deployment. Do not conflate
  the two terms.)
- Give it a dedicated web address where TradingView can send alerts.
- Tell the user what that address is when you're done.
- The alerts come from the Pine strategy already written in this project —
  match what it sends exactly. Read the `.pine` file's alert message and
  parse that shape; don't invent one.
- Each alert message says four things: which stock (the ticker, like
  SPCX), whether to buy or sell, how many shares, and optionally a token —
  a password the owner chooses.

**Validation checks** — never act on an alert that hasn't passed all of
these:

- Reject it if the message arrives garbled.
- Reject it if the stock is missing.
- Reject it if it says anything besides buy or sell.
- Reject it if the share count isn't a number greater than zero.
- Record exactly what was wrong with anything rejected.

**Authentication:**

- If a token is set, reject any alert that doesn't include the matching
  one — compare it in constant time.
- If no token is set, skip that check entirely; the only protection then is
  that nobody else knows the alert address.

**Audit trail:**

- Write every single alert into a log file, with timestamps.
- Write what happened to it too — accepted, or rejected and why.
- No database in this project; the log file is the record.

**Scope limit:**

- Do NOT connect to the broker in this step. This only receives and
  records.

---

## Getting it right

These are the things that bite a receiver in the real world, and none of them
show up in a hand-built test.

- **Validate the fields you USE, and ignore unknown extras.** TradingView
  attaches its own metadata beyond whatever message the user configured. A
  validator that rejects anything unexpected passes every test you write by
  hand, then refuses the first real alert. Check what you need; let the rest by.
- **Test with the real sender, not just your own requests.** A payload you
  constructed proves your parser reads your own format. Only a live alert
  proves it reads TradingView's.
- **The address is the real secret.** An unguessable URL is the primary
  protection, so treat it like a password — never in a screenshot, never in a
  doc, rotate it if it leaks. The token is defence on top of that, not instead
  of it.
- **A rejected alert must say why, in the log.** "Rejected" alone is useless at
  3am; the reason is the entire value of the audit trail.

# END
