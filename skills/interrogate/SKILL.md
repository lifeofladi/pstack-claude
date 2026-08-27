---
name: interrogate
description: "Use for \"interrogate\", \"adversarial review\", \"multi-model review\", \"challenge this\", \"stress test this code\", \"find blind spots\", or \"tear this apart\". A panel of reviewers challenges the change through different lenses, models, and effort tiers."
---

# Interrogate

Spawn a panel of reviewers to adversarially review code changes.

**The adversarial signal comes from lens diversity.** Each seat is given a different question to answer, a different model, and a different effort tier. Four reviewers running the same prompt mostly agree with each other and mostly miss the same things; four reviewers hunting different failure modes cover ground no single pass reaches. Agreement between seats holding *different* lenses is high-confidence signal, because they arrived from different directions. Agreement between seats holding the same lens is noise, which is why no two seats ever share one.

A finding from a single seat is worth reading, at lower confidence, and the seat that raised it tells you how to weigh it. The mechanics seat flagging a naming problem alone is expected. The correctness seat flagging a data-loss race alone is not something to discount because nobody seconded it.

The deliverable is a synthesized verdict. Do NOT auto-apply changes.

## Step 1, Determine Scope

Identify what to review from context:

- If the user points at specific files or a diff, use that
- If on a feature branch, run `git diff main...HEAD` (or the appropriate base branch) for the full changeset
- If the user's message references recent work, gather the relevant files

Package the diff (or file contents) plus any surrounding context files the reviewers need to understand the code.

## Step 2, State the Intent

Before spawning reviewers, state the intent explicitly. What is this code trying to accomplish? Derive this from:

- The user's message
- Commit messages
- PR description if one exists
- The code itself

Write one clear paragraph. Reviewers challenge whether the work achieves the intent well, not whether the intent itself is correct. If you're unsure about the intent, ask the user before proceeding.

## Step 3, Spawn Reviewers

Launch every seat in a **single message** so they run concurrently. Each seat is a dedicated agent whose lens, model, and effort tier are baked into its definition, so you do not set `model` and cannot set `effort`.

| Seat | `subagent_type` | Model | Effort | Hunts |
|---|---|---|---|---|
| Correctness | `pstack:panel-correctness` | `opus` | `xhigh` | edge cases, error paths, races, the input that breaks it |
| Design | `pstack:panel-design` | `fable` | `high` | shape, simplification, what the maintainer inherits |
| Evidence | `pstack:panel-evidence` | `sonnet` | `xhigh` | does it actually run and do what it claims |
| Mechanics | `pstack:panel-mechanics` | `haiku` | `high` | naming, dead code, convention drift, comments |

Drop a seat when the diff genuinely has no surface for it, and say which one you dropped and why. A one-line config change does not need the evidence seat driving a browser. Never drop the correctness seat.

When `~/.claude/pstack-models.md` sets an `interrogate reviewers` line, it overrides this table. Each entry is `<model> <effort> <lens>`; spawn the matching panel agent for that lens, overriding `model` only when the line names a different one. The line's entry count sets the seat count. A value of `inherit` means omit `model` on that call.

Read `references/reviewer-prompt.md` and fill in the template with:
1. The stated intent
2. The diff or file contents, or the paths and line ranges when the diff is large
3. The review rubric from `references/rubric.md`
4. The code-quality lens from `references/code-quality-review.md`

The same filled template goes to every seat. **Append one line naming that seat's lens and telling it to stay in its lane.** The seat's own definition already carries the lens in depth; this line is the reminder that the other three lenses are covered and duplicating them wastes the panel.

Each seat produces structured findings as described in the prompt template.

## Step 4, Synthesize

As results come back, build a unified picture:

1. **Parse all findings** from every seat.
2. **Identify cross-lens consensus.** A finding two seats reached through different lenses is the highest signal the panel produces. The design seat calling a structure fragile and the correctness seat finding the race it permits are the same finding, arrived at twice.
3. **Weigh lone findings by seat.** A lone correctness or evidence finding carries weight on its own; those seats deal in demonstrable failures. A lone design or mechanics finding is a judgment call to categorize in step 5.
4. **Deduplicate.** Seats describe the same issue in their own vocabulary. Merge them and record which seats raised it.
5. **Note disagreements.** One seat flagging what another explicitly cleared is useful context, and the evidence seat's verdict usually settles it. When it does not, say the disagreement is unresolved rather than picking the answer you like.
6. **Check what nobody covered.** Name the part of the diff no seat examined. An unreviewed area is a result, and hiding it behind four confident reports is how a panel launders a gap into a clean bill of health.

## Step 5, Lead Judgment

You are the lead reviewer, a pragmatic senior engineer, not a neutral aggregator.

Read `references/lead-judgment.md` for the full framework. Reviewers only see a slice of the codebase. You have the full context (the goal, the constraints, the timeline, which tradeoffs were already considered). Use that context aggressively.

Categorize every finding using these buckets:

- **Act on**. Real issues affecting correctness, security, or maintainability given the actual goals. These would block a real PR.
- **Consider**. Legitimate points, but you're not sure they outweigh the cost of addressing them right now. Worth the user's attention.
- **Noted**. Technically valid but not actionable. Context-dependent, premature optimization, or low-impact given the current stage.
- **Dismissed**. Wrong, nitpicky, or missing context. Brief explanation why.

For each finding, include:
- Which seat(s) raised it
- The category (act on / consider / noted / dismissed)
- A one-line rationale for the categorization

## Output Format

When the host supports it, report the **Act on** and **Consider** findings through the `ReportFindings` tool so they render as a typed list, ranked most severe first. Set `verdict: "CONFIRMED"` only for findings the evidence seat reproduced, and `"PLAUSIBLE"` for everything else. Do not also print those findings as text; write the rest of the verdict below in prose.

Present the verdict in this structure:

### Intent
> [The stated intent paragraph from Step 2]

### Panel
- [Seat]: [model], [effort], [N findings] (one bullet per seat, plus any seat you dropped and why)

### Act On
[Findings that should be addressed. For each: description, which seats raised it, why it matters.]

### Consider
[Findings worth thinking about. For each: description, which seats raised it, tradeoff involved.]

### Noted
[Valid but low-priority. Brief list.]

### Dismissed
[Rejected findings with brief rationale. This shows the user what was filtered out and why, so they can override your judgment if they disagree.]

### Agreement Map
[Where did seats converge from different lenses, where did they diverge, and what does that pattern say? Close with what no seat covered.]
