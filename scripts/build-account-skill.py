#!/usr/bin/env python3
"""Build the account-level skill from the plugin tree.

A claude.ai skill holds exactly one SKILL.md, so the plugin's skills become
sub-skill files at skills/<name>/<name>.md and a generated SKILL.md routes to
them. Agents ship as installable definitions under agents/ because a skill
cannot register subagents itself.

Usage: python3 scripts/build-account-skill.py [output-dir]
Writes <output-dir>/pstack/ and <output-dir>/pstack.skill (default: dist/).
Exit code 0 when the package validates, 1 otherwise.
"""
import json
import os
import pathlib
import re
import shutil
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "dist").resolve()
OUT = OUT_DIR / "pstack"
ZIP = OUT_DIR / "pstack.skill"

IGNORE = shutil.ignore_patterns("node_modules", ".DS_Store", "__pycache__")

# Wording that only makes sense inside the plugin. Each pair must match exactly
# once so drift in the source fails the build instead of shipping stale text.
PATCHES = {
    "agents/poteto-agent.md": [(
        "Invoke the `poteto-mode` skill and read its `SKILL.md` in full "
        "before doing any work,",
        "Read `skills/poteto-mode/poteto-mode.md` under the pstack directory "
        "your caller named, in full, before doing any work,",
    )],
}

DESCRIPTION = (
    "poteto's pstack, a rigorous agent-workflow library for Claude Code. "
    "23 playbooks, 21 engineering principles, 23 workflow skills, and a "
    "4-seat adversarial review panel. Use whenever the user says pstack, "
    "/pstack, poteto, or poteto-mode, or names any pstack skill: how, why, "
    "teach, architect, arena, swarm, interrogate, blast-radius, "
    "figure-it-out, tdd, no-comments, unslop, bro, recall, reflect, "
    "technical-writing, show-me-your-work, automate-me, "
    "create-verification-skill, maintain-verification-skill, "
    "typescript-best-practices, setup-pstack, or a principle by name "
    "(laziness-protocol, prove-it-works, model-the-domain, and the rest). "
    "Also use it unprompted for any non-trivial engineering task that needs "
    "rigor: a bug fix with a repro, a feature, a refactor, perf work, a code "
    "walkthrough, design rationale, adversarial review, design exploration, "
    "parallel fan-out, PR babysitting and shipping, long autonomous runs, "
    "and any prose the user will read, since unslop applies always."
)

ROUTER = """---
name: pstack
description: {description}
---

# pstack

poteto's agent-workflow library, packaged as one skill. 23 playbooks, 21 principles, 23 workflow skills, and a 4-seat review panel. The thesis is that AI writes too much slop. If you want to go fast, go deep first.

This file only routes. The substance is in the sub-skill files.

## Routing

1. Match the request to a sub-skill in the index. `/pstack <name> ...` names one directly. "Interrogate this", "how does X work", or "architect this" names one by its trigger phrase. A non-trivial engineering task that names none routes to **poteto-mode**, which matches a playbook and calls the other sub-skills as its steps fire.
2. Read that sub-skill's file in full and follow it. Never work from the one-line index entry. The file is at `skills/<name>/<name>.md`, relative to this skill's directory.
3. When a sub-skill names another pstack skill (`/unslop`, "the **architect** skill", **principle-model-the-domain**), read that sub-skill's file too. Every name in the index resolves this way. A name that is not in the index (`/loop`, `/schedule`, `/update-config`, `/code-review`, `/security-review`, the `run` and `claude-in-chrome` skills) is a host built-in. Use it as the host provides it.
4. Paths inside a sub-skill (`references/x.md`, `playbooks/x.md`, `scripts/x`) are relative to that sub-skill's own directory, `skills/<name>/`. Run bundled scripts through `node` or `bash` explicitly. The executable bit does not always survive packaging.

Poteto mode is sticky once entered. Its file says how to carry that across turns.

## Index

### Entry point

{entry}

### Workflow skills

{workflow}

### Principles

Each is one rule. poteto-mode indexes them inline and reads a leaf in full whenever it applies one. Naming one mid-task redirects the agent.

{principles}

### Setup

{setup}

## Agents

Sub-skills dispatch these agents by name in `subagent_type`. Each one's lens, model, and effort tier live in `agents/<name>.md`.

| agent | model | effort | role |
|---|---|---|---|
{agents}

A skill cannot register agents, and Claude Code discovers agent files once, at process start. A file copied in mid-session, even from a `SessionStart` hook, is not seen until the next session. So check the session's list of available agent types before the first dispatch and resolve each `subagent_type` this way.

- The name is in the list. Use it as written.
- The name is not in the list. Spawn `subagent_type: "general-purpose"` and set both of these on the call.
  1. `model`, from the table. Never omit it. `general-purpose` carries no model of its own, and a seat on the wrong model loses the diversity the panel depends on. `inherit` is the one value that means omit it.
  2. The prompt, in this order. The body of `agents/<name>.md`. The line `pstack skill directory: <this skill's base directory>`. The effort tier from the table, as an instruction, since the `Agent` tool cannot set effort per call. Then the task, as file pointers rather than pasted contents.

  Then make the next session better. On a machine the user keeps, run `bash scripts/install-agents.sh` once; it copies `agents/*.md` into `~/.claude/agents/` and overwrites the same six files on re-runs. In a cloud container that install evaporates with the container, so offer `bash scripts/install-agents.sh --project` instead, which writes the six files to the repo's `.claude/agents/` for the user to commit. That is a change to their repo, so offer it once rather than running it unasked. Tell the user in one line what ran or what you are offering.

Every prompt to a pstack agent names this skill's base directory, whichever route spawned it. The agent reads `skills/poteto-mode/poteto-mode.md` and the leaf principle files from there.

## Model configuration

`skills/poteto-mode/references/model-roles.md` maps each role to a model and an effort tier. **setup-pstack** writes `~/.claude/pstack-models.md` to override any line. Read the override first when it exists.

## Requirements

The markdown needs nothing installed. Two playbooks, Babysit and Orchestrate, run bundled TypeScript on Node 24.2 or newer, and the scripts install their one dependency on first run. Babysit and Shipping expect the `gh` CLI.
"""

errors: list[str] = []


def frontmatter(path: pathlib.Path):
    text = path.read_text()
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    fm = {}
    for line in text[4:end].split("\n"):
        if ":" in line and not line.startswith((" ", "-", "#")):
            k, _, v = line.partition(":")
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1].replace('\\"', '"')
            fm[k.strip()] = v
    return fm, text[end + 5:]


def rewrite_skill_links(md: pathlib.Path, text: str) -> str:
    """`../arena/SKILL.md` becomes `../arena/arena.md` after the rename."""
    def fix(m):
        rel, frag = m.group(1), m.group(2) or ""
        target = (md.parent / rel).resolve()
        if target.name != "SKILL.md" or target.parent.parent != OUT / "skills":
            errors.append(f"{md.relative_to(OUT)}: link to a SKILL.md outside skills/: {rel}")
            return m.group(0)
        renamed = target.parent / f"{target.parent.name}.md"
        return f"]({os.path.relpath(renamed, md.parent)}{frag})"
    return re.sub(r"\]\(((?:\.\./)+(?:[\w-]+/)*SKILL\.md)(#[^)]*)?\)", fix, text)


def transform(md: pathlib.Path) -> None:
    text = md.read_text()
    text = re.sub(r"pstack:(?=[a-z-]+)", "", text)
    text = rewrite_skill_links(md, text)
    for old, new in PATCHES.get(md.relative_to(OUT).as_posix(), []):
        if text.count(old) != 1:
            errors.append(f"{md.relative_to(OUT)}: patch target not found exactly once: {old[:50]!r}")
            continue
        text = text.replace(old, new)
    md.write_text(text)


def index_line(name: str, description: str) -> str:
    return f"- **{name}** (`skills/{name}/{name}.md`). {description}"


# --- assemble the tree ---
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir(parents=True)

skills: dict[str, str] = {}
for src in sorted(p for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").exists()):
    fm, _ = frontmatter(src / "SKILL.md")
    name = src.name
    if fm is None or fm.get("name") != name or not fm.get("description"):
        errors.append(f"skills/{name}/SKILL.md: frontmatter must carry name '{name}' and a description")
        continue
    skills[name] = fm["description"]
    dst = OUT / "skills" / name
    shutil.copytree(src, dst, ignore=IGNORE)
    (dst / "SKILL.md").rename(dst / f"{name}.md")

agents: dict[str, dict] = {}
shutil.copytree(ROOT / "agents", OUT / "agents", ignore=IGNORE)
for ag in sorted((OUT / "agents").glob("*.md")):
    fm, _ = frontmatter(ag)
    if fm is None or fm.get("name") != ag.stem:
        errors.append(f"agents/{ag.name}: frontmatter must carry name '{ag.stem}'")
        continue
    agents[ag.stem] = fm

(OUT / "scripts").mkdir()
shutil.copy2(ROOT / "scripts" / "install-agents.sh", OUT / "scripts" / "install-agents.sh")

patched = set()
for md in sorted(OUT.rglob("*.md")):
    transform(md)
    patched.add(md.relative_to(OUT).as_posix())
for rel in PATCHES:
    if rel not in patched:
        errors.append(f"patch target file missing: {rel}")

# --- the router ---
principles = [n for n in skills if n.startswith("principle-")]
workflow = [n for n in skills if n not in principles and n not in ("poteto-mode", "setup-pstack")]
agent_rows = [
    f"| `{n}` | {fm.get('model', 'inherit')} | {fm.get('effort', 'default')} | {fm['description']} |"
    for n, fm in agents.items()
]
router = ROUTER.format(
    description=json.dumps(DESCRIPTION),
    entry=index_line("poteto-mode", skills["poteto-mode"]),
    workflow="\n".join(index_line(n, skills[n]) for n in workflow),
    principles="\n".join(index_line(n, skills[n]) for n in principles),
    setup=index_line("setup-pstack", skills["setup-pstack"]),
    agents="\n".join(agent_rows),
)
(OUT / "SKILL.md").write_text(router)

# --- validate the package the way claude.ai will ---
skill_mds = list(OUT.rglob("SKILL.md"))
if len(skill_mds) != 1:
    errors.append(f"expected exactly one SKILL.md, found {len(skill_mds)}")

fm, _ = frontmatter(OUT / "SKILL.md")
allowed = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
if fm is None:
    errors.append("SKILL.md: no parseable frontmatter")
else:
    try:
        import yaml
        block = router.split("\n---\n", 1)[0][4:]
        parsed = yaml.safe_load(block)
        if parsed.get("description") != DESCRIPTION:
            errors.append("SKILL.md: description does not round-trip through YAML")
    except ImportError:
        print("note: PyYAML not installed, skipped the strict YAML check")
    except yaml.YAMLError as exc:
        errors.append(f"SKILL.md: frontmatter is not valid YAML: {exc}")
    if set(fm) - allowed:
        errors.append(f"SKILL.md: frontmatter keys not allowed: {sorted(set(fm) - allowed)}")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", fm.get("name", "")):
        errors.append(f"SKILL.md: name must be kebab-case, got {fm.get('name')!r}")
    if len(DESCRIPTION) > 1024:
        errors.append(f"SKILL.md: description is {len(DESCRIPTION)} chars, max 1024")
    if "<" in DESCRIPTION or ">" in DESCRIPTION:
        errors.append("SKILL.md: description cannot contain angle brackets")

for md in sorted(OUT.rglob("*.md")):
    rel = md.relative_to(OUT)
    text = md.read_text()
    for m in re.finditer(r"pstack:[a-z-]+", text):
        errors.append(f"{rel}: plugin namespace survived: '{m.group(0)}'")
    for m in re.finditer(r"\]\((\.\.?/[^)#]+)(?:#[^)]*)?\)", text):
        if not (md.parent / m.group(1)).resolve().exists():
            errors.append(f"{rel}: broken link '{m.group(1)}'")

for name in skills:
    body = (OUT / "skills" / name / f"{name}.md").read_text()
    for ref in re.findall(r"`((?:references|playbooks|scripts)/[\w./-]+)`", body):
        if not (OUT / "skills" / name / ref).exists():
            errors.append(f"skills/{name}/{name}.md: references missing file '{ref}'")

for m in re.finditer(r"`(skills/[\w-]+/[\w-]+\.md|agents/[\w-]+\.md|scripts/[\w-]+\.sh)`", router):
    if not (OUT / m.group(1)).exists():
        errors.append(f"SKILL.md: names missing file '{m.group(1)}'")

if errors:
    print(f"{len(errors)} error(s):")
    for e in errors:
        print(f"  ERROR {e}")
    sys.exit(1)

# --- package ---
with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(OUT.rglob("*")):
        if path.is_file():
            zf.write(path, path.relative_to(OUT.parent))

print(f"sub-skills: {len(skills)}   agents: {len(agents)}   "
      f"router: {router.count(chr(10))} lines   description: {len(DESCRIPTION)} chars")
print(f"{OUT}")
print(f"{ZIP}  ({ZIP.stat().st_size // 1024} KB)")
