---
type: bet
tags:
  - bet
bet: {{bet}}
owner: {{owner}}
area: {{area}}
cycle: {{cycle}}
appetite: {{appetite}}
cycle_start: {{cycle_start}}
cycle_end: {{cycle_end}}
started: {{started}}
shipped: {{shipped}}
dropped: {{dropped}}
outcome: {{outcome}}
source: {{source}}
status:
status_reason:
delivery:
kpi_result:
last_signal:
---
# {{bet}}

<!-- status, status_reason, delivery, kpi_result and last_signal are written by
bets.py score and overwritten on each run. Every other field is yours. -->

## Problem

{{problem}}

## Milestones

<!-- - [ ] #milestone What done looks like 📅 YYYY-MM-DD   (tick when done) -->
{{milestones}}

## KPIs

<!-- - #kpi Metric name [baseline:: 40] [target:: 25] [read_by:: YYYY-MM-DD] -->
{{kpis}}

## Readings

<!-- - YYYY-MM-DD #reading Metric name [value:: 32]   (newest last) -->
{{readings}}

## Blockers

<!-- - [ ] #blocker What is in the way [opened:: YYYY-MM-DD]   (tick when cleared) -->
{{blockers}}

## Signals

<!-- - YYYY-MM-DD One line on what happened. Add #off-track or #on-track when the owner calls it. -->
{{signals}}

## Notes

