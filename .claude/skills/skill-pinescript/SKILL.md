---
name: skill-pinescript
description: Build, fix, or verify TradingView Pine Script indicators and strategies. Covers writing a clean .pine file, the alert-message contract that downstream software reads, and the hard-won authoring rules (version pinning, drawing caps, build-both-behind-an-input, delivery format). Use when writing or debugging Pine Script, porting an indicator/strategy to Pine, fixing a compile error, or designing a strategy's alert payload.
---

# Pine Script + Alert Contracts

> **Personal skill** — written for this project. Its requirements are part of
> the build, and folding lessons back into it is encouraged.

Writes the TradingView strategy that fires this project's alerts, and pins the
alert-message contract the receiver later parses.

## Local adaptations (this project)

### Bare invocation

**With no arguments, `/skill-pinescript` builds this project's strategy to the
spec below, start to finish — no menu, no clarifying questions, no audit of an
existing script.**

- **If the strategy does not exist yet** — write it from scratch, exactly as
  specified below.
- **If it already exists** — update it in place so it satisfies every rule as
  this skill currently reads. Edit what's there; never write a parallel second
  script. Report what changed and what was already correct.

Typed arguments hand over to the general guidance below instead (fix a compile
error, port an indicator).

Treat this section as the complete specification — the user will type only the
slash command and pass no requirements.

### What to build (the full requirement set)

Write one TradingView **strategy** in Pine Script that says when to buy and when to sell.

- **Use the current version of Pine Script** — check what that actually is rather than
  assuming; a stale version marker dates the whole build. Show that version on the chart
  (the strategy's name is the cheap place) so it's obvious what it was written against.
- **Use a well-regarded indicator with a strong reputation among traders.** You pick it;
  in the reply, name it and explain in a sentence or two why it is well thought of (who uses
  it, what it is known for). Don't invent something novel.
- **Timeframes**: it runs on a **30-minute chart**, but must also work on a **1-minute chart
  and signal every few minutes there**, so it can be tested without waiting hours for a
  signal. Expose a **sensitivity setting** ("how twitchy it is"), adjustable from the chart's
  settings, so the same script can be loosened for the fast test and tightened for the
  30-minute chart.
- **Draw the indicator** on the chart, and **label every buy and sell on the exact bar it
  happened — buys BELOW the bar, sells ABOVE it.**
- **Plain shares, normal US stock, paper account.** No options, no crypto, no futures. Size
  in whole shares.
- **Buy to enter, sell to exit by default**, plus an input to **reverse the direction** (bet
  the other way).
- **Output: one file the user can paste into TradingView**, plus short plain-English
  instructions for getting it onto a chart and setting up the alert.

### The alert message contract (the part that matters most)

The alerts are read by **other software, not a human**. So:

- **Exactly four labelled values and nothing else**: which stock, buy or sell, how many
  shares, and a **password/token the user chooses**. Machine-readable format (JSON is the
  natural choice) — the same four keys every time, never prose.
- The **password field starts out empty**.
- **Side and share count reflect what the strategy is actually holding** — not a number typed
  in somewhere else. If it closes out or flips direction, the message must say so correctly.
- **Every alert carries real values** — the actual symbol, side and quantity at the moment it
  fires. Anything that fills in only under exactly the right alert settings is not good enough:
  when it fails to fill in, a blank goes out where the number should be, and whatever reads the
  alert acts on a broken instruction with nothing looking wrong.
- **Say exactly what to choose in TradingView's alert dialog** so the message goes out as
  written. Pick the wrong option there and the alerts look fine but carry nothing usable, so
  spell the choices out in the reply rather than assuming they're obvious.

---

## Getting it right

These are the things that bite a Pine script in practice, and most of them look
fine in review.

### Writing / fixing the script

- **Version mismatch is the single most common compile failure**; mangled indentation (e.g.
  code pasted through a chat renderer) is the second. Check those two before anything else.
- **Cap drawing objects** in the declaration: `max_lines_count`, `max_labels_count`,
  `max_boxes_count` (the default ~50 silently drops the oldest).
- **Comment generously in plain English** when the reader is non-technical — they read the
  source.
- Structure as a `strategy` (not `indicator`) when Strategy Tester results or position-derived
  alerts are wanted — position-derived alert values require `strategy`.
- **Label wording is the user's decision.** If the spec wrote label text, that wording is the
  default.
- **When two conventions are both defensible, build BOTH behind an input — don't pick for the
  user.** Where an entry anchors, what confirms a setup, how strict a threshold ships:
  implement both behaviors, default to whatever the spec shows, and expose the choice as one
  dropdown or number. Mind the semantics, not just the level — switching a mode can also
  change what CONFIRMS and what INVALIDATES a setup, so wire each mode's full state machine
  and verify the non-default mode actually changes the chart's markings.

### Verifying — before claiming success

**Pine Script cannot be trusted from code review alone.** The real test is that it compiles
and renders correctly on TradingView itself, so never call a script "working" because "I saw
lines" — verify the placement and the arithmetic.

- **Compile is the bar.** Nothing counts until the script compiles in the Pine Editor and adds
  to a chart. Re-read the source for v6 syntax (no v5 idioms), balanced parentheses, and
  consistent indentation before handing it over.
- **Check the marks are on the RIGHT bars** — zoom into the window with the highest density of
  the script's marks; a blank window verifies nothing.
- **Tie marks to arithmetic** when a signal is questioned: print the bar's OHLC and each
  condition with its threshold, and say which candidates were REJECTED and by what number.
  "Why is there a mark here and not there" is answered in numbers.
- **Sanity-check signal frequency on the demo timeframe.** If the requirement is "signals every
  few minutes on a 1-minute chart," the default sensitivity must actually produce that — a
  strategy that fires twice a day fails the demo even though it compiles.

### Delivery

Deliver the finished source (the user owns it).

**Attach the script as `.txt`, never only as `.pine`.** Chat and mobile preview apps render an
unfamiliar extension (`.pine`, `.mq5`, `.ts`) as a BLANK page — the reader concludes the file
is broken. Emit the `.pine` and a byte-identical `.txt` from the same source string so the
copy can never go stale, and say that it is the exact script with only the file type changed.
Both live in this project's `pinescript/` folder.

# END
