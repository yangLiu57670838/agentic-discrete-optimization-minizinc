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

## p02 — Retail shift roster
- id: p02
- family: rostering
- type: optimisation

### Problem

Build a weekly retail shift roster for a fixed set of staff.

Each person may be assigned to shifts on each day of the week. The shifts are opening, morning, lunch, afternoon, and closing. The days are Monday through Sunday.

For every person, day, and shift, there is a preference score. A score of zero means that person must not be assigned that shift on that day. Otherwise the score is a positive integer; higher means more preferred.

Decide which shifts each person works on each day. A person may work more than one shift on the same day, but at most two shifts per day.

Rules (all apply per day unless stated otherwise):

- Each person works at most two shifts that day.
- If a person works closing, they cannot also work afternoon that day.
- If a person works morning, they cannot also work opening that day.
- If a person works closing, they cannot also work opening that day.
- Exactly one person must be assigned to opening.
- Exactly one person must be assigned to closing.
- At least two people must be assigned to morning.
- At least two people must be assigned to lunch.
- At least three people must be assigned to afternoon.
- Counting every person-shift assignment that day, at least eight assignments must be to opening, morning, or lunch combined.
- Counting every person-shift assignment that day, at least eight assignments must be to lunch, afternoon, or closing combined.
- A person cannot be assigned a shift on a day when their preference for that shift is zero.

Maximize the total sum of preference scores over all assigned person-day-shift triples in the week.

### Instance data

- People (6): Ann, Ben, Cal, Dee, Eva, Fay
- Days (7): Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday
- Shifts (5): opening, morning, lunch, afternoon, closing
- Preference scores are integers from 0 to 10
- Default: if a person-day-shift is not listed below, its preference is 7
- Unavailable slots (preference 0):
  - Ann: Saturday opening, Sunday opening, Sunday closing
  - Ben: Monday afternoon, Tuesday afternoon, Wednesday afternoon
  - Cal: Thursday morning, Friday morning, Saturday morning
  - Dee: Sunday lunch, Sunday afternoon
  - Eva: Monday opening, Tuesday opening, Wednesday opening
  - Fay: Saturday closing, Sunday closing
- Higher-preference highlights (optional soft peaks, still subject to rules above):
  - Ann: Friday closing = 10, Thursday lunch = 9
  - Ben: Saturday morning = 10, Sunday morning = 9
  - Cal: Wednesday afternoon = 10, Thursday afternoon = 9
  - Dee: Monday lunch = 10, Tuesday lunch = 9
  - Eva: Friday afternoon = 10, Saturday afternoon = 9
  - Fay: Monday closing = 10, Tuesday closing = 9

### Constraint inventory
- C1: Each person works at most two shifts per day
- C2: Closing and afternoon cannot both be assigned to the same person on the same day
- C3: Morning and opening cannot both be assigned to the same person on the same day
- C4: Closing and opening cannot both be assigned to the same person on the same day
- C5: Each day, exactly one opening shift and exactly one closing shift are staffed
- C6: Each day, at least two morning shifts and at least two lunch shifts are staffed
- C7: Each day, at least three afternoon shifts are staffed
- C8: Each day, opening plus morning plus lunch assignments total at least eight
- C9: Each day, lunch plus afternoon plus closing assignments total at least eight
- C10: No assignment where the preference score is zero

### Objective
- sense: maximize
- quantity: total sum of preference scores of all assigned shifts

## p03 — Hidato grid path
- id: p03
- family: puzzle
- type: satisfaction

### Problem

Hidato is a fill-in puzzle on a rectangular grid. The player is given an n by m grid that is only partly filled. The task is to put every integer from 1 through n times m into the cells so that the grid is completely filled.

Each of those numbers appears in exactly one cell. Consecutive numbers k and k+1 must sit in cells that touch: horizontally, vertically, or diagonally (the eight neighbouring cells around a cell, including corners). Numbers that are not consecutive have no adjacency requirement beyond using each value once.

Some cells already contain a clue: a fixed number that must stay in that cell. Other cells are blank and must be filled. There is no extra rule that the first or last number of the range must appear among the clues.

Find any filling that obeys the clues and the consecutive-neighbour rule.

### Instance data

- Grid size: 6 rows by 6 columns
- Numbers to place: 1 through 36
- Clues (row by row, left to right; blank means the cell is free):
  - Row 1: 26, 28, 29, 31, 33, 34
  - Row 2: blank, blank, blank, 30, blank, blank
  - Row 3: 3, 1, 22, blank, 36, blank
  - Row 4: 4, 2, blank, blank, blank, 18
  - Row 5: blank, 8, blank, 13, 17, blank
  - Row 6: 7, blank, blank, 11, 14, 15

### Constraint inventory
- C1: Every cell gets one integer from 1 through 36
- C2: Each integer from 1 through 36 appears in exactly one cell
- C3: A given clue stays in its cell
- C4: For every k from 1 through 35, the cells holding k and k+1 share an edge or a corner

### Objective
- sense: satisfy
