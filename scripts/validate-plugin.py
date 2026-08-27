#!/usr/bin/env python3
"""Validate the pstack Claude Code plugin.

Checks the manifest, every SKILL.md and agent frontmatter, cross-file
references, and that no Cursor-era construct survived the port.

Usage: python3 scripts/validate-plugin.py [plugin-root]
Exit code 0 when clean, 1 when any error is found.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                    pathlib.Path(__file__).resolve().parent.parent)

errors: list[str] = []
warnings: list[str] = []

VALID_MODELS = {"opus", "sonnet", "haiku", "fable", "inherit"}
VALID_EFFORT = {"low", "medium", "high", "xhigh", "max"}

# Constructs that mean the port missed something.
BANNED = {
    r"\.cursor/": "Cursor config path",
    r"cursor-team-kit": "unbundled Cursor plugin dependency",
    r"\bdeslop\b": "skill that does not exist here",
    r"\bcreate-skill\b": "Cursor built-in that does not exist here",
    r"\bBugbot\b": "Cursor product name",
    r"/add-plugin\b": "Cursor install command (use /plugin install)",
    r"\bgeneralPurpose\b": "Cursor subagent type",
    r"`Task` (?:tool|call)": "Cursor tool name (use Agent)",
    r"\bAskQuestion\b": "Cursor tool name (use AskUserQuestion)",
    r"disable-model-invocation": "Cursor frontmatter key",
    r"grok-4|gpt-5\.|claude-fable-5-|claude-opus-5-": "Cursor model slug",
    r"agent-transcripts": "Cursor transcript directory",
}


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
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm, text[end + 5:]


# --- manifest ---
manifest_path = ROOT / ".claude-plugin" / "plugin.json"
if not manifest_path.exists():
    errors.append(".claude-plugin/plugin.json is missing")
else:
    try:
        manifest = json.loads(manifest_path.read_text())
        for key in ("name", "description"):
            if key not in manifest:
                errors.append(f"manifest: missing required key '{key}'")
        # Claude Code compares version strings, not contents. A declared
        # version that does not change leaves every installed copy pinned to
        # the cache while `claude plugin update` reports users up to date.
        # With the field absent the commit SHA becomes the version, so every
        # push reaches everyone.
        if "version" in manifest:
            errors.append(
                "manifest: remove 'version'. It pins installed users to the "
                "cached copy until it is bumped; omitting it makes the commit "
                "SHA the version so every push ships.")
        for rel in manifest.get("agents", []):
            if not (ROOT / rel.lstrip("./")).exists():
                errors.append(f"manifest: agents entry not found: {rel}")
        # Agents, skills and commands are auto-discovered from their directories.
        # Listing them again registers each one twice, so the manifest stays quiet.
        for key in ("agents", "skills", "commands"):
            if key in manifest:
                warnings.append(
                    f"manifest: '{key}' duplicates auto-discovery of {key}/")
    except json.JSONDecodeError as exc:
        errors.append(f"manifest: invalid JSON: {exc}")

# --- marketplace ---
# Without this, `/plugin marketplace add <path>` has nothing to read and the
# plugin cannot be installed from a local checkout at all.
market_path = ROOT / ".claude-plugin" / "marketplace.json"
if not market_path.exists():
    errors.append(".claude-plugin/marketplace.json is missing "
                  "(needed to install from a local checkout)")
else:
    try:
        market = json.loads(market_path.read_text())
        for key in ("name", "owner", "plugins"):
            if key not in market:
                errors.append(f"marketplace: missing required key '{key}'")
        for entry in market.get("plugins", []):
            src = entry.get("source")
            if not isinstance(src, str):
                continue
            if not (ROOT / src / ".claude-plugin" / "plugin.json").exists():
                errors.append(
                    f"marketplace: source '{src}' has no .claude-plugin/plugin.json")
    except json.JSONDecodeError as exc:
        errors.append(f"marketplace: invalid JSON: {exc}")

# --- skills ---
skill_names = set()
skill_files = sorted(ROOT.glob("skills/*/SKILL.md"))
for sk in skill_files:
    rel = sk.relative_to(ROOT)
    fm, body = frontmatter(sk)
    if fm is None:
        errors.append(f"{rel}: no parseable YAML frontmatter")
        continue
    name = fm.get("name")
    if not name:
        errors.append(f"{rel}: frontmatter missing 'name'")
    elif name != sk.parent.name:
        errors.append(f"{rel}: name '{name}' != directory '{sk.parent.name}'")
    else:
        skill_names.add(name)
    if not fm.get("description"):
        errors.append(f"{rel}: frontmatter missing 'description'")
    elif len(fm["description"]) < 20:
        warnings.append(f"{rel}: description looks too short to route on")

    # referenced sibling files must exist
    for ref in re.findall(r"`((?:references|playbooks|scripts)/[\w./-]+)`", body):
        if not (sk.parent / ref).exists():
            errors.append(f"{rel}: references missing file '{ref}'")

# --- agents ---
agent_names = set()
for ag in sorted(ROOT.glob("agents/*.md")):
    rel = ag.relative_to(ROOT)
    fm, _ = frontmatter(ag)
    if fm is None:
        errors.append(f"{rel}: no parseable YAML frontmatter")
        continue
    if not fm.get("name"):
        errors.append(f"{rel}: frontmatter missing 'name'")
    else:
        agent_names.add(fm["name"])
    if not fm.get("description"):
        errors.append(f"{rel}: frontmatter missing 'description'")
    model = fm.get("model")
    if model and model not in VALID_MODELS:
        errors.append(f"{rel}: invalid model '{model}' (want {sorted(VALID_MODELS)})")
    effort = fm.get("effort")
    if effort and effort not in VALID_EFFORT:
        errors.append(f"{rel}: invalid effort '{effort}' (want {sorted(VALID_EFFORT)})")

# --- cross references ---
all_md = [p for p in ROOT.rglob("*.md") if ".git" not in p.parts]
for md in all_md:
    rel = md.relative_to(ROOT)
    text = md.read_text()

    # The README documents what each Cursor construct became, so it names them on purpose.
    if rel.as_posix() != "README.md":
        for pattern, why in BANNED.items():
            for m in re.finditer(pattern, text):
                line = text[:m.start()].count("\n") + 1
                errors.append(f"{rel}:{line}: {why}: '{m.group(0)}'")

    # `/plugin install pstack` without a marketplace fails: the name is only
    # unique within one. This check runs on the README too, which the ban
    # sweep above skips.
    for m in re.finditer(r"/plugin install pstack(?!@)", text):
        line = text[:m.start()].count("\n") + 1
        errors.append(f"{rel}:{line}: install needs a marketplace "
                      "(use /plugin install pstack@pstack-claude)")

    # pstack: subagent references must resolve to a real agent.
    # `pstack:panel-<lens>` and friends are documented templates, not references.
    for m in re.finditer(r"pstack:([a-z-]+)(?!<)", text):
        if m.group(1).endswith("-"):
            continue
        if m.group(1) not in agent_names:
            line = text[:m.start()].count("\n") + 1
            errors.append(f"{rel}:{line}: unknown agent 'pstack:{m.group(1)}'")

    # relative markdown links must resolve
    for m in re.finditer(r"\]\((\.\.?/[^)#]+)\)", text):
        target = (md.parent / m.group(1)).resolve()
        if not target.exists():
            line = text[:m.start()].count("\n") + 1
            errors.append(f"{rel}:{line}: broken link '{m.group(1)}'")

# --- report ---
print(f"skills: {len(skill_files)}   agents: {len(agent_names)}   markdown files: {len(all_md)}")
if warnings:
    print(f"\n{len(warnings)} warning(s):")
    for w in warnings:
        print(f"  warn  {w}")
if errors:
    print(f"\n{len(errors)} error(s):")
    for e in errors:
        print(f"  ERROR {e}")
    sys.exit(1)
print("\nOK: plugin validates clean.")
