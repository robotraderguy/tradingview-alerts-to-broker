---
name: skill-init
description: Load the context for this project at the start of a session — what is being built, how it gets built (short plain-English direction plus the skills in this repo), which branch you are on, and the rules that apply. Use at the start of a new conversation, after cloning the repo, or whenever the session needs re-grounding.
---

# Start a Session

> **Personal skill** — written for this project. Its requirements are part of
> the build, and folding lessons back into it is encouraged.

Run this once at the start of a session, before building anything.

> **Terminology: `main` always means the git branch.** Throughout this skill and
> every other skill in this repo, `main` and `start` in backticks are the two git
> branches and nothing else — never a `main.py` file, never a `main()` function,
> never "the main module". This build has no `main.py` and no `main()`; where a
> file or function is meant, it is named explicitly.

## How it gets built

**Who "you" is — this holds for every skill in this repo, not just this one.**
Throughout the skill library, **"you" means the AI reading it** and **"the user"
means the person driving the build**. This skill runs first and is where that
convention is declared; the other skills rely on it and do not restate it.

- **The user gives short, plain-English direction** — usually just a slash
  command like `/skill-webhook`, sometimes one sentence that names a skill.
- The **skills in `.claude/skills/` carry the specification**. Every page,
  field, validation rule, and failure behavior for this project already lives
  in each personal skill's **"Local adaptations (this project)"** section.
- **You do the work.** The user does not paste requirement walls and does not
  run terminal commands — you clone, install, build, run, and deploy on their
  behalf, and report back what happened.

If the user is writing long requirements prompts, something has gone wrong —
that requirement belongs in a skill, and it is probably already there.

**How every skill in this repo is laid out.** They share one shape, so you always
know where to look:

- A **`> **Personal skill**`** marker under the title, if it is one.
- A **`### Bare invocation`** block saying what the bare slash command does —
  every skill here is designed to be invoked with no arguments.
- **`## Local adaptations (this project)`** — the **requirements**. This section
  is the specification and is binding.
- **`---` then `## Getting it right`** — **advisory**: the gotchas, the things
  that bite in the real world, and how to verify. Read it, apply your judgment;
  it explains and warns rather than specifies.
- **`# END`** as the last line, so a truncated file is obvious.

Requirements live above the rule, advice below it. When the two ever seem to
disagree, the requirement wins. A skill with no gotchas worth stating omits
"Getting it right" rather than padding it — this one does.

The **build** skills state their requirements as a spec to satisfy. The three
**session** skills — this one, `/skill-install`, and `/skill-end` — state theirs
as ordered steps to run instead, since their job is a procedure rather than an
artifact. Same sections, same order.

## Local adaptations (this project)

### Bare invocation

**With no arguments, `/skill-init` runs the steps below in order and stops.** It
loads context and switches branch if needed; it builds nothing and plans nothing.

### Steps

1. **Read `README.md`.** The two branches carry very different ones, and which
   one you are looking at changes what it is good for.

   **On the `start` branch the README is orientation and branding only** — the
   channel, a high-level description of what this build does, and how the build
   is directed. It deliberately carries **no requirements**: no endpoints, no
   status codes, no response shapes, no field names, no constants. That is not an
   oversight to fix, and it is not a gap to fill in — a README documenting those
   things would hand over the answer, and you would end up building to the
   documentation instead of to the spec. **The skills are the specification.
   There is no second source.** Read it for context, then build from the skills.

   On the **`main`** branch (the finished build — see step 2) the README is a
   different document: it documents the finished app in full — architecture,
   endpoints, configuration, deployment — and there it is the correct reference,
   because the app is done and describing it is no longer a spoiler.

   **Writing that full README is beyond the scope of this build.** No skill here
   produces one, and its absence at the end is not a loose end: don't write one
   unprompted, and don't treat the `start` README as a draft to be expanded into
   it. If the user asks for one, that's a normal request — write it then.

2. **Get onto the right branch. This is the one thing this skill acts on** —
   everything else it does is read-and-report. Find out which branch is checked
   out.

   - **`start`** — the launchpad: skills, `install/`, `.env.example`, and **no
     app code**. This is where the app gets built, one skill at a time. Already
     correct; nothing to do.
   - **`main`** — the finished build. **Cloning the repo without asking for a
     branch lands here**, so this is the ordinary starting state, not a mistake
     by the user. Unless they've said they want to run, deploy, or modify the
     finished app, a session that starts here is a *build* session sitting on
     the wrong branch: **switch to `start`** (fetching it first if it isn't on
     this machine yet), then confirm it took and tell them you moved and why.

   **Why act here when the rest of this skill only reports:** building while
   `main` is checked out puts the finished code in the working tree, which is
   exactly the situation the "build from the spec" rule below exists to prevent.
   Leaving the user on `main` doesn't keep them safe — it drops them into the
   one setup where copying the answer is the path of least resistance. A branch
   switch is instant and reversible; the trap isn't.

   If the switch can't be made cleanly — uncommitted changes in the working
   tree, or no `start` on the remote — **stop and report.** Never force it,
   never stash or discard someone's work, never re-clone to get around it.

   If you can't determine a branch at all — no git repository, or a detached
   checkout — say so and stop there. Report what you found and let the user
   decide.

3. **Inventory the skills.** List `.claude/skills/` and read each `SKILL.md`
   frontmatter description so you know what is available and can reach for the
   right one. These are the build mechanism, not background reading.

   **Sort them into personal and vendor by reading, not by guessing.** A
   **personal** skill says so on its own second line — a `> **Personal skill**`
   note directly under the heading. Anything without that note is **vendor**:
   leave it byte-identical (they usually ship a `LICENSE` file, which is a
   second confirmation).

   Do not infer this from anything else. In particular, **"it has a Local
   adaptations section" is not the test** — some personal skills don't have one,
   and that exact inference has already caused personal skills to be mistaken
   for vendor and wrongly treated as untouchable. If a skill carries no marker
   and no LICENSE, say so rather than assuming; treating a personal skill as
   vendor costs a lesson, and editing a vendor skill breaks its upstream
   updates, so when genuinely unsure, treat it as vendor and flag it.

4. **Don't build a plan from scratch — a plan already exists.** Apart from the
   branch switch in step 2, this skill only loads context. It builds nothing.

   There is a definite order to this build. It just isn't yours to work out, and
   it isn't written down here: **the user is holding it**, and reveals it one
   step at a time by invoking the skill for the piece they want next. Each piece
   is built by its own skill. So you are never planning in a vacuum, and you are
   never missing a plan — you're working inside one that's already set.

   What that means in practice: when this skill finishes, **stop**. Don't draft a
   build sequence, don't ask what the remaining steps are, and don't start one.

   Two failure modes this prevents, both of which look helpful:
   - **Running ahead.** Given a plan, an eager assistant executes it. Building
     three steps because the user asked for one destroys the thing the user came
     for — watching each piece get built and understanding it before the next.
   - **Building toward a step that hasn't been asked for yet.** Don't create a
     file "because we'll need it later", and don't design the current piece
     around a later one you're guessing at. Build exactly what the invoked skill
     specifies, then stop. If a later piece needs something different, its own
     skill will say so when its turn comes.

   When a skill's work is done, report what you built and wait.

5. **Report back, briefly:** which branch you ended up on (and say so plainly if
   you switched), what the project builds, and which skills are available. Then **stop and wait.** Don't
   recommend a first step or ask which one to run — the user is driving.

   **Don't audit the machine here.** Whether the tools are installed, which
   Python is present, whether `.env` has been filled in — none of that is this
   skill's business, and checking it early produces noise about things that
   aren't supposed to exist yet. Each of those belongs to the skill that
   actually deals with it, at the point where it matters.

### What the `main` branch is, and what it is not

The `main` branch was produced with **model `claude-opus-5` (Claude Opus 5),
reasoning effort `high`, on 2026-07-26**. Matching that spec gets you a build
that looks more like it; drifting from it gets you one that looks less like it.
That is all the spec means.

**The `main` branch is one build that works. It is not the gold standard, not the
reference answer, and not a grading key.** It's what came out of one session, on
one day, from one model. A build that differs from it is not wrong — if yours
satisfies the requirements and runs, yours is exactly as valid, and it may well
be better. The requirements are the standard; that branch is one thing that met
them.

So when a comparison happens, treat a difference as **interesting, not
incorrect**: worth a look to see whether it reveals a requirement one of the two
missed, and otherwise just two legitimate ways to build the same thing. Never
"correct" a working build to look more like `main`, and never tell the user their
output is wrong because it diverged.

### Rules for this session

**Build from the spec, never from the finished answer.** The `main` branch holds
a completed version of this app. When the job is to **build** — to produce the
app by running the skills — that finished code is **off-limits as a source**.
Do not open it, copy it, paraphrase it, or check your work against it mid-build.
Write every file from the skill's "Local adaptations (this project)" section and
nothing else.

This is not a formality; it is the entire point of the exercise:

- **A spec that can only produce the app while the answer is visible is a broken
  spec, and copying hides the break.** If you catch yourself wanting to look at
  the finished file because the requirements feel thin, you have found a real
  gap. **Say so, name the missing decision, and fill the gap in the skill** —
  that repair is worth more than the file you were about to copy.
- **Nobody learns to direct an AI by watching it transcribe.** The reason to
  build is to see the requirements turn into working code.

How to tell which job you are on:

- **Building / reproducing** — the finished code is off-limits, as above. Work on
  `start`, or in an empty folder. If a finished copy happens to be sitting in the
  working directory, do not read it; ask to move or ignore it first.
- **Maintaining** — running, deploying, debugging, or changing the app that is
  already here (the normal job on `main`). Reading the existing code is not only
  fine, it is required. This is not the cheat; the cheat is *reproducing* a build
  with the answer open beside you.

Comparing against the `main` branch is legitimate **after** your build works,
never during it — finish, run it, then diff to see where the two landed
differently.

**Never edit a vendor skill.** Two kinds of skill live in `.claude/skills/`:

- **Personal skills** carry this project's specification in their "Local
  adaptations (this project)" section. Improve them freely — folding a lesson
  back into the responsible skill is how the next build gets better, and it is
  exactly what `/skill-end` does.
- **Vendor skills** were downloaded from someone else and must stay
  byte-identical to what shipped — no project details, no reformatting, no
  lessons. That way an upstream update drops straight in. When a step needs a
  vendor skill *and* this project's details, the details go in a personal
  companion skill, and the user invokes the two together.

Before editing any skill, ask which kind it is. If it shipped from elsewhere,
the lesson goes in the nearest personal skill instead.

**Never invoke a skill yourself — the user types the slash commands.** Running
`/skill-…` is the user's job, always. It is how they drive the build one piece at
a time, and it is the entire reason this works the way it does: they decide what
gets built next and when. So never run one on your own initiative, never chain
from the skill you're in into another one, and never treat "the next skill
obviously comes next" as permission. When a skill's work is done, report and
wait.

**Prefer a skill over hand-writing.** If a skill covers the work, don't
reconstruct it on the fly — its spec is more complete than anything you'd write
from memory. Treat "I'll just write this directly" as a signal to check the skill
list again, then **tell the user which skill covers it and let them invoke it.**

**Build it fully — no placeholders.** No `TODO`, no `FIXME`, no stub function
whose body is a comment describing what it should do, no note explaining what is
still missing. If something needs doing, do it and wire it end to end. The only
acceptable stopping point is a genuine external blocker, like a credential only
the user has — and even then, build everything up to that blocker.

**Paper trading, on purpose.** This build targets a broker's paper/sandbox
environment and nothing else. Never point it at a live-money account, never
substitute live credentials or a live endpoint for the sandbox ones, and never
present any of it as trading advice. If the user supplies live-account
credentials, stop and say why rather than wiring them in.

**Never fail silently.** When a broker rejects an order or an external call
fails, log the full reason and return it. A swallowed error in a trading system
is worse than a crash, because the position is wrong and nobody knows why.

**Never commit secrets.** The real `.env`, API tokens, and account ids stay out
of git and off the screen. `.env.example` is the only one that ships.

**Add any new setting to `.env.example` in the same step that introduces it.**
If a piece of work starts reading a new environment variable, that file has to
learn about it immediately — otherwise it drifts out of date, and the first
sign is the deployed app behaving differently from the local one for no visible
reason.

**Do not create branches, commit, or push unless asked.** Work on the branch
that is already checked out.

### Pinned choices, and what is left to you

**How much technical direction the skills give — and why so little.** The skills
in this repo pin a choice for exactly one reason: leaving it open would let this
build come out **visibly different** from the one it reproduces. That is the
whole test. The stack, the broker, the names a person sees on screen — pinned,
because a mismatch there is obvious. Everything else is yours to decide —
**working out the mechanics is the job.** If you find yourself wishing the spec
had named an approach, that's the work, not a gap in the brief. Decide, say what
you decided and why, and move on.

**Pinned, because it is visible**
- A widely used Python web framework — Flask is a good pick — served in
  production by a standard production web server.
- Tradier as the broker.
- Render as the primary host.
- The alert receiver and the dashboard pages live together in the application's
  entry-point module — the one that creates the web app and is what gets run;
  everything that talks to the broker lives in its own module beside it. The
  TradingView strategy and the machine-setup scripts each get their own folder.
  (Name the entry-point module for the application, not `main.py` — "the entry
  point" here has nothing to do with the `main` git branch.)

**Left to you**
- **Everything not named above.** Deciding it is the job — see the note at the
  top of this section.

**Scope limit**
- Position management, partial-fill handling, retry logic, and order types
  beyond the simplest one are beyond the scope of this build. Don't add them
  unasked.

# END
