% === COP Only: home-away balancing ===

% Parameters
int: n;
int: nMatches = (n - 1) * n div 2;
set of int: Teams = 1..n;
set of int: Matches = 1..nMatches;

% Match table
array[Matches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2];

% Decision variable: whether to swap roles in each match
array[Matches] of var 0..1: swap;

% Count how many times each team is home/away
array[Teams] of var 0..n-1: home_count;
array[Teams] of var 0..n-1: away_count;
array[Teams] of var 0..n: imbalance;


constraint forall(t in Teams) (
  home_count[t] = sum(m in Matches) (
    ((table_t1[m] == t) * (1 - swap[m])) +
    ((table_t2[m] == t) * swap[m])
  )
);

constraint forall(t in Teams) (
  imbalance[t] = abs(2 * home_count[t] - (n - 1)) - 1
);

solve :: int_search(swap, input_order, indomain_min, complete) 
       minimize sum(t in Teams)(imbalance[t]);

output [
  "swap=", show(swap), " obj=", show(sum(t in Teams)(imbalance[t]))
];
