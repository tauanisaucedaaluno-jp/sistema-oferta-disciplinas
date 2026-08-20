---
name: skill-creator
description: >-
  Create new skills, modify and improve existing skills, and measure skill performance. Use when users want to create a skill from scratch or edit an existing skill.
---

# Skill Creator

Use this skill to help the user extend the agent's capabilities by writing new `SKILL.md` files.

## Skill Creation Workflow

1. **Understand the Goal**: Ask the user what workflow eles querem automatizar.
2. **Determine the Trigger**: Formulate a strong, third-person `description` for the YAML frontmatter. This is crucial for the agent's routing logic.
3. **Draft the Instructions**: Write clear, imperative steps in Markdown. Use progressive disclosure se a skill for complexa.
4. **File Placement**: Ensure the skill is saved correctly in `.agents/skills/<skill-name>/SKILL.md`.
5. **Validation**: Review the generated YAML frontmatter to ensure it contains both `name` e `description`.
