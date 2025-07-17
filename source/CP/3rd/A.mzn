% Sports Tournament Scheduling Problem
% Each team plays against every other team exactly once
% Games are scheduled across weeks and periods

include "alldifferent.mzn";

% Input parameter: number of teams (default 8)
int: nTeams = 8;

% Derived parameters
int: nWeeks = nTeams - 1;                    % Number of weeks in the tournament
int: nPeriods = nTeams div 2;                % Number of periods (games) per week
int: nMatches = (nTeams - 1) * nTeams div 2; % Total number of matches

% Predicate to calculate match number for teams t1 and t2 (where t1 < t2)
% This creates a unique identifier for each possible match
predicate match_number(var int: t1, var int: t2, var int: match) = 
  match = nMatches - ((nTeams - t1) * (nTeams - t1 - 1)) div 2 + (t2 - t1 - 1);

% Create the table of valid (team1, team2, match_number) combinations
% This represents all possible matches in the tournament
set of int: Teams = 0..nTeams-1;
set of int: Matches = 0..nMatches-1;

% Decision variables
% m[w,p] is the match number scheduled at week w, period p
array[0..nWeeks-1, 0..nPeriods-1] of var Matches: m;

% x[w,p] is the first team playing at week w, period p
array[0..nWeeks-1, 0..nPeriods-1] of var Teams: x;

% y[w,p] is the second team playing at week w, period p
array[0..nWeeks-1, 0..nPeriods-1] of var Teams: y;

% Constraints

% 1. All matches must be different (each pair of teams plays exactly once)
constraint alldifferent([m[w,p] | w in 0..nWeeks-1, p in 0..nPeriods-1]);

% 2. Link the team variables (x,y) with match numbers (m) through table constraint
% For each scheduled match, ensure the teams and match number are consistent
constraint forall(w in 0..nWeeks-1, p in 0..nPeriods-1) (
  % Ensure x[w,p] < y[w,p] to maintain ordering
  x[w,p] < y[w,p] /\
  % Match number must correspond to the teams playing
  match_number(x[w,p], y[w,p], m[w,p])
);

% 3. Each week, all teams must be different (every team plays exactly once per week)
constraint forall(w in 0..nWeeks-1) (
  alldifferent([x[w,p] | p in 0..nPeriods-1] ++ [y[w,p] | p in 0..nPeriods-1])
);

% 4. Each team plays at most twice in each period across all weeks
% This ensures a fair distribution of game times
constraint forall(p in 0..nPeriods-1) (
  forall(t in Teams) (
    let {
      % Count how many times team t appears in period p across all weeks
      var 1..2: count = sum(w in 0..nWeeks-1) (
        bool2int(x[w,p] = t) + bool2int(y[w,p] = t)
      )
    } in count >= 1 /\ count <= 2
  )
);

% 5. Symmetry breaking constraints to reduce search space

% 5a. Team 0 plays against team (w+1) in week w
% This fixes when team 0 plays against each other team
constraint forall(w in 0..nWeeks-1) (
  exists(p in 0..nPeriods-1) (
    match_number(0, w + 1, m[w,p])
  )
);

% 5b. Fix the first week's schedule: 0 vs 1, 2 vs 3, 4 vs 5, etc.
% This provides a canonical starting point
constraint forall(p in 0..nPeriods-1) (
  let {
    int: t1 = 2*p;
    int: t2 = 2*p + 1;
    int: match = nMatches - ((nTeams - t1) * (nTeams - t1 - 1)) div 2 + (t2 - t1 - 1);
  } in m[0,p] = match
);

% Solve directive
solve satisfy;

% Output format
output [
  "Tournament Schedule for ", show(nTeams), " teams:\n",
  "=========================================\n"
] ++
[
  if p = 0 then "\nWeek " ++ show(w+1) ++ ":\n" else "" endif ++
  "  Period " ++ show(p+1) ++ ": Team " ++ show(x[w,p]) ++ 
  " vs Team " ++ show(y[w,p]) ++ " (Match #" ++ show(m[w,p]) ++ ")\n"
  | w in 0..nWeeks-1, p in 0..nPeriods-1
];