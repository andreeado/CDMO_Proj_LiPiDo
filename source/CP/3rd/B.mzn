% Sports Tournament Scheduling Problem
% Each team plays against every other team exactly once
% Games are scheduled across weeks and periods

include "alldifferent.mzn";

% Input parameter: number of teams (default 8)
int: n = 8;

% Derived parameters
int: nWeeks = n - 1;                    % Number of weeks in the tournament
int: nPeriods = n div 2;                % Number of periods (games) per week
int: nMatches = (n - 1) * n div 2;      % Total number of matches

% Predicate to calculate match number for teams t1 and t2 (where t1 < t2)
% This creates a unique identifier for each possible match (1-indexed)
predicate match_number(var int: t1, var int: t2, var int: match) = 
  match = nMatches - ((n - t1 + 1) * (n - t1)) div 2 + (t2 - t1);

% Create the table of valid (team1, team2, match_number) combinations
% Teams and matches are now 1-indexed
set of int: Teams = 1..n;
set of int: Matches = 1..nMatches;

% Decision variables (1-indexed)
% m[w,p] is the match number scheduled at week w, period p
array[1..nWeeks, 1..nPeriods] of var Matches: m;

% x[w,p] is the first team playing at week w, period p
array[1..nWeeks, 1..nPeriods] of var Teams: x;

% y[w,p] is the second team playing at week w, period p
array[1..nWeeks, 1..nPeriods] of var Teams: y;

% Constraints

% 1. All matches must be different (each pair of teams plays exactly once)
constraint alldifferent([m[w,p] | w in 1..nWeeks, p in 1..nPeriods]);

% 2. Link the team variables (x,y) with match numbers (m) through table constraint
% For each scheduled match, ensure the teams and match number are consistent
constraint forall(w in 1..nWeeks, p in 1..nPeriods) (
  % Ensure x[w,p] < y[w,p] to maintain ordering
  x[w,p] < y[w,p] /\
  % Match number must correspond to the teams playing
  match_number(x[w,p], y[w,p], m[w,p])
);

% 3. Each week, all teams must be different (every team plays exactly once per week)
constraint forall(w in 1..nWeeks) (
  alldifferent([x[w,p] | p in 1..nPeriods] ++ [y[w,p] | p in 1..nPeriods])
);

% 4. Each team plays at most twice in each period across all weeks
% This ensures a fair distribution of game times
constraint forall(p in 1..nPeriods) (
  forall(t in Teams) (
    let {
      % Count how many times team t appears in period p across all weeks
      var 1..2: count = sum(w in 1..nWeeks) (
        bool2int(x[w,p] = t) + bool2int(y[w,p] = t)
      )
    } in count >= 1 /\ count <= 2
  )
);

% 5. Symmetry breaking constraints to reduce search space

% 5a. Team 1 plays against team (w+1) in week w
% This fixes when team 1 plays against each other team
constraint forall(w in 1..nWeeks) (
  exists(p in 1..nPeriods) (
    match_number(1, w + 1, m[w,p])
  )
);

% 5b. Fix the first week's schedule: 1 vs 2, 3 vs 4, 5 vs 6, etc.
% This provides a canonical starting point
constraint forall(p in 1..nPeriods) (
  let {
    int: t1 = 2*p - 1;
    int: t2 = 2*p;
    int: match = nMatches - ((n - t1 + 1) * (n - t1)) div 2 + (t2 - t1);
  } in m[1,p] = match
);

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