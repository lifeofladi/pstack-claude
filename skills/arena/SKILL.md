---
name: arena
description: "Spawn N parallel candidates at the same task, pick a base, graft the strongest parts of the losers into it. Use for /arena, 'arena this', 'throw it in the arena', or when one attempt at a non-trivial artifact would lock in the wrong shape."
---

# Arena

Fan out N parallel attempts at the same task. Read every candidate end to end. Pick the strongest as the base. Graft the best ideas from the others into it. Verify the synthesized result.

## Start

Open a task list with one entry per phase before launching anything. The arena runs autonomously and the list keeps phases from silently disappearing.

1. Frame
2. Fan out
3. Cross-judge
4. Pick
5. Graft
6. Verify

## Phase A: Frame

The N candidates will receive the same prompt, so the prompt is the contract. Get it right before spawning anything.

1. State the artifact each candidate is producing.
2. Derive the rubric. State what success looks like for *this* task, then turn it into 3-6 concrete gradeable criteria. Concrete: `Adds a --dry-run flag that skips writes`. Vague: `code is correct`. The rubric is the picker's tool in Phase D; candidates only see the task.
3. Pick the runners and give each one a **stance**. Use `arena runners` from `~/.claude/pstack-models.md` when present. Otherwise default to one each on `opus`, `fable`, `sonnet`, `haiku`.

   A stance is the starting bias a candidate argues from, and it is what makes candidates actually differ. Without one, N runners converge on the same obvious answer and the arena buys nothing but tokens. Assign a different stance to each runner, drawn from what this task can vary:

   - **Smallest thing that works.** The minimum that satisfies the rubric, nothing speculative.
   - **Build for the next three requirements.** Assume this grows; pick the shape that absorbs growth.
   - **Risk-first.** Start from what breaks in production and design backward from the failure.
   - **Ergonomics-first.** Start from the call site and the reader. Design the API you would want to use, then make it work.

   Spawn more runners when the arena covers more directions than you have stances. Running the same model N times is fine when the work is generation-bound rather than judgment-sensitive; in that case the stances carry all the diversity, so they matter more, not less.
4. Assign output paths. Each candidate writes to its own location (a git worktree where possible, otherwise `/tmp/arena-<slug>/candidate-<n>/`). N candidates writing to the same path is shared mutable state and fails the the **separate-before-serializing-shared-state** principle skill test.

## Phase B: Fan out

Spawn all N subagents in one message with `run_in_background: true`, each with the task, the path to the shared grounding, its own output path, and instructions to produce both the artifact and a short rationale.

The rationale is mandatory. Without it, the parent cannot tell whether a candidate's structure is principled or accidental, which makes Phase E grafting unreliable. Each rationale names the alternatives the candidate considered and what it rejected.

If a candidate fails to produce output, proceed with N-1 and note the dropout in the synthesis record.

## Phase C: Cross-judge

After all Phase B candidates complete, spawn one read-only judge. Use the `arena cross-judge pool` in `~/.claude/pstack-models.md` when present; otherwise use `pstack:panel-design`, which is built for exactly this call.

**The judge must not grade its own homework.** Pick a model that produced none of the candidates. When every candidate came from the same model, the judge still differs on the other two axes: give it a stance no runner held, and read its verdict knowing it shares the runners' priors.

The judge sees the rubric and the candidates by path label, scores each criterion, and recommends a base with rationale. It runs in parallel with the parent's reading in Phase D, not with the candidates themselves. Spawning while candidates are still writing means the judge sees partial or empty outputs and reports them as dropouts.

## Phase D: Pick a base

Read every candidate end to end before picking. Skimming N candidates surfaces only the candidate whose surface looks most familiar.

Score each candidate against the rubric criterion by criterion, not on holistic feel. Compare against the cross-judge. Agreement on the base confirms the pick. Disagreement means one of you is biased or the rubric was ambiguous. Read both rationales before deciding.

Pick the base on which candidate a future maintainer can extend most easily without breaking invariants. Prefer the cleaner boundary or smaller surface area when two feel tied, per the Laziness Protocol.

Record the pick and the reason in a short synthesis note alongside the base artifact, including the cross-judge's verdict.

## Phase E: Graft

Walk each losing candidate once more and identify what is worth porting into the base. The signal is usually one or two things per candidate, not most of it.

Fold each graft in by hand, per the **redesign-from-first-principles** principle skill. Don't paste mechanically. The result has to remain coherent under one mental model.

Record what was grafted, from which candidate, and what was rejected and why. The rejection notes are the highest-signal part of the record. Future readers learn from what you considered and dropped, not just what you kept.

When N candidates converge on the same shape, that is a strong agreement signal. Note the convergence in the record and ship the consensus shape. No graft is needed. When N candidates wildly diverge, Phase A was under-specified. Reframe and re-run rather than averaging the divergence.

## Phase F: Verify

The synthesized artifact has to hold up under the same scrutiny as any other output, per the **prove-it-works** principle skill. The arena does not earn you a pass.

If verification surfaces a problem the arena did not catch, either Phase A was wrong (re-frame and re-run) or one candidate caught it and you missed the graft (go back to Phase E). Don't paper over.

## Outputs

One synthesized artifact. One short synthesis note alongside, naming the base, the grafts (with source candidate), the rejections, the dropouts if any, and the verification result.
