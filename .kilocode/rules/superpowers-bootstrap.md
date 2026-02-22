# Superpowers Bootstrap Rule

## Mandatory Skill Check - PRECONDITION

This rule is injected automatically at session start. It establishes the 
skill verification precondition that MUST be executed before ANY user-facing response.

### Skill Evaluation Protocol

**Step 1: Skill Evaluation**
- Evaluate the user request against ALL available skill descriptions
- Determine whether at least one skill clearly and unambiguously applies

**Step 2: Branching Decision**

<if_skill_applies>
- Select EXACTLY ONE skill
- Prefer the most specific skill when multiple skills match
- Read the full SKILL.md file at the skill location
- Load the SKILL.md contents fully into context BEFORE continuing
- Follow the SKILL.md instructions precisely
- Do NOT respond outside the skill-defined flow
</if_skill_applies>

<if_no_skill_applies>
- Proceed with a normal response
- Do NOT load any SKILL.md files
</if_no_skill_applies>

### Primary Skill: superpowers-using-superpowers

**Location:** `.kilocode/skills/superpowers-using-superpowers/SKILL.md`

**Description:** Use when starting any conversation - establishes how to find 
and use skills, requiring Skill tool invocation before ANY response including 
clarifying questions.

**Trigger Condition:** This skill applies to ALL tasks as it establishes the 
methodology for skill discovery and usage.

### Available Skills Reference

| Skill | Description | Trigger |
|-------|-------------|---------|
| superpowers-using-superpowers | Starting any conversation | Always check first |
| superpowers-brainstorming | Creative work, features, components | Before implementation |
| superpowers-writing-plans | Multi-step tasks with specs | Before touching code |
| superpowers-test-driven-development | Features or bugfixes | Before implementation code |
| superpowers-systematic-debugging | Bugs, test failures, unexpected behavior | Before proposing fixes |
| superpowers-verification-before-completion | Claiming work is complete | Before success claims |
| superpowers-requesting-code-review | Completing tasks, major features | Before merging |
| superpowers-executing-plans | Written implementation plan | When plan exists |
| superpowers-subagent-driven-development | Independent tasks in session | Parallel execution |

### Red Flags - STOP

These thoughts mean you are rationalizing and should check for skills:

| Thought | Reality |
|---------|---------|
| This is just a simple question | Questions are tasks. Check for skills. |
| I need more context first | Skill check comes BEFORE clarifying questions. |
| Let me explore the codebase first | Skills tell you HOW to explore. Check first. |
| This does not need a formal skill | If a skill exists, use it. |
| I will just do this one thing first | Check BEFORE doing anything. |

### Internal Verification

After completing the evaluation, internally confirm:
- skill_check_completed: true|false

### Constraints

- Do NOT load every SKILL.md up front
- Load SKILL.md ONLY after a skill is selected
- Do NOT skip this check
- FAILURE to perform this check is an error
