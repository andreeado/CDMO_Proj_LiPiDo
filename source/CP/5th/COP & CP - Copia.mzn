% === Parameters Shared Between COP and CP ===
int: n;
int: nMatches = (n - 1) * n div 2;
set of int: Teams = 1..n;
set of int: Matches = 1..nMatches;

% === COP Only: home-away balancing ===

% Match table
array[Matches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2];

% Decision variable: whether to swap roles in each match
array[Matches] of var 0..1: swap;

% Count how many times each team is home/away
array[Teams] of var 0..n-1: home_count;
array[Teams] of var 0..n-2: imbalance;

constraint forall(t in Teams) (
  home_count[t] = sum(m in Matches) (
    ((table_t1[m] == t) * (1 - swap[m])) +
    ((table_t2[m] == t) * swap[m])
  )
);

constraint forall(t in Teams) (
  imbalance[t] = abs(2 * home_count[t] - (n - 1)) - 1
);

% === CP: Sports Tournament Scheduling Problem ===

include "alldifferent.mzn";
include "global_cardinality.mzn";

int: nWeeks = n - 1;
int: nPeriods = n div 2;

% Function to calculate match number
function int: match_number(int: t1, int: t2) = 
  (t1 - 1) * n - (t1 * (t1 - 1)) div 2 + (t2 - t1);

set of int: Weeks = 1..nWeeks;
set of int: Periods = 1..nPeriods;

array[Matches] of int: table_match = [match_number(t1, t2) | t1 in Teams, t2 in Teams where t1 < t2];

array[Weeks, Periods] of var Matches: match_vars;
array[Weeks, Periods] of var Teams: x;
array[Weeks, Periods] of var Teams: y;

% Constraints
constraint forall(w in Weeks, p in Periods) (
  exists(i in Matches) (
    x[w, p] = table_t1[i] /\
    y[w, p] = table_t2[i] /\
    match_vars[w, p] = table_match[i]
  )
);

constraint alldifferent(match_vars);

constraint forall(w in Weeks) (
  alldifferent([x[w, p] | p in Periods] ++ [y[w, p] | p in Periods])
);

constraint forall(p in Periods) (
  forall(t in Teams) (
    let {
      var int: count = sum([bool2int(x[w, p] = t) + bool2int(y[w, p] = t) | w in Weeks])
    } in count in 1..2
  )
);

constraint forall(w in Weeks) (
  let { int: t = w + 1 } in
  t <= n ->
    count([match_vars[w, p] | p in Periods], match_number(1, t)) = 1
);

constraint forall(p in Periods) (
  match_vars[1, p] = match_number(2 * p - 1, 2 * p)
);

% === Solve Phase (COP objective only) ===
solve :: int_search(swap, input_order, indomain_min, complete) 
       minimize sum(t in Teams)(imbalance[t]);

% === Output ===
output [
  "sol = [\n"
] ++ [
  "  [" ++
  join(", ", [
    let {
      var int: m = match_vars[w, p],
      var int: h = if swap[m] = 0 then x[w, p] else y[w, p] endif,
      var int: a = if swap[m] = 0 then y[w, p] else x[w, p] endif
    } in " [" ++ show(h) ++ ", " ++ show(a) ++ "]"
  | w in Weeks ]) ++ "]" ++
  if p != nPeriods then ",\n" else "\n" endif
| p in Periods
] ++ ["]\n"];