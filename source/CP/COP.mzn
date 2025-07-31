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

solve :: restart_geometric(n, 2) :: bool_search(swap, input_order, indomain_random, complete)
       minimize sum(imbalance);

output [
  "swap=", show(swap), " obj=", show(sum(imbalance))
];