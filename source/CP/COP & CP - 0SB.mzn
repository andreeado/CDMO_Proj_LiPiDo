int: n;
int: nMatches = (n - 1) * n div 2;
set of int: Teams = 1..n;
set of int: Matches = 1..nMatches;

array[Matches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2];

array[Teams] of var 0..n-2: imbalance;

array[Teams] of var 0..n-1: home_count;

constraint forall(t in Teams)(
  home_count[t] = sum(p in 1..n div 2, w in 1..n-1)(bool2int(x[p,w] = t))
);

constraint forall(t in Teams)(
  imbalance[t] = abs(2 * home_count[t] - (n - 1)) - 1
);

include "alldifferent.mzn";

int: nWeeks = n - 1;
int: nPeriods = n div 2;

function int: match_ID(int: t1, int: t2) = 
  let {
    int: lo = min(t1, t2),
    int: hi = max(t1, t2)
  } in ((lo - 1) * n + hi ) - (lo * (lo + 1)) div 2;

set of int: Weeks = 1..nWeeks;
set of int: Periods = 1..nPeriods;

array[Periods, Weeks] of var Matches: match_vars;
array[Periods, Weeks] of var Teams: x;
array[Periods, Weeks] of var Teams: y;

constraint forall(p in Periods, w in Weeks)(
  let {
    var int: lo = min(x[p,w], y[p,w]),
    var int: hi = max(x[p,w], y[p,w])
  } in
    match_vars[p,w] = ((lo - 1) * n + hi) - (lo * (lo + 1)) div 2
);


constraint alldifferent(match_vars);

constraint forall(w in Weeks)(
  alldifferent([x[p,w] | p in Periods] ++ [y[p,w] | p in Periods])
);

constraint forall(p in Periods)(
  forall(t in Teams)(
    let {
      var int: count = sum(w in Weeks)(bool2int(x[p,w] = t) + bool2int(y[p,w] = t))
    } in count in 1..2
  )
);

constraint forall(t in Teams)(
  sum(p in Periods)(
    bool2int(sum(w in Weeks)(bool2int(x[p,w] = t) + bool2int(y[p,w] = t)) = 1)
  ) = 1
);

% Well ordering of columns by fixing team 1 period choice
constraint forall(w in Weeks) (
  x[(w+2) div 2, w] = 1 \/ y[(w+2) div 2, w] = 1
);

% Well ordering of rows by fixing first week schedule
constraint forall(p in Periods) (
  match_vars[p, 1] = match_ID(2 * p - 1, 2 * p)
);

solve :: seq_search([
  int_search(match_vars, first_fail, indomain_random)
]) minimize sum(imbalance);

output [
  "  [" ++
  join(", ", [
    " [" ++ show(x[p, w]) ++ ", " ++ show(y[p, w]) ++ "]"
  | w in Weeks ]) ++ "]" ++
  if p != nPeriods then ",\n" else "\n" endif
| p in Periods
] ++ ["]\n"] ++ [
 "Objective function: " ++ show(sum(imbalance)) ++ "\n",
];
