---
type: concept
title: "Skill Discovery"
complexity: intermediate
domain: "agent skills"
aliases: ["find-skills"]
created: 2026-11-26
updated: 2026-11-26
tags:
  - concept
  - agent-skills
status: seed
related:
  - "[[Compounding Knowledge]]"
sources:
  - "https://www.uber.com/us/en/blog/optimizing-ubers-agent-skills/"
---

# Skill Discovery

## Definition

Skill discovery is the step where an agent picks the right saved skill for the job you are doing, instead of you having to remember which skill exists. You describe the task; the agent searches your skill library, ranks the matches, and runs the best one in the same workflow.

## How It Works

1. **Ask.** You describe what you are trying to do, in plain words.
2. **Search.** A find-skills step matches the request against every skill's name and "when to use" description.
3. **Rank.** Matches are ordered by a quality score:
   - **Evals:** does the skill have tests or evals that pass?
   - **Run counts:** how often it has actually been used recently.
   - **Fit:** how well it matches this request and the current session.
4. **Run.** The top skill runs right away, without leaving the workflow.
5. **Log.** Each run adds one line to a run log, which feeds the next ranking.
6. **Prune.** Skills with no runs over a set window (30 days) show up on an unused list: fix them, merge them, or retire them.

## Why It Matters

A skill library only compounds if skills get found and used. Without discovery, skills pile up and are forgotten; with it, every new skill is reachable from the moment it lands, and the run log shows which ones earn their place.

## Examples

- In my Rig (saixso/rig): find-skills, a run log, ranking, and an unused-skills report.
- Uber's skills marketplace (5,000+ skills): a find-skills skill finds a quality skill and runs it within the workflow; skills are ranked with evals and run counts into a skill quality score. Uber also sorts skills into always-on, core and domain tiers and uses an internal context graph to answer "skills my peers are using that I'm not". Both are skipped at personal scale in a private Rig.

## Connections

- [[Compounding Knowledge]]: discovery is what makes a growing skill library pay off.

## Sources

- Uber Engineering, "How Uber Evals 1 Million Agent Skill Invocations a Month" (2026-11-23): https://www.uber.com/us/en/blog/optimizing-ubers-agent-skills/
