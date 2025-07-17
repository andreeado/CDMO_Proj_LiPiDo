% Sports Tournament Scheduling Problem
% Each team plays against every other team exactly once
% Games are scheduled across weeks and periods
include "alldifferent.mzn";
include "global_cardinality.mzn";

% Input parameter: number of teams
int: n;

% Derived parameters
int: nWeeks = n - 1;              % Number of weeks in the tournament
int: nPeriods = n div 2;          % Number of periods (games) per week
int: nMatches = (n - 1) * n div 2;      % Total number of matches

% Precomputed match numbers for all team pairs
% match_numbers[t1, t2] gives the match number for teams t1 and t2 (where t1 < t2)
function int: match_number(int: t1, int: t2) = 
  (t1 - 1) * n - (t1 * (t1 - 1)) div 2 + (t2 - t1);

array[1..n, 1..n] of int: match_numbers = 
  array2d(1..n, 1..n, [
    if t1 < t2 then 
      match_number(t1,t2)
    else 
      0  % Invalid pairing (t1 >= t2)
    endif
    | t1 in 1..n, t2 in 1..n
  ]);

% Sets for indexing
set of int: Teams = 1..n;
set of int: Matches = 1..nMatches;

% Decision variables (1-indexed)
% m[w,p] is the match number scheduled at week w, period p
array[1..nWeeks, 1..nPeriods] of var Matches: m;
% x[w,p] is the first team playing at week w, period p
array[1..nWeeks, 1..nPeriods] of var Teams: x;
% y[w,p] is the second team playing at week w, period p
array[1..nWeeks, 1..nPeriods] of var Teams: y;

% 0. Link the team variables (x,y) with match numbers (m) using precomputed array
% For each scheduled match, ensure the teams and match number are consistent
constraint forall(w in 1..nWeeks, p in 1..nPeriods) (
  % Ensure x[w,p] < y[w,p] to maintain ordering
  x[w,p] < y[w,p] /\
  % Match number must correspond to the teams playing (using precomputed array)
  m[w,p] = match_numbers[x[w,p], y[w,p]]
);

% Constraints
% 1. All matches must be different (each pair of teams plays exactly once)
constraint alldifferent(m);

% 2. Each week, all teams must be different (every team plays exactly once per week)
constraint forall(w in 1..nWeeks) (
  alldifferent([x[w,p] | p in 1..nPeriods] ++ [y[w,p] | p in 1..nPeriods])
);

% 3. Symmetry breaking constraints to reduce search space
% 3a. In period k, teams 2k-1 and 2k play exactly once, all others play twice
array[1..nPeriods, Teams] of int: counts =
  array2d(1..nPeriods, Teams,
    [ if t = 2*p - 1 \/ t = 2*p then 1 else 2 endif | p in 1..nPeriods, t in Teams ]);

constraint forall(p in 1..nPeriods) (
  global_cardinality(
    [x[w,p] | w in 1..nWeeks] ++ [y[w,p] | w in 1..nWeeks], 
    [t | t in Teams], 
    [counts[p,t] | t in Teams]
  )
);

% 3b. Team 1 plays in periods following pattern: 1, 2, 2, 3, 3, 4, 4, ...
% Week 1: period 1, Week 2: period 2, Week 3: period 2, Week 4: period 3, etc.
constraint forall(w in 1..nWeeks) (
    (x[w,(w+2) div 2] = 1) );

% 5c. Disambiguate the order of two successive columns
constraint forall(p in 2..nPeriods) (
    (y[2*p-2,p] < y[2*p-1,p]) );


% Solve directive
solve satisfy;

% Output format
output [
  "Tournament Schedule for ", show(n), " teams:\n",
  "=========================================\n"
] ++
[
  if p = 1 then "\nWeek " ++ show(w) ++ ":\n" else "" endif ++
  "  Period " ++ show(p) ++ ": Team " ++ show(x[w,p]) ++ 
  " vs Team " ++ show(y[w,p]) ++ " (Match #" ++ show(m[w,p]) ++ ")\n"
  | w in 1..nWeeks, p in 1..nPeriods
];