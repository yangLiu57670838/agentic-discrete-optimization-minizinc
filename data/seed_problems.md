<!-- Handwritten natural-language seed problems only; no MiniZinc. -->

## p01 — Hospital staff rostering and surgery scheduling (instance A: one shift type)
- id: p01
- family: rostering_scheduling
- type: optimisation

### Problem

A hospital needs a staff roster and a schedule of planned elective surgeries over a horizon of 14 consecutive days, numbered Day 0 to Day 13. The two parts are linked: every surgery needs certain staff to be on duty while it takes place.

**Part 1 — Staff rostering.**

There is a set of staff members (employees). There is a set of shift types; each shift type has a length in minutes. For each employee and each day, decide which shift type the employee works that day, or that the employee is free (not working) that day.

Rules (hard):

- Each employee works at most one shift per day (one shift type or free).
- Some shift types cannot directly follow another shift type. For each shift type there is a (possibly empty) set of shift types that are forbidden on the very next day after working that shift type. (Example: a night shift may not be followed by an early shift the next day.)
- Each employee has an individual contract:
  - the total time of all shifts assigned to the employee over the horizon (sum of the lengths of the shifts worked) must be at least the employee's minimum time and at most the employee's maximum time (both in minutes);
  - for each shift type, the number of shifts of that type assigned to the employee over the horizon must not exceed the employee's maximum for that shift type;
  - the number of weekends the employee works must not exceed the employee's maximum number of weekends. The weekends of the horizon are given as pairs of days. An employee works a weekend if they are assigned a shift on at least one of that weekend's days.

Preferences (soft): employees submit requests. Each request names an employee, a day, a shift type, whether it is an ON request or an OFF request, and a weight. An ON request is violated if the employee is *not* assigned that shift type on that day; an OFF request is violated if the employee *is* assigned that shift type on that day. Each violated request costs its weight. The request penalty is the sum of the weights of all violated requests.

Staffing (soft): for every day and every shift type, a required cover (number of staff) is given. The number of staff rostered on that shift on that day is the number of employees assigned that shift type on that day (every rostered employee counts, regardless of role). If fewer staff than required are rostered, each missing person costs the understaffing cost for that day and shift; if more are rostered than required, each extra person costs the overstaffing cost for that day and shift. The staffing penalty is the sum of these costs over all days and shift types.

**Part 2 — Surgery scheduling.**

Planned elective surgeries happen only during one designated shift type each day (the surgery shift). Each employee has exactly one role (e.g. Surgeon, Surgical nurse, Anaesthetist, Nurse). Each surgery (operation) has a set of required roles, a planned duration in minutes, and a set of possible days on which it may take place. The hospital has a given number of identical operating theatres.

For each operation decide its day and its starting time, measured in minutes from the start of the surgery shift on that day, and decide which staff attend it. Rules (hard):

- Every operation is scheduled exactly once, on one of its possible days.
- An operation starts and finishes within the surgery shift of its day: starting minute ≥ 0 and starting minute + duration ≤ length of the surgery shift.
- For every role an operation requires, at least one employee with that role attends the operation for its entire duration, and every attending employee must be rostered on the surgery shift on that day.
- An employee cannot attend two operations whose time intervals overlap on the same day.
- At any moment on any day, the number of operations in progress is at most the number of operating theatres (theatres are interchangeable).

The surgery schedule adds no cost; it only has to be feasible together with the roster.

**Goal.** Minimise the sum of the request penalty and the staffing penalty, subject to all hard rules above (both parts).

### Instance data

- Horizon: 14 days, Day 0 .. Day 13.
- Weekends: two weekends, {Day 5, Day 6} and {Day 12, Day 13}.
- Shift types: one shift type, D, length 480 minutes. No shift type is forbidden after D.
- Employees: 8, named E1 .. E8.
- Contract limits (identical for all 8 employees):
  - maximum total time 4320 minutes; minimum total time 3360 minutes;
  - maximum number of D shifts over the horizon 14;
  - maximum number of weekends worked 1.
- Required cover for shift D by day (Day 0 .. Day 13): 5, 7, 6, 4, 5, 5, 5, 6, 7, 4, 2, 5, 6, 4.
- Understaffing cost: 100 per missing person, for every day and shift.
- Overstaffing cost: 1 per extra person, for every day and shift.
- Requests (26 in total):

| # | Employee | Day | Shift | Type | Weight |
|---|---|---|---|---|---|
| 1 | E1 | 2 | D | ON | 2 |
| 2 | E1 | 3 | D | ON | 2 |
| 3 | E2 | 0 | D | ON | 3 |
| 4 | E2 | 1 | D | ON | 3 |
| 5 | E2 | 2 | D | ON | 3 |
| 6 | E2 | 3 | D | ON | 3 |
| 7 | E2 | 4 | D | ON | 3 |
| 8 | E3 | 0 | D | ON | 1 |
| 9 | E3 | 1 | D | ON | 1 |
| 10 | E3 | 2 | D | ON | 1 |
| 11 | E3 | 3 | D | ON | 1 |
| 12 | E3 | 4 | D | ON | 1 |
| 13 | E4 | 8 | D | ON | 2 |
| 14 | E4 | 9 | D | ON | 2 |
| 15 | E6 | 0 | D | ON | 2 |
| 16 | E6 | 1 | D | ON | 2 |
| 17 | E8 | 9 | D | ON | 1 |
| 18 | E8 | 10 | D | ON | 1 |
| 19 | E8 | 11 | D | ON | 1 |
| 20 | E8 | 12 | D | ON | 1 |
| 21 | E8 | 13 | D | ON | 1 |
| 22 | E3 | 12 | D | OFF | 1 |
| 23 | E3 | 13 | D | OFF | 1 |
| 24 | E6 | 8 | D | OFF | 3 |
| 25 | E8 | 2 | D | OFF | 3 |
| 26 | E8 | 3 | D | OFF | 3 |

- Roles: Surgeon, SurgicalNurse, Anaesthetist, Nurse.
- Role of each employee: E1 Surgeon; E2 SurgicalNurse; E3 SurgicalNurse; E4 Anaesthetist; E5, E6, E7, E8 Nurse.
- Surgery shift: D.
- Operating theatres: 1.
- Operations: 10 (unnamed, Op1 .. Op10). Every operation requires the roles {Surgeon, SurgicalNurse, Anaesthetist}, lasts 140 minutes, and may be scheduled on any non-weekend day of the horizon, i.e. Days 0, 1, 2, 3, 4, 7, 8, 9, 10, 11.

### Constraint inventory
- C1: Each employee is assigned at most one shift per day (a shift type or free)
- C2: For each employee and consecutive pair of days, the next day's shift type is not in the forbidden-successor set of the previous day's shift type
- C3: For each employee, total minutes of assigned shifts is between the employee's minimum and maximum total time
- C4: For each employee and shift type, number of assigned shifts of that type is at most the employee's maximum for that type
- C5: For each employee, number of weekends on which they work at least one day is at most the employee's maximum weekends
- C6: Request penalty equals the sum of weights of violated requests (ON violated if the shift is not assigned, OFF violated if it is)
- C7: Staffing penalty equals, over all days and shift types, understaffing cost × shortfall below cover plus overstaffing cost × excess above cover
- C8: Every operation is scheduled on exactly one of its possible days
- C9: Every operation starts at minute ≥ 0 and finishes by the end of the surgery shift (start + duration ≤ shift length)
- C10: For each required role of an operation, an employee of that role attends it, and all attending employees are rostered on the surgery shift that day
- C11: No employee attends two operations that overlap in time on the same day
- C12: At any time on any day, the number of operations in progress is at most the number of theatres

### Objective
- sense: minimize
- quantity: request penalty + staffing penalty
