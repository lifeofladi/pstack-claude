---
name: reflect
description: Spawn three parallel review subagents over the active transcript, surface learnings, and route each to a concrete edit on an existing skill. Use when the user says reflect.
---

# Reflect

Mine the current conversation for durable learnings, then route them into skill edits.

## When to invoke

- The user said "reflect" or "/reflect".
- A complex task (5+ tool calls) just landed cleanly and the recipe is worth keeping.
- The agent hit dead ends, found the working path, and the path generalizes.
- The user corrected the agent's approach mid-task.
- A non-trivial workflow emerged that isn't captured anywhere.

Skip when the conversation is trivial, off-topic, or already covered by an existing skill the parent followed correctly. One-offs are not learnings.

## Process

### 1. Locate the active transcript

The parent finds its own transcript file before fanning out. Transcripts live at `~/.claude/projects/<slug>/<session-id>.jsonl`, where `<slug>` is the workspace path with its separators replaced by dashes (`/Users/me/dev/app` becomes `-Users-me-dev-app`).

```bash
ls -t ~/.claude/projects/<slug>/*.jsonl 2>/dev/null | head -10
```

Stay inside this project's directory. Globbing across `~/.claude/projects/*/` crosses workspace boundaries and reads private chats from unrelated projects.

For each candidate, read the first JSONL line and check that `message.content[0].text` contains the conversation's opening user prompt. Take the matching path. If no path resolves, write a tight digest of the session and pass that instead.

### 2. Spawn three reviewers in parallel

One message, three `Agent` calls. Each reviewer needs its full tool set for context lookups (tickets, chat threads, observability traces referenced in the transcript), so use `pstack:poteto-agent` rather than a restricted seat. The prompt forbids file writes; the parent applies edits.

| Lens | `subagent_type` | `model` | Prompt template |
|---|---|---|---|
| Judgment | `pstack:poteto-agent` | `fable` | `references/judgment-reviewer.md` |
| Tooling | `pstack:poteto-agent` | `sonnet` | `references/tooling-reviewer.md` |
| Divergent | `pstack:poteto-agent` | `opus` | `references/divergent-reviewer.md` |

The divergent seat runs on a different model from the other two on purpose. Its job is the reading neither of them took, and it cannot do that from the same priors.

Pass each template verbatim, substituting the transcript path or digest where marked. Reviewers return findings in the `Agent` response body.

### 3. Synthesize

One `Agent` call, `subagent_type: "pstack:poteto-agent"`, `model: fable`. The synthesizer spot-verifies citations against the transcript, so it needs the same access the reviewers had. Use `references/synthesizer.md` verbatim, with each reviewer's full output inlined where marked. The synthesizer returns a structured Accepted / Rejected / Backlog list.

### 4. Structural enforcement check

Sanity-check the synthesizer's Accepted list. For any item that would be enforced more reliably by a lint rule, script, metadata flag, or runtime check, move it from Accepted to Backlog. The synthesizer already applies this criterion; this is a final pass before edits land. See the **encode-lessons-in-structure** principle skill.

### 5. Apply

Before applying any Accepted edit, present the synthesizer's full Accepted/Rejected/Backlog output to the user and wait for explicit approval. The user picks which subset to apply and may redirect routings. Skill changes affect every future agent in the org; do not auto-apply.

Backlog items file to whatever devex / backlog tracker your team uses automatically. Those are tracker submissions, not skill edits. Only the Accepted list waits for approval.

For each approved Accepted item, follow the Routing field exactly:

- Trivial existing-skill edit (a one-line bullet, a tightened sentence, a stale fact corrected): parent does directly.
- Substantive existing-skill edit (a new section, a new pattern table, more than ~10 lines): follow the Authoring a skill playbook (`../poteto-mode/playbooks/authoring-a-skill.md`) and run its draft / test / iterate loop.
- `tune description: <skill path>` (the skill exists but didn't trigger when it should have): rewrite the `description` line against the phrasings that failed to trigger it, then re-run the eval from the Eval playbook.
- `new skill: <kebab-name>`: author it per the Authoring a skill playbook. Do not invent the shape ad hoc.
- **Not a skill edit at all.** Three destinations beat a skill edit when they fit, and preferring them is the **encode-lessons-in-structure** principle:
  - A durable fact about the user, the project, or how they want you to work goes to this project's memory directory as one file per fact, indexed in `MEMORY.md`.
  - A rule that should fire automatically on some event goes in `settings.json` as a hook. Use `/update-config`.
  - A rule a machine can check goes in a lint, a script, or a test.

Read every touched `SKILL.md` back after editing and confirm its frontmatter still parses, its `name` still matches its directory, and its `description` still names the phrasings that should trigger it.

### 6. Summarize for the user

Short list, no preamble:

- Edits applied: `<skill path>`. What changed, one line each.
- New skills created: `<skill path>`. One line each (rare).
- Backlog filed to the devex tracker: `<issue title>` (`<tags>`). One line each.
- Dropped: one line per rejected finding + reason from the synthesizer.
