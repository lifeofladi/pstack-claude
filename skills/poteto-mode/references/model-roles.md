# Model roles

pstack routes each kind of work to a model and an effort tier. This file is the default mapping. `/setup-pstack` writes `~/.claude/pstack-models.md` to override any line; a role with no override keeps its default here.

Read the override file first when it exists. Never invent a model name. The valid values are `opus`, `sonnet`, `haiku`, `fable`, and `inherit` (run on the parent's model, which means omitting `model` on the `Agent` call). Valid effort values are `low`, `medium`, `high`, `xhigh`, and `max`.

## Single-agent roles

| role | model | effort | when |
|---|---|---|---|
| fast mechanical code | `haiku` | `medium` | trivial edits, renames, a sweep of the same change across files |
| precisely-specified code | `sonnet` | `xhigh` | a spec to execute to the letter, where the shape is already settled |
| hardest tasks | `opus` | `xhigh` | cross-cutting design, gnarly concurrency, subtle algorithms, vague intent |
| judgment and prose | `fable` | `high` | replies, docs, PR descriptions, unslop, naming |
| bug fix | `sonnet` | `xhigh` | the fix itself, once the mechanism is confirmed |
| perf issue, hillclimb | `sonnet` | `xhigh` | measured work against a baseline |
| feature, refactoring | `sonnet` | `high` | built from a named data shape |
| how explorer | `sonnet` | `medium` | read-heavy subsystem mapping |
| how explainer | `fable` | `high` | weaving the walkthrough |
| why investigators | `sonnet` | `high` | one per evidence source, in parallel |
| why synthesizer | `fable` | `xhigh` | reconciling contradictory evidence |
| swarm workers | `sonnet` | `medium` | one per slice, unless an arm names its own |
| reflect tooling | `sonnet` | `high` | what the transcript shows about tool use |
| reflect judgment | `fable` | `xhigh` | what the transcript shows about calls made |
| reflect divergent | `opus` | `xhigh` | the reading nobody else took |
| reflect synthesizer | `fable` | `xhigh` | the skill edit itself |

## Panels

A panel is the part of pstack that cannot be transliterated. Upstream it drew diversity from four model vendors. Here it draws diversity from three axes at once: **model**, **effort tier**, and a **lens** that fixes what that seat is looking for. Two seats never get the same lens. Agreement across different lenses is the signal; agreement across identical prompts is noise.

The standard four-seat panel:

| seat | model | effort | lens |
|---|---|---|---|
| 1 | `opus` | `xhigh` | **Correctness.** Edge cases, error paths, concurrency, the input that breaks it. Assume the happy path works and hunt everything else. |
| 2 | `fable` | `high` | **Design and altitude.** Is this the right shape? What would a simpler version look like? What does the next maintainer inherit? |
| 3 | `sonnet` | `xhigh` | **Evidence.** Does the claimed behavior actually reproduce? Run it. Every assertion in the diff or the writeup has to trace to something observed. |
| 4 | `haiku` | `high` | **Mechanics.** Naming, dead code, inconsistency with surrounding conventions, comments that shouldn't exist, the boring stuff the other three skip. |

Panel roles that use this table: `how critics`, `arena runners`, `architect runners`, `interrogate reviewers`.

Two rules for every panel:

- **Lens diversity is mandatory, model diversity is not.** If `/setup-pstack` collapses every seat to one model, the panel still works because the lenses still differ. If two seats ever get the same lens, drop one; a duplicate seat costs tokens and adds no information.
- **Seat count is set by the panel's role line.** Four is the default. Three is fine for a small diff. Adding a fifth means writing a fifth lens, not repeating one.

### Arena cross-judge

Arena judges candidates with a seat whose model differs from the one that produced the candidate, so no seat grades its own homework. When every candidate came from the same model, vary the effort tier and use a lens the producing seat did not hold.

## Reading the override file

`~/.claude/pstack-models.md` holds one line per role, in the same labels used above:

```
hardest tasks: opus xhigh
judgment and prose: fable high
interrogate reviewers: opus xhigh correctness, fable high design, sonnet xhigh evidence, haiku high mechanics
```

A panel line lists its seats comma-separated, each as `<model> <effort> <lens>`. The number of seats on the line sets the fan-out. A value of `inherit` means that seat runs on the parent's model, so omit `model` on the `Agent` call.
