% === Parameters Shared Between COP and CP ===
int: n; % Number of teams in the tournament
int: nMatches = (n - 1) * n div 2; % Total number of matches in tournament
set of int: Teams = 1..n; % Set of team indices
set of int: Matches = 1..nMatches; % Set of match indices

% === COP Only: home-away balancing ===

% Match table
array[Matches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2]; % For each match, first team (home by default)
array[Matches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2]; % For each match, second team (away by default)

% Decision variable: whether to swap team order in each match
array[Matches] of var 0..1: swap; % For each match, 0 means no swap (t1 is home), 1 means swap (t2 is home)

% Count how many times each team is home/away
array[Teams] of var 0..n-1: home_count; % For each team, number of times they are home
array[Teams] of var 0..n-2: imbalance; % For each team, imbalance in home/away games

constraint forall(t in Teams) (
  % For each team, count the number of times they are home
  home_count[t] = sum(m in Matches) (
    ((table_t1[m] == t) * (1 - swap[m])) + % t1 is home if swap[m] == 0
    ((table_t2[m] == t) * swap[m])         % t2 is home if swap[m] == 1
  )
);

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

% Function to calculate match number from team indices
% Only works for t1 < t2, second term "skips over" all matches s.t. t1 \geq t2
function int: match_number(int: t1, int: t2) = 
  ((t1 - 1) * n + t2 ) - (t1 * (t1 + 1)) div 2;

set of int: Weeks = 1..nWeeks; % Set of week indices
set of int: Periods = 1..nPeriods; % Set of period indices

array[Weeks, Periods] of var Matches: match_vars; % For each week and period, which match is scheduled
array[Weeks, Periods] of var Teams: x; % For each week and period, first team in the match
array[Weeks, Periods] of var Teams: y; % For each week and period, second team in the match

% = Constraints =

% Channeling Constraints Between implementations
constraint forall(w in Weeks, p in Periods) (
  x[w, p] = table_t1[match_vars[w, p]] /\
  y[w, p] = table_t2[match_vars[w, p]]
);

% All scheduled matches must be different (no repeats)
constraint alldifferent(match_vars); 

% For each week, all teams must play exactly once
constraint forall(w in Weeks) (
  alldifferent([x[w, p] | p in Periods] ++ [y[w, p] | p in Periods])
);

% For each period and team, count the times the team appears in that period across all weeks
constraint forall(p in Periods) (
  forall(t in Teams) (
    let {
      var int: count = sum([bool2int(x[w, p] = t) + bool2int(y[w, p] = t) | w in Weeks])
    } in count in 1..2 % Each team appears in each period 1 or 2 times
  )
);

% = Symmetry breaking =

% Well ordering of columns by fixing team 1 period choice
constraint forall(w in Weeks) (
  x[w,(w+2) div 2] = 1
);

% Well ordering of rows by fixing first week schedule
constraint forall(p in Periods) (
  match_vars[1, p] = match_number(2 * p - 1, 2 * p)
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
      var int: m = match_vars[w, p], % Match number for week w, period p
      var int: h = if swap[m] = 0 then x[w, p] else y[w, p] endif, % Home team after swap
      var int: a = if swap[m] = 0 then y[w, p] else x[w, p] endif % Away team after swap
    } in " [" ++ show(h) ++ ", " ++ show(a) ++ "]"
  | w in Weeks ]) ++ "]" ++
  if p != nPeriods then ",\n" else "\n" endif
| p in Periods
] ++ ["]\n"] ++ [
 "Objective function: " ++ show(sum(t in Teams)(imbalance[t])) ++ "\n",
]; % Output the schedule as a list of home-away pairs for each period and week