### Authoring or modifying a skill

**You own the skill's voice.** Agent-facing prose has a higher bar than human prose; unhelpful sentences become instructions.

1. **Decide it should be a skill at all.** A durable fact belongs in memory. A rule that fires on an event belongs in a hook (`/update-config`). A rule a machine can check belongs in a lint or a test. Reach for a skill when the thing being captured is a *procedure with judgment in it*. See **principle-encode-lessons-in-structure**.
2. **Place it.** A skill lives at `<root>/skills/<kebab-name>/SKILL.md`. Project skills go in `.claude/skills/`, personal skills in `~/.claude/skills/`, plugin skills in the plugin's `skills/`. The directory name is the invocation name, so `skills/blast-radius/` is `/blast-radius`.
3. **Write the frontmatter.** Only two keys are required and both carry weight:
   - `name`. Kebab-case, and it must match the directory name.
   - `description`. This is the only part loaded into every session, and it is the entire basis on which the skill gets picked. Write it as *when to use this*, in the user's words, not as *what this is*. Name the literal phrasings that should trigger it. A description that describes the skill's contents instead of its trigger is the single commonest reason a good skill never fires.
4. **Write the body.** Everything below the frontmatter loads only once the skill is invoked, so it can be long, but every line still has to earn its place.
   - Tell it to do the thing. Skip the reason unless the rule is confusing without one.
   - Number the steps when order matters. A step someone might skip needs the consequence attached.
   - Push detail into `references/` and name the file at the point of use. The body stays scannable; the reference carries the depth.
   - Delegate to other skills by name; don't restate their rules.
   - Point at structural sources (types, READMEs, config). Hardcoded details go stale.
5. **Validate.** Frontmatter parses as YAML. `name` matches the directory. Every referenced file exists (check the relative paths; a broken `references/foo.md` is invisible until the skill runs). Cross-skill links resolve.
6. **Test it, two ways.** Does it *trigger*? Say the things a user would really say and check the skill fires; if it doesn't, the description is wrong, not the body. Does it *work*? Run it on a real task. For structural skills, write the test cases. For subjective ones (`-mode` skills, voice, taste), skip the benchmark and vibe-check with the user instead. The Eval playbook (`eval.md`) covers a blinded comparison when a change is contested.
7. Run **Opening a PR**.

When in doubt, delete; prose earns its keep by changing a decision. Match tone to scope. A workflow you keep hitting but isn't captured is a proposal for a new skill.

**Reply:** summary of the skill, key design decisions, what you did to check it triggers and works.
