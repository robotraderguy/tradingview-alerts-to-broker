---
name: skill-end
description: Close a session cleanly — the bookend to /skill-init. Folds anything learned back into the skills, checks no secret is exposed, clears away scratch files, reports what is uncommitted, and prints a short wrap-up. Use when the user says they're done for now, or invokes /skill-end.
---

# End a Session

> **Personal skill** — written for this project. Its requirements are part of
> the build, and folding lessons back into it is encouraged.

Closes a session so nothing learned is lost and nothing unsafe is left behind.
`/skill-init` loads the context at the start; this puts it away at the end.

## Local adaptations (this project)

### Bare invocation

**With no arguments, `/skill-end` runs the steps below in order and prints the
wrap-up.** Stopping a session with the build half-finished is completely normal
and is not a problem to warn about.

### This skill CLOSES work — it must not open more

The point of a wrap-up is to end the session, not to hand the user a list of
chores or start a project of its own. So:

- **Never start building something here.** Not a test suite, not a README, not a
  missing feature, not a refactor. If this skill notices a gap, it *names* it in
  one line and stops.
- **Fix only what is genuinely trivial** and belongs to work already done — a
  scratch file to delete, a lesson to write down. Anything larger is reported,
  not undertaken.
- **Don't manufacture follow-ups.** A build that ended where the user stopped is
  finished for today. Only mention what actually matters: something unsafe,
  something half-connected, or something they explicitly asked to be reminded of.

### Step 1: Fold this session's lessons back into the skills

This is the step that makes the next build better, and it's the reason the skills
are editable at all. Look back over the session for anything that taught a
reusable lesson — a spec that turned out to be ambiguous, a gotcha that cost
time, a correction the user had to make twice.

For each one:

1. Find the skill that owns that ground (`.claude/skills/`) and add the lesson
   there — as a **requirement** if it's binding, or under **"Getting it right"**
   if it's advice.
2. Write it as a standing rule, not a story. Present tense, no dates, no
   "this session we found…". The skill is instructions; the incident is not.
3. **Only personal skills** — the ones marked `> **Personal skill**`. Vendor
   skills stay byte-identical, as always.

If a lesson has no natural home, say so rather than inventing a new skill for a
one-liner.

### Step 2: Check nothing secret is exposed

Cheap, and the one thing that genuinely can't wait:

- The real `.env` is untracked and ignored.
- No token, account id, or key was written into a tracked file this session.
- Nothing secret is sitting in a file that's about to be pushed.

If something is exposed, say so plainly — it needs removing and rotating.

### Step 3: Clear away scratch files

Anything created as scaffolding this session — one-off scripts, debug dumps,
`tmp_*` / `*.bak` files — should not outlive it. Delete what is unambiguously
scratch and this session's. When unsure whether a file is scratch or real work,
**leave it and mention it** rather than deleting it.

### Step 4: Check tests — only if this project has any

**Check first whether a test suite exists at all.** This build does not ship
with one, so the normal answer is that there's nothing to run:

- **No suite** — say so in one line and move on. **Do not create one.** Writing a
  test suite is a build task the user would ask for directly, not something a
  wrap-up decides to start.
- **A suite exists** (the user added one) — **only run it if it hasn't already
  run since the last code change.** A redundant run costs minutes and tells you
  nothing new. If it already ran after the last edit, report that result and its
  verdict; run it now only when code changed afterwards, or when nothing in this
  session ran it at all. Either way, if it fails, report the failure — don't
  start fixing it unless the user asks.

Either way this step ends in a sentence, not a project.

### Step 5: Report what's uncommitted — never commit

Find out what has changed in the working tree since the last commit, and
summarize it grouped by theme. Then **stop there**: do not commit, push, stash,
or branch, not even "to be safe". That's
the user's call, exactly as it is during the build. The deliverable is the
summary, not the commit.

### Step 6: Print the wrap-up

Short, and only what's true:

- what got built this session,
- lessons folded into which skills,
- secrets check: clean, or exactly what's exposed,
- scratch files deleted, or flagged as uncertain,
- tests: no suite in this project, or the last result and whether it was already
  current (say when it was from, rather than implying you just ran it),
- uncommitted work, grouped,
- anything only the user can do (a credential, a browser sign-in), each with the
  exact action.

If the user wants this kept for next time, offer to save it as a file — don't
write one unasked, since nothing in this project reads it automatically.

---

## Getting it right

- **A half-finished build is a normal place to stop.** Ending mid-way is not a
  failure state and doesn't need a warning attached. Note where things stopped so
  it's easy to pick up, and leave it there.
- **Don't report a result you didn't see.** If something was still running when
  the session ended, say it was still running — not what you expect it would have
  said.
- **A lesson written as a story stops working.** "We discovered the alert dialog
  needs a specific option" helps nobody on the next build; "choose this option in
  the alert dialog, because otherwise the message goes out empty" is a rule that
  fires when it's needed.
- **The session's context shouldn't carry into the next one.** Once the wrap-up
  is printed, the useful parts live in the skills and in the repo. Tell the user
  they're done and can start fresh — a new session begins at `/skill-init`.

# END
