% === Parameters Shared Between COP and CP ===
int: n; % Number of teams in the tournament
int: nMatches = (n - 1) * n div 2; % Total number of matches in tournament
set of int: Teams = 1..n; % Set of team indices
set of int: Matches = 1..nMatches; % Set of match indices

% === COP Only: home-away balancing ===

% Function to calculate match ID from team indices
% Only works for i < j, second term "skips over" all other matches
function int: match_ID(int: i, int: j) = 
  ((i - 1) * n + j ) - (i * (i + 1)) div 2;

% Match table
array[Teams, Teams] of int: match_lookup = 
  array2d(Teams, Teams, 
    [ if i < j then match_ID(i, j) else 0 endif 
    | i in Teams, j in Teams ]
  );
  
array[Matches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2];

% Decision variable: whether to swap team order in each match
array[Matches] of var bool: swap; % For each match, 0 means no swap (i is home), 1 means swap (j is home)

% Count how many times each team is home/away
array[Teams] of var 0..n-1: home_count; % For each team, number of times they are home

constraint forall(t in Teams) (
  home_count[t] = sum(m in Matches) (
    ((table_t1[m] == t) * (1 - swap[m])) + 
    ((table_t2[m] == t) * swap[m])
  )
);

array[Teams] of var 0..n-2: imbalance; % For each team, imbalance in home/away games


constraint forall(t in Teams) (
  % For each team, calculate imbalance: abs(2 * home_count - (n - 1)) - 1
  % This measures deviation from perfect home/away balance
  imbalance[t] = abs(2 * home_count[t] - (n - 1)) - 1
);

% === CP: Sports Tournament Scheduling Problem ===

include "alldifferent.mzn";
include "global_cardinality.mzn";

int: nWeeks = n - 1; % Number of weeks in the tournament
int: nPeriods = n div 2; % Number of periods per week

set of int: Weeks = 1..nWeeks; % Set of week indices
set of int: Periods = 1..nPeriods; % Set of period indices

array[Periods, Weeks] of var Matches: match_vars; % For each period and week, which match is scheduled
array[Periods, Weeks] of var Teams: x; % For each period and week, first team in the match
array[Periods, Weeks] of var Teams: y; % For each period and week, second team in the match

% = Constraints =

% Channeling Constraints
constraint forall(p in Periods, w in Weeks) (
  match_vars[p, w] = match_lookup[x[p, w], y[p, w]] 
  /\ x[p, w] < y[p, w]
);

% Match Uniqueness
constraint alldifferent(match_vars); 

% Weekly Team Participation
constraint forall(w in Weeks) (
  alldifferent([x[p, w] | p in Periods] ++ [y[p, w] | p in Periods])
);

% Period Participation
constraint forall(p in Periods) (
  forall(t in Teams) (
    let {
      var int: count = sum([bool2int(x[p, w] = t) + bool2int(y[p, w] = t) | w in Weeks])
    } in count in 1..2 % Each team appears in each period 1 or 2 times
  )
);

% Implied Defectiveness Constraint
constraint forall(t in Teams) (
  sum(p in Periods) (
    bool2int(sum(w in Weeks) (bool2int(x[p,w] = t) + bool2int(y[p,w] = t)) = 1)
  ) = 1
);

% = Symmetry breaking =

% Well ordering of columns by fixing team 1 period choice
constraint forall(w in Weeks) (
  x[(w+2) div 2, w] = 1
);

% Well ordering of rows by fixing first week schedule
constraint forall(p in Periods) (
  match_vars[p, 1] = match_ID(2 * p - 1, 2 * p)
);

% === Solve Phase (COP objective only) ===

% solve minimize sum(imbalance);


solve :: seq_search([
  int_search(match_vars, first_fail, indomain_random),
  int_search(swap, input_order, indomain_random, complete),
]) minimize sum(imbalance);


% === Output ===

output [
  "  [" ++
  join(", ", [
    let {
      var int: m = match_vars[p, w], % Match ID for period p, week w
      var int: h = if swap[m] = 0 then x[p, w] else y[p, w] endif, % Home team after swap
      var int: a = if swap[m] = 0 then y[p, w] else x[p, w] endif % Away team after swap
    } in " [" ++ show(h) ++ ", " ++ show(a) ++ "]"
  | w in Weeks ]) ++ "]" ++
  if p != nPeriods then ",\n" else "\n" endif
| p in Periods
] ++ ["]\n"] ++ [
 "Objective function: " ++ show(sum(imbalance)) ++ "\n",
]; % Output the schedule as a list of home-away pairs for each period and week