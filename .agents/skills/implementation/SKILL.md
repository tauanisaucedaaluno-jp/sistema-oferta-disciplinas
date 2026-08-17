---
name: implementation-together
description: >
  Use this skill when the user wants to execute a complex task that benefits from multiple specialized
  approaches working in concert: explaining simply (caveman), challenging assumptions (grill-me),
  writing tests first (tdd), and following project guidelines (guideline). Trigger whenever the user
  asks to implement a feature, build a system, solve a multi-step problem, or says anything like
  "let's build", "implement this", "start the task", or "work on this together". Always saves
  progress to /specs/specs.md after each step so work is never lost.
---

# Implementation Together

Orchestrates multiple specialized skills in sequence to deliver high-quality, well-reasoned implementations. Every task is broken into verifiable steps, challenged for blind spots, test-driven, and aligned with project guidelines — with full progress saved after each move.

---

## Skill Inventory

Before starting any task, read all four skills in parallel:

| Order | Skill path                                                | Purpose                                                            |
| ----- | --------------------------------------------------------- | ------------------------------------------------------------------ |
| 1     | `Sorted-Chaos/grupo12/.agents/skills/caveman`             | Simplify the problem to its core — strip jargon, find the real ask |
| 2     | `Sorted-Chaos/grupo12/.agents/skills/grill-me`            | Challenge assumptions, surface edge cases, stress-test the plan    |
| 3     | `Sorted-Chaos/grupo12/.agents/skills/tdd`                 | Write failing tests first, then implement to make them pass        |
| 4     | `Sorted-Chaos/grupo12/.agents/skills/guideline`           | Ensure output follows project conventions and standards            |

> **Note:** `Sorted-Chaos/grupo12/.agents/skills/grill-with-docs` is available as a supplement to `grill-me` when the task involves external documentation or specs. Load it alongside `grill-me` if docs are present.

---

## Execution Protocol

### Phase 0 — Orient

1. Read all four skill files.
2. Read `/specs/specs.md` if it exists (resume context).
3. Identify which skills are most relevant to the current task.
4. Determine skill order (default: caveman → grill-me → tdd → guideline; adjust if the task calls for it).

### Phase 1 — Caveman (Simplify)

- Restate the problem in the simplest possible language.
- Identify the **one core thing** that needs to happen.
- Reject scope creep — flag anything that is not strictly necessary.
- Output: a plain-language problem statement + a concrete goal.

### Phase 2 — Grill-Me (Challenge)

- Ask the hard questions: What could go wrong? What are we assuming? What's the failure mode?
- Surface at least 3 assumptions and evaluate each.
- If docs exist, invoke `grill-with-docs` to cross-check against them.
- Output: a list of validated assumptions + a risk-aware plan.

### Phase 3 — TDD (Test-First Implementation)

- Write failing tests before writing any implementation code.
- Implement only enough to make the tests pass.
- Refactor once tests are green.
- Output: test files + implementation files.

### Phase 4 — Guideline (Standards Check)

- Review the output against project conventions (naming, structure, formatting, patterns).
- Fix any violations.
- Output: compliant, production-ready code/artifact.

---

## Progress Tracking

**All progress is saved to `/specs/specs.md` after every phase.**

Structure of `/specs/specs.md`:

```markdown
# Task: <title>

## Status

Current phase: <phase name>
Last updated: <timestamp>

## Problem Statement (Caveman)

<plain-language summary>

## Assumptions & Risks (Grill-Me)

- [ ] Assumption 1 — <validated/flagged>
- [ ] Assumption 2 — <validated/flagged>

## Test Plan (TDD)

- [ ] Test: <description> — <status>

## Implementation Steps

- [x] Step 1 — done
- [ ] Step 2 — in progress
- [ ] Step 3 — pending

## Decisions Log

- <date>: <decision and rationale>

## Open Questions

- <question>
```

Update `/specs/specs.md` **after each phase completes** — not just at the end.

---

## Adaptive Behavior

- **If a phase is clearly irrelevant** (e.g., task has no code → skip TDD), note the skip in `/specs/specs.md` and move on.
- **If the user interrupts mid-task**, save state immediately to `/specs/specs.md` and summarize where things stand.
- **If resuming a previous task**, read `/specs/specs.md` first and pick up from the last incomplete phase.
- **If requirements are ambiguous**, use the Caveman phase to surface the ambiguity and resolve it before proceeding.

---

## Output Expectations

Each phase should produce a concrete, inspectable artifact:

| Phase     | Artifact                                                   |
| --------- | ---------------------------------------------------------- |
| Caveman   | Written problem statement (added to `/specs/specs.md`)     |
| Grill-Me  | Assumptions list + risk notes (added to `/specs/specs.md`) |
| TDD       | Test file(s) + implementation file(s)                      |
| Guideline | Reviewed/corrected final output                            |

Do not move to the next phase without completing the artifact for the current one.

---

## Final Response Rule — Caveman Output

**All responses to the user must follow the caveman style from `Sorted-Chaos/grupo12/.agents/skills/caveman`.**

- Short sentences. Simple words. No jargon.
- Say only what matters. Cut the rest.
- This applies to every reply: status updates, questions, phase summaries, and final output explanations.

This rule exists to save tokens and keep communication clear. The code and artifacts can be as complex as needed — but the words you write to the user must be simple.
