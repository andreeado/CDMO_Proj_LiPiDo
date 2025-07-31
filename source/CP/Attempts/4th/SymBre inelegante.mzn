% Sports Tournament Scheduling Problem
% Each team plays against every other team exactly once
% Games are scheduled across weeks and periods
include "alldifferent.mzn";

% Parameters
int: n;  % Replace with your desired number of teams
int: nWeeks = n - 1;
int: nPeriods = n div 2;
int: nMatches = (n - 1) * n div 2;

% Function to calculate match number
function int: match_number(int: t1, int: t2) = 
  (t1 - 1) * n - (t1 * (t1 - 1)) div 2 + (t2 - t1);

% Sets
set of int: Teams = 1..n;
set of int: Weeks = 1..nWeeks;
set of int: Periods = 1..nPeriods;
set of int: Matches = 1..nMatches;

% Match table
array[Matches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_match = [match_number(t1, t2) | t1 in Teams, t2 in Teams where t1 < t2];

% Decision variables
array[Weeks, Periods] of var Matches: match_vars;
array[Weeks, Periods] of var Teams: x;
array[Weeks, Periods] of var Teams: y;

% Flattened match assignments: 2 teams per period per week
array[1..2*nWeeks, 1..nPeriods] of var Teams: all_assignments;

% Channeling: link match number ↔ team pairs
constraint forall(w in Weeks, p in Periods) (
  exists(i in Matches) (
    x[w, p] = table_t1[i] /\
    y[w, p] = table_t2[i] /\
    match_vars[w, p] = table_match[i]
  )
);

% Link to flat array for speed
constraint forall(w in Weeks, p in Periods) (
  all_assignments[w, p] = x[w, p] /\
  all_assignments[nWeeks + w, p] = y[w, p]
);

% All matches must be scheduled exactly once
constraint alldifferent(match_vars);

% Each team plays only once per week
constraint forall(w in Weeks) (
  alldifferent([x[w, p] | p in Periods] ++ [y[w, p] | p in Periods])
);

% Participation pattern: team t plays either once or twice per period
array[1..nPeriods, Teams] of int: counts = 
  array2d(1..nPeriods, Teams,
    [ if t = 2*p - 1 \/ t = 2*p then 1 else 2 endif | p in 1..nPeriods, t in Teams ]);

% Faster alternative to global_cardinality using count
constraint forall(p in 1..nPeriods, t in Teams) (
  count([ all_assignments[w, p] | w in 1..2*nWeeks ], t) = counts[p, t]
);

% Team 1 plays in specific periods each week
constraint forall(w in 1..nWeeks) (
  x[w, (w + 2) div 2] = 1
);

% Order constraint to break symmetry
constraint forall(p in 2..nPeriods) (
  y[2*p - 2, p] < y[2*p - 1, p]
);

% Search strategy (can improve Gecode performance)
solve satisfy;

% Output formatting
output [
  "Schedule of Matches (week x period):\n"
] ++ [
  "Week " ++ show(w) ++ ":\n" ++
  concat([
    "  Period " ++ show(p) ++ ": Team " ++ show(x[w, p]) ++ 
    " vs Team " ++ show(y[w, p]) ++ " (Match #" ++ show(match_vars[w, p]) ++ ")\n"
  | p in Periods])
| w in Weeks];
