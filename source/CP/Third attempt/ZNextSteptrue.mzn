include "alldifferent.mzn";
include "global_cardinality.mzn";

% Sports Tournament Scheduling Problem

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

% Create arrays for the table lookup
array[Matches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_match = [match_number(t1, t2) | t1 in Teams, t2 in Teams where t1 < t2];

% Decision variables
array[Weeks, Periods] of var Matches: match_vars;
array[Weeks, Periods] of var Teams: x;
array[Weeks, Periods] of var Teams: y;

% Constraints

% Channeling variables through table constraints
constraint forall(w in Weeks, p in Periods) (
  exists(i in Matches) (
    x[w, p] = table_t1[i] /\
    y[w, p] = table_t2[i] /\
    match_vars[w, p] = table_match[i]
  )
);

% All matches are different
constraint alldifferent(match_vars);

% Each week, all teams are different
constraint forall(w in Weeks) (
  alldifferent([x[w, p] | p in Periods] ++ [y[w, p] | p in Periods])
);

% Each team plays at most two times in each period
constraint forall(p in Periods) (
  forall(t in Teams) (
    let {
      var int: count = sum([bool2int(x[w, p] = t) + bool2int(y[w, p] = t) | w in Weeks])
    } in count = 1 + ( p == ((t+1) div 2))
  )
);

% Symmetry breaking: Match (1 vs t+1) occurs in week t
constraint forall(w in Weeks) (
  let { int: t = w + 1 } in
  t <= n ->
    count([match_vars[w, p] | p in Periods], match_number(1, t)) = 1
);

% First week is fixed: 1 vs 2, 3 vs 4, 5 vs 6, ...
constraint forall(p in Periods) (
  match_vars[1, p] = match_number(2 * p - 1, 2 * p)
);

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