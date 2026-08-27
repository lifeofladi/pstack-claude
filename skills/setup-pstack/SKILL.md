---
name: setup-pstack
description: Configure which models and effort tiers pstack uses per role. Writes ~/.claude/pstack-models.md, which every pstack skill reads and which overrides the built-in defaults. Use for /setup-pstack, "configure pstack models", or changing pstack's model choices.
---

# Setup pstack

pstack ships with working defaults, so this skill is optional. Run it when you want different models per role, a different panel shape, or fewer seats to save tokens.

It writes `~/.claude/pstack-models.md`. Every pstack skill reads that file when it exists and falls back to `../poteto-mode/references/model-roles.md` when a role has no line there. It is an override layer, not a requirement.

## What you can and cannot set

**Model, yes.** `opus`, `sonnet`, `haiku`, `fable`, or `inherit`. The `Agent` tool takes `model` on every call, so a role's model is always yours to choose.

**Effort, only for the panel seats.** Effort comes from an agent definition's frontmatter, and the `Agent` tool cannot override it per call. The four panel agents ship with their tiers baked in (`pstack:panel-correctness` at `xhigh`, `pstack:panel-design` at `high`, `pstack:panel-evidence` at `xhigh`, `pstack:panel-mechanics` at `high`). To change one, edit that agent file in the plugin. Writing a different effort into `pstack-models.md` records your intent but does not by itself change what runs, so this skill will tell you when a choice needs a file edit instead.

**Lens, yes, by choosing seats.** Dropping a seat from a panel line removes it. Adding a seat means writing its lens and pointing at an agent that carries it.

## Steps

### 1. Confirm the available models

The valid values are `opus`, `sonnet`, `haiku`, `fable`, and `inherit`. Confirm which of these the user can actually reach in this session rather than assuming all four. If a model is not entitled, an `Agent` call naming it fails at spawn time, and a config that points at it breaks every delegation for that role.

Do not invent model names. Do not write a dated model id here; the short aliases are what the `Agent` tool takes.

### 2. Load current state

If `~/.claude/pstack-models.md` exists, read it and treat its values as the current choices. Otherwise start from the defaults in `../poteto-mode/references/model-roles.md`.

### 3. Map and confirm

Show every role with its current model and effort, marking anything unavailable. Ask whether to accept as-is or change specific roles. Prefer `AskUserQuestion` over free text.

Most users only care about a few decisions, so lead with those rather than walking all sixteen roles:

- **How hard should the default code delegate work?** Trading `sonnet` for `opus` on the code roles costs more and catches more.
- **How many panel seats?** Four is the default. Three drops mechanics and saves roughly a quarter of review cost. Two is a spot check, not a panel.
- **Is anything running on a model they don't want to pay for?**

For panel roles (`how critics`, `arena runners`, `architect runners`, `interrogate reviewers`) the value is a list, one seat per entry, so the list length sets the fan-out. `arena cross-judge pool` is also a list, and Arena picks from it a model that produced none of the candidates.

### 4. Validate

Every model written must be one the user can reach; `inherit` always passes. If a chosen model is unavailable, stop and ask again.

Check the panel lines against the lens rule: **no two seats in one panel may hold the same lens.** A panel with two correctness seats costs double and returns the same findings twice. If the user asks for that anyway, say why it doesn't help once, then write what they asked for.

Flag any effort value that differs from the shipped agent definition, and name the file they would need to edit to make it real.

### 5. Write the config

Write `~/.claude/pstack-models.md`, overwriting the whole file so re-runs stay idempotent. One line per role, using the same labels as `model-roles.md`. Delete a line to fall back to the default.

```markdown
# pstack model configuration
# One line per role. Delete a line to fall back to the pstack default.
# Models: opus | sonnet | haiku | fable | inherit
# `inherit` means that role runs on the parent's model (omit `model` on the Agent call).
# Panel lines list one seat per entry as `<model> <effort> <lens>`; the entry count sets the fan-out.

fast mechanical code: haiku
precisely-specified code: sonnet
hardest tasks: opus
judgment and prose: fable
bug fix: sonnet
perf issue, hillclimb: sonnet
feature, refactoring: sonnet
how explorer: sonnet
how explainer: fable
why investigators: sonnet
why synthesizer: fable
swarm workers: sonnet
reflect tooling: sonnet
reflect judgment: fable
reflect divergent: opus
reflect synthesizer: fable
how critics: opus xhigh correctness, fable high design, sonnet xhigh evidence
arena runners: opus, fable, sonnet, haiku
arena cross-judge pool: opus, fable, sonnet, haiku
architect runners: opus, fable, sonnet, haiku
interrogate reviewers: opus xhigh correctness, fable high design, sonnet xhigh evidence, haiku high mechanics
```

### 6. Confirm

Tell the user what changed from the defaults, in one line per changed role. Say plainly that nothing needs restarting; skills read the file when they run.

If any effort choice needs a plugin agent file edited to take effect, say which file and which line, and offer to make that edit.
