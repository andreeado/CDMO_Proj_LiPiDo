% === Parameters Shared Between COP and CP ===
par int: n; % Number of teams in the tournament
int: nMatches = (n - 1) * n div 2; % Total number of matches in tournament
set of int: Teams = 1..n; % Set of team indices
set of int: Matches = 1..nMatches; % Set of match indices

% === COP Only: home-away balancing ===

% Match table
array[Matches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2]; % For each match, first team (home by default)
array[Matches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2]; % For each match, second team (away by default)

% Decision variable: whether to swap team order in each match
array[Matches] of var bool: swap; % For each match, 0 means no swap (t1 is home), 1 means swap (t2 is home)

% Count how many times each team is home/away
array[Teams] of var 0..n-2: imbalance; % For each team, imbalance in home/away games

  
% For each team, calculate imbalance: abs(2 * home_count - (n - 1)) - 1
constraint forall(t in Teams) (
  let {
    % Count how many times team t is home, based on swap direction
    var int: home_count = sum(m in Matches) (
      (table_t1[m] == t) * (1 - swap[m]) +
      (table_t2[m] == t) * swap[m]
    )
  } in
    % Compute the imbalance as deviation from ideal home/away split
    imbalance[t] = abs(2 * home_count - (n - 1)) - 1
);

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
constraint forall(w in Weeks, p in Periods) (
  x[p, w] = table_t1[match_vars[p, w]] /\
  y[p, w] = table_t2[match_vars[p, w]]
);

% All scheduled matches must be different (no repeats)
constraint alldifferent(match_vars); 

% Circle Method: For each match, compute its designated week
array[Matches] of int: week_of_match = [
  if table_t2[m] = n then
    table_t1[m] % team n plays team r in week r
  else
    min([w | w in 1..n-1 where ((table_t1[m] + table_t2[m]) mod (n-1)) = (2 * w) mod (n-1)])
  endif
| m in Matches
];

% Constraint: Each match must be scheduled in its designated week
constraint forall(p in Periods, w in Weeks) (
  week_of_match[match_vars[p, w]] = w
);

% For each period and team, count the times the team appears in that period across all weeks
constraint forall(p in Periods) (
  forall(t in Teams) (
    let {
      var int: count = sum([bool2int(x[p, w] = t) + bool2int(y[p, w] = t) | w in Weeks])
    } in count in 1..2 % Each team appears in each period 1 or 2 times
  )
);

% = Implied Constraints =


% Each team has exactly one "defective" period (plays only once in that period)
constraint forall(t in Teams) (
  sum(p in Periods) (
    bool2int(sum(w in Weeks) (bool2int(x[p,w] = t) + bool2int(y[p,w] = t)) = 1)
  ) = 1
);


% = Symmetry breaking =

/*
% Well ordering of rows by fixing first week schedule (according to the circle method)
constraint
  forall(p in Periods) (
    match_vars[p, 1] = match_ID(p, n+1-p)
  );

% Fixing the first boolean value WLOG
constraint swap[1]=0;

*/

% === Solve Phase (COP objective only) ===

% solve minimize sum(imbalance);s

solve :: seq_search([
    int_search(match_vars, first_fail, indomain_random),
    bool_search(swap, input_order, indomain_random, complete)
]) minimize sum(imbalance);

% === Output ===

output ["[\n"] ++ [
  "  [" ++
  join(", ", [
    let {
      var int: m = match_vars[p, w], % Match ID for period p, week w
      var int: home = if swap[m] = 0 then x[p, w] else y[p, w] endif, % Home team after swap
      var int: away = if swap[m] = 0 then y[p, w] else x[p, w] endif % Away team after swap
    } in " [" ++ show(home) ++ ", " ++ show(away) ++ "]"
  | w in Weeks ]) ++ "]" ++
  if p != nPeriods then ",\n" else "\n" endif
| p in Periods
] ++ ["]\n"] ++ [
 "Objective function: " ++ show(sum(imbalance)) ++ "\n",
]; % Output the schedule as a list of home-away pairs for each period and week