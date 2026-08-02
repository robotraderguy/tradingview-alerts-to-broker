---
name: skill-deploy-cloud
description: Get this project onto a cloud host with a public, always-on address, and deploy it. Use when the app needs to be reachable from the internet so TradingView can send it alerts.
---

# Cloud Deploy

> **Personal skill** — written for this project. Its requirements are part of
> the build, and folding lessons back into it is encouraged.

Puts the finished app on a public host so TradingView can reach it, and hands
back the address to point alerts at.

## Local adaptations (this project)

### Bare invocation

**With no arguments, `/skill-deploy-cloud` produces the host files AND actually
puts the app live, then hands back the public address.** A run that stops at
generated files has not finished the job.

Typed arguments change that: `audit` reports on what exists, `remove` takes the
host files out.

Treat this section as the complete specification — the user will type only the
slash command and pass no requirements.

### Before it can go live — the user's job, not yours

Three one-time things need a browser, and they belong to the user: **creating the
host account, signing both CLIs in** (the host's and GitHub's), and **authorising
the host to read their GitHub** — that last one is what lets it deploy from a
private repo. Tell them plainly if any of them isn't done, and wait.

**After that, do the rest yourself.** Once those CLIs are signed in, creating the
service, setting the secrets, deploying, and reading back the URL are all things
Render's CLI can do — so don't send the user to its dashboard for any of it, and
don't assume it can't. Check its own help before concluding something needs the
website; if a step really does, name which one and why.

If the service somehow already exists (the user made it by hand, or a previous
run created it), don't create a second one — confirm the existing one from the
terminal, then update it and deploy.

### What has to be true when you're done

- **The app answers at a public HTTPS address, 24/7.** That address is the
  whole point — TradingView POSTs to it at an unpredictable moment, and a host
  that has gone to sleep misses the alert entirely. Reachability is the
  requirement; how you get there is your call.
- **It can reach out as well as be reached.** The broker call goes out over the
  open internet. A host that accepts the alert but can't call the broker places
  no orders.
- **The public address is printed at the end**, including the exact path
  TradingView should target. That string is the deliverable.
- **It runs under a production web server**, not the framework's development
  server. (Gunicorn is the usual pick.)
- **The deployed Python matches the local one.** Check what's actually
  installed rather than assuming, and pin it.
- **Render is the host.** Just Render — don't generate config for other
  platforms, and don't offer them as alternatives.
- **The code lives in a PRIVATE GitHub repo, and the host deploys from it.**
  Create it private and keep it private — this is the user's trading app, not
  something to publish. (The repo the skills were cloned from is a separate,
  public thing; don't confuse the two.) Connecting the host to a private repo is
  why the GitHub authorisation above matters.
- **Create that repo with the GitHub CLI, from the terminal.** It's installed
  already, so there's no reason to send the user to the website — a browser
  detour mid-run is exactly what the manual step above exists to avoid. Signing
  that CLI in is a one-time thing the user does themselves; if it isn't signed in
  yet, say so and wait rather than working around it. Tell them the repo name
  you're using.
- **Work out what the app actually reads — don't trust a list, including this
  one.** Search the finished code for every environment variable it looks up.
  The build may well have introduced settings beyond the original three
  (`TRADIER_TOKEN`, `TRADIER_ACCOUNT_ID`, `WEBHOOK_TOKEN`), and one that exists
  locally but was never set on the host is a failure that only shows up at
  runtime, usually as behaviour nobody can explain. Reconcile three things:
  what the code reads, what the local environment file defines, and what the
  host has.
  - **Report any mismatch before deploying** — a variable the code reads that
    nothing supplies, or one supplied that nothing reads.
  - **Bring `.env.example` back in line** if the build added settings, so it
    still describes what this app needs. It's the only guide anyone else gets.
- **Set them on Render yourself, from the terminal.** Use Render's CLI rather
  than making the user paste anything into a web form — fewer steps, and it
  keeps values out of a browser window.
  - The broker credentials already exist in the user's local environment file.
    Read them from there; don't ask them to type them again.
  - Settings that aren't secret (a window length, a mode flag) still have to be
    set — just treat them normally rather than protecting them.
  - **Generate `WEBHOOK_TOKEN` yourself** — long, random, from a source meant
    for secrets rather than something you invent. Set it on the host AND write
    it into the user's local environment file, because they have to paste that
    same value into the TradingView alert for the two ends to match. Tell them
    where to find it; don't make them hunt.
  - **Don't put secret values on screen** — not in output, not in a log, and
    not typed as literals into a command. Pass them by referencing the variables
    they're already stored in, so the command shows a name and the shell
    supplies the value. Confirm by naming which variables are set, never by
    showing what's in them. The token still has to reach the user, but through
    the file, not the terminal.
- **Secrets never get committed.** Config files may name these variables; they
  must never contain the values.
- **Explain each file you generated, in plain English**, at the end.

### Two hard stops before anything is pushed or deployed

This puts a **live public endpoint** on the internet, which is hard to walk
back. Both conditions must hold. If either fails, **STOP and tell the user** —
don't fix it and carry on.

1. **No secret in anything about to be tracked.** Confirm the ignore rules
   cover the environment file, and check the staged content for a real token or
   account value — not just the names. If one is there, stop; it has to be
   removed and rotated first. The repo being private is not a reason to relax
   here: git history is forever, the host can read the repo, and a repo that is
   private today can be made public by one click later.
2. **The endpoint is backed by the paper account.** This will not open a public
   order endpoint onto real money. If the project is ever repointed at a live
   account, deploying needs the shared secret made mandatory and a separate,
   explicit go-ahead — not this command.

These gates are what make an unattended deploy safe to run. They are not
optional, and not removable later "to reduce friction".

### Verify the deployed thing actually works

A live URL is not a working product. When it's up, **offer** to send one test
alert to the deployed address — ask first, exactly as the broker step does, and
use a stock not used in an earlier test — then confirm all three:

1. the alert was received and recorded,
2. an order was actually placed at the broker,
3. both are visible on the pages.

---

## Getting it right

These are the things that bite a deploy, and none of them are visible from a
green build log.

- **A URL that answers is not a deploy that works.** The build succeeding, the
  service showing "live", and the home page loading all prove the host is
  serving something. None of them prove an alert becomes an order.
- **If the alert records but no order appears, the pieces were never
  connected.** The receiver and the broker module can each work perfectly and
  still not be joined to each other. Say so plainly and fix it; do not report a
  successful deploy. This is the last point where that gap can be caught before
  the build is handed over as finished.
- **Check the host's plan terms rather than trusting anything written here** —
  they change, and which plan this runs on decides whether the app works at all.
  The thing to look for: **a plan that puts the service to sleep when nothing has
  called it for a while.** TradingView sends an alert once and does not retry, so
  a sleeping service either refuses it outright or wakes up and answers a minute
  late — by which point the trade is gone. That's fine for a demo someone is
  actively poking at, and useless for anything real. If the honest answer is that
  the free plan won't do, say so and name what the cheapest plan that will costs.
- **A variable that exists locally and not on the host fails at runtime, not at
  deploy.** It usually surfaces as behaviour nobody can explain rather than as an
  error, which is why the reconciliation above is worth doing properly.

# END
