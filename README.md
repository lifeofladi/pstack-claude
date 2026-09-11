# pstack for Claude Code

A Claude Code port of [pstack](https://github.com/cursor/plugins/tree/main/pstack), Lauren Tan's ([poteto](https://x.com/poteto)) agent-workflow plugin.

The original is a Cursor plugin. This fork keeps the engineering discipline and rebuilds the parts that were bolted to Cursor: the tool names, the model routing, the review panels, and the control surfaces.

**The thesis is unchanged.** AI writes too much slop. Throughput without quality is not a goal worth having. If you want to go fast, go deep first. pstack helps you write less code, of higher quality, and gives you enough confidence in one agent that you can run several in parallel.

## Install

Two ways. The plugin is per machine and updates from git. The account skill (next section) follows your claude.ai account into every session.

As a plugin, in a Claude Code chat:

```text
/plugin marketplace add lifeofladi/pstack-claude
/plugin install pstack@pstack-claude
/reload-plugins
```

To work on the plugin itself, add your checkout instead of the repo:

```text
/plugin marketplace add /path/to/pstack-claude
```

The reload reports what registered. Expect 44 skills and 6 agents. The plugin is pure markdown plus two small shell scripts; there is nothing to build.

### Requirements

The skills themselves are markdown and need nothing installed. Two playbooks shell out to bundled TypeScript, and those need **Node 24.2 or newer** on your `PATH`. Babysit runs `scripts/watch-pr/watch-pr` to read PR status, and Orchestrate runs `scripts/orch/orch.ts` for bookkeeping. Both run straight from source on Node's built-in TypeScript support and install their one dependency on first use. Babysit and Shipping also expect the `gh` CLI.

### Turn on auto-update

Claude Code disables auto-update for third-party marketplaces by default, so a fresh install never changes again on its own. Turn it on once:

1. Run `/plugin`.
2. Go to the **Marketplaces** tab.
3. Select `pstack-claude`.
4. Choose **Enable auto-update**.

Claude Code then refreshes after your session starts, within about ten minutes, and prompts you to run `/reload-plugins`. The running session keeps the version it launched with either way.

Without this you stay on the copy you installed until you run `/plugin marketplace update pstack-claude` yourself.

## Install as an account skill

The same library packaged as one claude.ai skill, so it loads in every Claude Code, Cowork, and claude.ai session on your account without a per-machine plugin install.

```bash
python3 scripts/build-account-skill.py
```

That writes `dist/pstack.skill`. Upload it in claude.ai under Settings, Capabilities, Skills, or click **Save skill** when Claude hands you the file in a chat. Rebuild and re-upload after editing anything under `skills/` or `agents/`.

What differs from the plugin:

- **One skill, named `pstack`.** A claude.ai skill holds exactly one `SKILL.md`, so the build generates a router that indexes all 44 skills as `skills/<name>/<name>.md`. `/pstack interrogate this` or plain "interrogate this" reach the same file `/interrogate` did. The skill's description carries every trigger phrase, since it is the only text in context before the skill loads.
- **Agents install on first use.** A skill cannot register subagents, so the six definitions ship in `agents/` and the first dispatch runs `scripts/install-agents.sh`, which copies them into `~/.claude/agents/`. From the next session on, `subagent_type: "panel-correctness"` resolves with its effort tier baked in. Until then the seat runs on `general-purpose` with the same body and model, and the effort tier requested in the prompt.
- **Uninstall the plugin once the skill is saved.** With both present Claude has two copies of every skill to pick from and tends to pick the plugin's.

The build is a transform of the plugin tree, not a second copy to maintain. It strips the `pstack:` agent namespace, rewrites links between skills, applies a short list of exact-match patches for plugin-only wording, and fails on any broken reference, so the plugin stays the single source.

To try a build locally before uploading, symlink it as a user skill and remove the link when done:

```bash
ln -s "$PWD/dist/pstack" ~/.claude/skills/pstack
```

## Get started

Two steps:

1. Run `/poteto-mode` whenever you're doing anything that needs rigor.
2. Optionally run `/setup-pstack` to change which models each role uses. The defaults work without it.

```
/poteto-mode this pr has a subtle bug where the scroll drifts every 750ms even when idle.
repro first, then fix and verify.
```

`/poteto-mode` reads your request, matches it to one of 23 playbooks, copies those steps into a task list verbatim, and routes to the other skills as each step fires. You don't name a playbook or list skills. A goal and a way to check it is all the routing signal it needs.

It's sticky. Once entered it stays on for the session, applying itself when a playbook matches and staying out of the way otherwise. Say so to opt out.

## What's in it

| | count | |
|---|---|---|
| **Playbooks** | 23 | procedures for bug fix, perf, refactoring, shipping, orchestration, overnight runs |
| **Principle skills** | 21 | one rule each, grouped core / architecture / verification / delegation / meta |
| **Workflow skills** | 23 | `/how`, `/why`, `/architect`, `/arena`, `/swarm`, `/interrogate`, `/unslop`, and more |
| **Agents** | 6 | the style wrapper, Comment Sicko, and four review panel seats |

Run `/poteto-mode` and it uses the rest for you. Reach for one directly when you want just that:

```
/how do we cancel runs? do we have an n+1 when we look up every run to cancel?
/interrogate review this pr.
/why is this feature flag not on yet?
```

## What changed from the Cursor version

### Review panels are built from lenses, not vendors

This is the substantive difference. Upstream, `/interrogate`, `/arena`, `/how --critique`, and `/architect` drew their adversarial signal from running four different vendors' models against the same prompt. Claude Code routes to Anthropic models only, so a straight transliteration would have been four near-identical reviewers agreeing with each other.

Instead each panel seat is a **separate agent** with its own lens, model, and effort tier baked in:

| Seat | Model | Effort | Hunts |
|---|---|---|---|
| `panel-correctness` | `opus` | `xhigh` | edge cases, error paths, races, the input that breaks it |
| `panel-design` | `fable` | `high` | shape, simplification, what the maintainer inherits |
| `panel-evidence` | `sonnet` | `xhigh` | does it actually run and do what it claims |
| `panel-mechanics` | `haiku` | `high` | naming, dead code, convention drift, comments |

Two seats never share a lens. Agreement between seats that arrived from *different* directions is the signal; agreement between identical prompts was never worth much.

Separate agent files are load-bearing rather than cosmetic. The `Agent` tool can override `model` per call but **not** `effort`, which comes only from an agent definition. Tier diversity is real here because each seat is its own file.

### Everything else that moved

| Cursor | Here |
|---|---|
| `Task` tool | `Agent` tool |
| `AskQuestion` | `AskUserQuestion` |
| `~/.cursor/rules/pstack-models.mdc` (always-applied rule) | `~/.claude/pstack-models.md`, read by the skills |
| Model slugs (`grok-4.6-fast-xhigh`, `gpt-5.6-sol-max`, …) | `opus` / `sonnet` / `haiku` / `fable` + effort tiers |
| `control-cli`, `control-ui` (unbundled) | the built-in `run` and `claude-in-chrome` skills |
| `/deslop` (unbundled) | folded into `/unslop` |
| `/create-skill` (Cursor built-in) | the Authoring a skill playbook, now self-contained |
| Cursor's Bugbot | any automated reviewer, `/code-review`, `/security-review` |
| `environment: "cloud"` | `isolation: "remote"` / `isolation: "worktree"` |
| ad-hoc todolists | `TaskCreate` / `TaskUpdate` |
| cloud-sleeper wake chains | `/loop`, `ScheduleWakeup`, `/schedule` |
| Graphite assumed | Graphite when present, `gh` fallback documented |

The port also wires in Claude Code capabilities the original had no way to use: worktree isolation for parallel writers, the memory directory as a destination for `/reflect`, hooks via `/update-config` for `principle-encode-lessons-in-structure`, and `ReportFindings` for `/interrogate`.

## The 21 principles

`poteto-mode` indexes them inline and reads that index at task start. The standalone files exist so other skills can cite a principle by name and so the index can point at the full rule.

**Core.** laziness-protocol, foundational-thinking, redesign-from-first-principles, subtract-before-you-add, minimize-reader-load, outcome-oriented-execution, experience-first, exhaust-the-design-space, build-the-lever.

**Architecture.** model-the-domain, boundary-discipline, type-system-discipline, make-operations-idempotent, migrate-callers-then-delete-legacy-apis, separate-before-serializing-shared-state.

**Verification.** prove-it-works, fix-root-causes, sequence-verifiable-units.

**Delegation.** guard-the-context-window, never-block-on-the-human.

**Meta.** encode-lessons-in-structure.

Naming one mid-task redirects the agent. "this is doing too much, apply subtract-before-you-add" lands harder than a paragraph of explanation.

## Configure the models

`/setup-pstack` writes `~/.claude/pstack-models.md`, one line per role. Skills read it and fall back to the defaults in `skills/poteto-mode/references/model-roles.md` when a line is absent, so you override only what you care about.

Model is settable per role from the config. Effort is settable only for the panel seats, and only by editing those agent files, because the `Agent` tool can't override effort per call. `/setup-pstack` tells you when a choice needs a file edit instead.

## Validate

```bash
python3 scripts/validate-plugin.py
```

Checks the manifest, every skill and agent's frontmatter, cross-file references, relative links, and that no Cursor-era construct survived. Run it after editing anything.

`python3 scripts/build-account-skill.py` validates the account-skill package the same way and exits non-zero on a broken reference or a patch that no longer matches.

## Not ported

- **The benny automation pack.** Upstream ships a dormant Slack triage-and-repro automation. Its triggers are Cursor automations with no direct equivalent; porting it means rebuilding on `/schedule` plus a Slack MCP. Not done here.
- **The docs guide** (`docs/guide/`) came across with a light pass. The prompts and concepts hold; a few Cursor-flavored asides remain.

## Make it yours

`/automate-me` mines your recent transcripts, drafts a `<your-name>-mode` skill from how you've actually worked, and routes through pstack underneath. You keep pstack as the base and get your own routing skill alongside `poteto-mode`.

## Credit and license

All of the engineering substance here is Lauren Tan's. This fork is a port, not a rewrite; the playbooks, principles, and voice are the original's. MIT, as upstream.
