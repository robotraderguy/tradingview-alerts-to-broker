---
name: skill-broker-api
description: Build this project's broker module — the single file that places orders on the Tradier paper account and reads the account, orders, and positions back. Use when the broker layer needs building, fixing, or extending, or when adapting this build to a different broker.
---

# Broker API Integration

> **Personal skill** — written for this project. Its requirements are part of
> the build, and folding lessons back into it is encouraged.

Builds the module that places orders on the broker and reads the account back,
and connects the alert receiver to it.

## Local adaptations (this project)

### Bare invocation

**With no arguments, `/skill-broker-api` builds or updates this project's broker
module to the spec below — it does not produce an audit report.**

- **If the broker module does not exist yet** — build it from scratch, exactly as
  specified below.
- **If it already exists** — update it in place so it satisfies every rule as
  this skill currently reads. Edit what's there; never create a parallel second
  broker module, never duplicate a function that already exists. Leave working
  behavior alone and change only what the current rules require. Report what
  changed and what was already correct.

Typed arguments change that: `audit` reports on the existing module instead of
changing it, `remove` takes it out.

Treat this section as the complete specification — the user will type only the
slash command and pass no requirements.

### Scope: one broker, one file

This project talks to **one** broker, so the whole integration is a **single
module at the project root** — not a package, not a registry, not a plugin
system. Supporting more than one broker is beyond the scope of this build, so
don't build an abstraction layer for brokers that aren't here.

### What to build (the spec)

**Where it connects**
- **Tradier**, and specifically its **paper-money environment**. That is
  deliberate and permanent — nothing here may point at a live account.
- The credentials it needs come from the environment, never written into the
  code and never kept in a settings file. Missing credentials must produce a
  clear complaint when an order is attempted — not a crash the moment the module
  is imported.

**What it must be able to do**
- **Place an order**, given a symbol, a direction, and a size. Report back
  enough for the caller to identify the order afterwards and say whether it
  went through.
- **Report the account, the recent orders, and the open positions** when asked.
- **Connect it to the alert path — this step owns that.** The receiver already
  validates and records alerts and then stops; there is nothing calling the
  broker yet. Finish the job here: an accepted alert must actually place its
  order, and what the broker says back — the id, or the refusal in full — gets
  recorded the same way the alert was. A broker module nothing calls is not
  done, however well it works on its own.

**Rules it must never break**
- **Answer fast, or fail fast.** Whatever sends the alert waits only a few
  seconds before giving up, so this module must give up first and say so. A slow
  failure here is worse than a quick one.
- **When the broker refuses an order, pass back exactly what the broker said.**
  Word for word. Never replace it with your own wording, never reduce it to
  "failed", never quietly drop it.
- **A read must never blow up.** If the broker is unreachable, or answers with
  something unexpected, return empty rather than raising. Placing an order may
  fail loudly; reading may not — whatever calls it has to survive a bad day at
  the broker.
- **Don't trust a number just because its name looks right.** A payload can
  carry more than one field that plausibly means "how much money is in here",
  and the wrong one can read as zero while the real figure sits beside it. Check
  what the broker actually returns before deciding which value to use.
- **Every field name must be verified, never guessed.** Take each one from
  documentation, library source, or a real captured response. If one can't be
  verified, call the endpoint and print the raw body before writing code against
  it.

### Sending anything to the broker needs the user's say-so

**Never place an order, cancel one, or send anything else to the broker without
asking the user first.** It's a paper account, not a pretend one: an order shows
up in the account, moves a position, and sits in the history. Don't do it on your
own initiative, and don't treat "it's only paper" as permission.

So when the module is wired up, stop and report:

- what you built, and what you could NOT confirm without touching the broker,
- that a live check is the way to confirm it, and exactly what you'd send,
- then wait. If the user says go, run it and report what came back, including any
  refusal text verbatim.

Until they say yes, describe the module as **written but unverified** — never as
working.

---

## Getting it right

These are the things that bite a broker integration, and none of them show up in
a test written by hand.

- **A guessed field name doesn't fail loudly.** It reads as missing, and the
  damage lands downstream: a fill that's never seen, a position value that
  renders as 0, a status that falls through to "unknown". Because the broker's
  real response usually looks plausible next to the guess, these bugs survive
  review and surface only against a live account. "It looked like the docs" is
  not verification.
- **A refusal can arrive with a success status code.** A broker may answer an unusable order
  with HTTP 200 and an error body, so "did the HTTP call succeed" is not the same question as
  "did the order go through". Decide acceptance on the presence of the order in the response,
  never on the status alone — and don't stamp the status onto the message you pass back when
  it was 200, because "HTTP 200: rejected" reads as nonsense to whoever finds it later. Keep
  the status and the raw body on the recorded result regardless.
- **Collect every number the account payload carries, under its real name, rather than
  the names you expect.** A hand-written list of fields silently omits whatever it didn't
  anticipate, and the omission looks exactly like a zero. Real payloads carry near-duplicate
  names — one reading 0 next to the true figure under a longer name — so also surface WHICH
  field each displayed number came from. A figure nobody can name is a guess.
- **A swallowed rejection is worse than a crash.** The reason the broker gives is
  the most valuable string in the system — the difference between "something went
  wrong" and "this account isn't approved for that symbol". A crash gets fixed; a
  silent failure leaves a position nobody knows is wrong. If you catch an
  exception here, the handler must record what actually happened, including the
  status code and the response body.
- **Importing cleanly is not evidence of anything.** The only real proof is
  sending something to the broker — which is why it needs asking for first.
- **Test the whole path, not the parts.** The check that matters is a test alert
  sent to the endpoint the way TradingView would — not a direct call to the order
  function, which proves only that one piece works. One alert should produce a
  new recorded alert AND a new order, and both should be visible. Then send one
  with a nonsense symbol and confirm the broker's own refusal comes back intact
  rather than disappearing.
- **Use a stock not used in an earlier test.** Repeating a symbol makes the new
  order indistinguishable from the last one, and "is that row from this run?"
  wastes more time than picking a different ticker.

### Where the API facts come from

There is no bundled API reference in this project — get the details from
**Tradier's own documentation** (<https://documentation.tradier.com>), and note
that the paper environment has its own base address, separate from the live one.

**Check whether there's a Python SDK for it too** — an official one, or a
well-maintained community package. Where one exists it's a second verified place
to read field names and behaviour from, and often a better one than prose docs,
because it's the code that actually runs. Whether you use the SDK or call the
API directly is your call.

Docs and SDK are both starting points, not the finish line: where a response
shape matters, confirm it against a real reply from the paper account before
writing code that depends on it.

# END
