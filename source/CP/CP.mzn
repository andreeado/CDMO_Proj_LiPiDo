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

% === CP: Sports Tournament Scheduling Problem ===

include "alldifferent.mzn";

int: nWeeks = n - 1; % Number of weeks in the tournament
int: nPeriods = n div 2; % Number of periods per week

% Function to calculate match ID from team indices
function int: match_ID(int: t1, int: t2) = 
  ((t1 - 1) * n + t2 ) - (t1 * (t1 + 1)) div 2;

set of int: Weeks = 1..nWeeks; % Set of week indices
set of int: Periods = 1..nPeriods; % Set of period indices

array[Periods, Weeks] of var Matches: match_vars; % For each period and week, which match is scheduled
array[Periods, Weeks] of var Teams: x; % For each period and week, first team in the match
array[Periods, Weeks] of var Teams: y; % For each period and week, second team in the match

% = Constraints =

% Channeling Constraints Between implementations
constraint forall(p in Periods, w in Weeks) (
  x[p, w] = table_t1[match_vars[p, w]] /\
  y[p, w] = table_t2[match_vars[p, w]]
);

% All scheduled matches must be different (no repeats)
constraint alldifferent(match_vars); 

% For each week, all teams must play exactly once
constraint forall(w in Weeks) (
  alldifferent([x[p, w] | p in Periods] ++ [y[p, w] | p in Periods])
);

% For each period and team, count the times the team appears in that period across all weeks
constraint forall(p in Periods) (
  forall(t in Teams) (
    let {
      var int: count = sum([bool2int(x[p, w] = t) + bool2int(y[p, w] = t) | w in Weeks])
    } in count in 1..2 % Each team appears in each period 1 or 2 times
  )
);

% Each team has exactly one "defective" period (plays only once in that period)
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


solve :: int_search(match_vars, first_fail, indomain_random) satisfy;


% === Output ===

output ["[\n"] ++ [
  "[\n[" ++
  join(", ",
 [" [" ++ show(x[p, w]) ++ ", " ++ show(y[p, w]) ++ "]"
  | w in Weeks ]) ++ "]" ++
  if p != nPeriods then ",\n" else "\n" endif
| p in Periods
] ++ ["]\n"]; % Output the schedule as a list of home-away pairs for each period and week