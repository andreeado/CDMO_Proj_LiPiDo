% === COP Only: home-away balancing ===

% Parameters
par int: n ;
int: nMatches = (n - 1) * n div 2;
set of int: Teams = 1..n;
set of int: Matches = 1..nMatches;

% Match table
array[Matches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2];

% Decision variable: whether to swap roles in each match
array[Matches] of var bool: swap;

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

constraint swap[1]=0;

solve :: restart_geometric(2, n) 
     :: bool_search(swap, input_order, indomain_random, complete)
       minimize max(imbalance);

output [
    show(swap) ++
    "\nObjective function: " ++ show(max(imbalance))
];