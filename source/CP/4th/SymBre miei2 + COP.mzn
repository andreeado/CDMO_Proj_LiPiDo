% Sports Tournament Scheduling Problem
% Each team plays against every other team exactly once
% Games are scheduled across weeks and periods
include "alldifferent.mzn";
include "global_cardinality.mzn";

% === Parameters ===
int: n;
int: nWeeks = n - 1;
int: nPeriods = n div 2;
int: nMatches = (n - 1) * n div 2;

set of int: Teams = 1..n;
set of int: Weeks = 1..nWeeks;
set of int: Periods = 1..nPeriods;
set of int: Matches = 1..nMatches;

% === Match Numbering ===
function int: match_number(int: t1, int: t2) = 
  (t1 - 1) * n - (t1 * (t1 - 1)) div 2 + (t2 - t1);

array[Matches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2];
array[Matches] of int: table_match = [match_number(t1, t2) | t1 in Teams, t2 in Teams where t1 < t2];

% === COP: Home-Away Balancing ===

% Decision variable: swap team roles in match?
array[Matches] of var 0..1: swap;

% Derived counts
array[Teams] of var 0..n-1: home_count;
array[Teams] of var 0..n-1: away_count;
array[Teams] of var 0..n: imbalance;

constraint forall(t in Teams) (
  home_count[t] = sum([m in Matches] (
    (if table_t1[m] = t then 1 - swap[m] else 0 endif) +
    (if table_t2[m] = t then swap[m] else 0 endif)
  )));

constraint forall(t in Teams) (
  away_count[t] = (n - 1 - home_count[t]
  ));

constraint forall(t in Teams) (
  imbalance[t] = abs(home_count[t] - away_count[t]) - 1
);

% === Main Scheduling Problem ===

array[Weeks, Periods] of var Matches: match_vars;
array[Weeks, Periods] of var Teams: x;
array[Weeks, Periods] of var Teams: y;

% Apply matches using swap
constraint forall(w in Weeks, p in Periods) (
  let {
    var int: m = match_vars[w, p],
    var int: t1 = table_t1[m],
    var int: t2 = table_t2[m]
  } in
    (if swap[m] = 0 then
        x[w, p] = t1 /\ y[w, p] = t2
     else
        x[w, p] = t2 /\ y[w, p] = t1
     endif)
);

constraint alldifferent(match_vars);

constraint forall(w in Weeks) (
  alldifferent([ x[w, p] | p in Periods ] ++ [ y[w, p] | p in Periods ])
);

array[1..nPeriods, Teams] of int: counts =
  array2d(1..nPeriods, Teams,
    [ if t = 2*p - 1 \/ t = 2*p then 1 else 2 endif | p in 1..nPeriods, t in Teams ]);

constraint forall(p in Periods, t in Teams) (
  count([ x[w, p] | w in Weeks ] ++ [ y[w, p] | w in Weeks ], t) = counts[p, t]
);

% === Team 1 Pattern and Ordering Constraints ===

array[Weeks] of var Periods: team1_period;

constraint forall(w in Weeks) (
  exists(p in Periods) (
    team1_period[w] = p /\
    (x[w, p] = 1 \/ y[w, p] = 1)
  )
);

constraint forall(k in 1..n-1) (
  let { var Periods: p = team1_period[k] } in
    (x[k, p] = 1 /\ y[k, p] = k + 1) \/ (x[k, p] = k + 1 /\ y[k, p] = 1)
);

constraint forall(k in 1..(nWeeks div 2)) (
  team1_period[2 * k] <= team1_period[2 * k + 1]
);

% === Disambiguate ordering
constraint forall(p in 2..nPeriods) (
  y[2 * p - 2, p] < y[2 * p - 1, p]
);

% === Solve: First optimize COP, then schedule ===

solve :: int_search(swap, input_order, indomain_min, complete) 
       minimize sum(t in Teams)(imbalance[t]);
