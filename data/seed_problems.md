<!-- Handwritten natural-language seed problems only; no MiniZinc. -->

## p01 — PowerGen capacity expansion
- id: p01
- family: capacity_expansion
- type: optimisation

### Problem

Plan long-term power generation building to meet future demand over a horizon of decades.

Three plant types can be built:

- Nuclear: costs 10 billion, lasts 60 years (6 decades), generates 4 GW while operating.
- Coal: costs 1 billion, lasts 20 years (2 decades), generates 1 GW while operating.
- Solar: costs 2 billion, lasts 30 years (3 decades), generates 1 GW while operating.

Decide how many plants of each type to build in each decade. A plant built in a given decade starts contributing in that decade and keeps contributing for its lifetime (in decades), then stops.

In every decade, total available generation must cover expected demand. Available generation in a decade is existing capacity for that decade plus output from every plant that is still within its lifetime.

Additional rules:

- In any decade, nuclear generation must be at most 40% of all generation available that decade.
- In every decade, solar generation must be at least 20% of all generation available that decade.
- Over the whole plan, the total number of coal plant-decades is at most 10: if you add up, for each decade, how many coal plants are operating in that decade, that sum must be ≤ 10.

Find a plan with minimal total building cost (sum of construction costs of all plants built).

### Instance data

- Number of decades T = 10
- Expected demand e (GW) by decade: 25, 25, 30, 25, 20, 20, 15, 15, 15, 12
- Existing capacity a (GW) by decade: 18, 15, 12, 8, 4, 3, 2, 0, 0, 0

### Constraint inventory
- C1: In each decade, available generation (existing capacity plus operating plants) meets expected demand
- C2: In each decade, nuclear share of available generation is at most 40%
- C3: In each decade, solar share of available generation is at least 20%
- C4: Sum over decades of the number of operating coal plants that decade is at most 10
- C5: Plant lifetimes are respected (nuclear 6 decades, coal 2, solar 3) from the build decade inclusive

### Objective
- sense: minimize
- quantity: total building cost in billions
