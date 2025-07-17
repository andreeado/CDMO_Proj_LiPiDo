include "alldifferent.mzn";
include "global_cardinality.mzn";

% Sports Tournament Scheduling Problem

% Parameters
int: n;  
int: nWeeks = n - 1;
int: nPeriods = n div 2;
int: nMatches = (n - 1) * n div 2;

% Function to calculate match number (1-based)
function int: match_number(int: t1, int: t2) = 
  nMatches - ((n - t1) * (n - t1 - 1)) div 2 + (t2 - t1 - 1);

% Sets (1-based)
set of int: Teams = 1..n;
set of int: Weeks = 1..nWeeks;
set of int: Periods = 1..nPeriods;
set of int: Matches = 1..nMatches;

% Create arrays for the table lookup
array[Matches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_match = [match_number(t1, t2) | t1 in Teams, t2 in Teams where t1 < t2];

% Decision variables
array[Weeks, Periods] of var Matches: match_vars;
array[Weeks, Periods] of var Teams: x;
array[Weeks, Periods] of var Teams: y;

% Constraints

% All matches are different
constraint alldifferent([match_vars[w, p] | w in Weeks, p in Periods]);

% Channeling variables through table constraints
constraint forall(w in Weeks, p in Periods) (
  exists(i in Matches) (
    x[w, p] = table_t1[i] /\
    y[w, p] = table_t2[i] /\
    match_vars[w, p] = table_match[i]
  )
);

% Each week, all teams are different
constraint forall(w in Weeks) (
  alldifferent([x[w, p] | p in Periods] ++ [y[w, p] | p in Periods])
);

% Each team plays at most two times in each period
constraint forall(p in Periods) (
  forall(t in Teams) (
    let {
      var int: count = sum([bool2int(x[w, p] = t) + bool2int(y[w, p] = t) | w in Weeks])
    } in count >= 1 /\ count <= 2
  )
);

% 5. Symmetry breaking constraints to reduce search space

% 5a. In period k, teams 2k-1 and 2k play exactly once, all others play twice
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

% 5b. Team 1 plays in periods following pattern: 1, 2, 2, 3, 3, 4, 4, ...
% Week 1: period 1, Week 2: period 2, Week 3: period 2, Week 4: period 3, etc.
constraint forall(w in 1..nWeeks) (
    (x[w,(w+2) div 2] = 1) );

% 5c. Disambiguate the order of two successive columns
constraint forall(p in 2..nPeriods) (
    (y[2*p-2,p] < y[2*p-1,p]) );

% Solve
solve satisfy;

% Output
output [
  "Schedule of Matches (week x period):\n"
] ++ [
  "Week " ++ show(w) ++ ":\n" ++
  concat([
    "  Period " ++ show(p) ++ ": Team " ++ show(x[w, p]) ++ 
    " vs Team " ++ show(y[w, p]) ++ " (Match #" ++ show(match_vars[w, p]) ++ ")\n"
  | p in Periods])
| w in Weeks];