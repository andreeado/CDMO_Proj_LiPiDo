% Sports Tournament Scheduling Problem

include "alldifferent.mzn";

% Sports Tournament Scheduling Problem

% Parameters
int: nTeams = 14;  % Replace with your desired number of teams
int: nWeeks = nTeams - 1;
int: nPeriods = nTeams div 2;
int: nMatches = (nTeams - 1) * nTeams div 2;

% Function to calculate match number
function int: match_number(int: t1, int: t2) = 
  nMatches - ((nTeams - t1) * (nTeams - t1 - 1)) div 2 + (t2 - t1 - 1);

% Generate the table of valid (team1, team2, match_number) triples
set of int: Teams = 0..nTeams-1;
set of int: Matches = 0..nMatches-1;

% Create arrays for the table lookup
array[1..nMatches] of int: table_t1 = [t1 | t1 in Teams, t2 in Teams where t1 < t2];
array[1..nMatches] of int: table_t2 = [t2 | t1 in Teams, t2 in Teams where t1 < t2];
array[1..nMatches] of int: table_match = [match_number(t1, t2) | t1 in Teams, t2 in Teams where t1 < t2];

% Decision variables
array[0..nWeeks-1, 0..nPeriods-1] of var 0..nMatches-1: match_vars;
array[0..nWeeks-1, 0..nPeriods-1] of var Teams: x;
array[0..nWeeks-1, 0..nPeriods-1] of var Teams: y;

% Constraints

% All matches are different (no team can play twice against another team)
constraint alldifferent([match_vars[w,p] | w in 0..nWeeks-1, p in 0..nPeriods-1]);

% Channeling variables through table constraints
constraint forall(w in 0..nWeeks-1, p in 0..nPeriods-1) (
  exists(i in 1..nMatches) (
    x[w,p] = table_t1[i] /\ 
    y[w,p] = table_t2[i] /\ 
    match_vars[w,p] = table_match[i]
  )
);

% Each week, all teams are different (each team plays each week)
constraint forall(w in 0..nWeeks-1) (
  alldifferent([x[w,p] | p in 0..nPeriods-1] ++ [y[w,p] | p in 0..nPeriods-1])
);

% Each team plays at most two times in each period
constraint forall(p in 0..nPeriods-1) (
  forall(t in Teams) (
    let {
      var int: count = sum(w in 0..nWeeks-1) (
        bool2int(x[w,p] = t) + bool2int(y[w,p] = t)
      )
    } in count >= 1 /\ count <= 2
  )
);

% Symmetry breaking constraints
% The match '0 versus t' (with t > 0) appears at week t-1
constraint forall(w in 0..nWeeks-1) (
  count([match_vars[w,p] | p in 0..nPeriods-1], match_number(0, w+1)) = 1
);

% The first week is set: 0 vs 1, 2 vs 3, 4 vs 5, etc.
constraint forall(p in 0..nPeriods-1) (
  match_vars[0,p] = match_number(2*p, 2*p+1)
);

% Solve
solve satisfy;

% Output
output [
  "Schedule of Matches (week x period):\n"
] ++ [
  "Week " ++ show(w+1) ++ ":\n" ++
  concat([
    "  Period " ++ show(p+1) ++ ": Team " ++ show(x[w,p]) ++ 
    " vs Team " ++ show(y[w,p]) ++ " (Match #" ++ show(match_vars[w,p]) ++ ")\n"
  | p in 0..nPeriods-1])
| w in 0..nWeeks-1];

%-------------- Dummy Week Variant (uncomment to enable) --------------
% To enable the dummy week variant, uncomment the following section:

/*
% Dummy week variables
array[0..nPeriods-1] of var Teams: xd;
array[0..nPeriods-1] of var Teams: yd;

% All teams are different in the dummy week
constraint alldifferent(xd ++ yd);

% Each team plays exactly two times in each period (including dummy week)
constraint forall(p in 0..nPeriods-1) (
  forall(t in Teams) (
    let {
      var int: count = sum(w in 0..nWeeks-1) (
        bool2int(x[w,p] = t) + bool2int(y[w,p] = t)
      ) + bool2int(xd[p] = t) + bool2int(yd[p] = t)
    } in count = 2
  )
);

% Symmetry breaking for dummy matches
constraint forall(p in 0..nPeriods-1) (
  xd[p] < yd[p]
);

% Add dummy week output
output [
  "\nDummy Week:\n"
] ++ [
  "  Period " ++ show(p+1) ++ ": Team " ++ show(xd[p]) ++ 
  " vs Team " ++ show(yd[p]) ++ "\n"
| p in 0..nPeriods-1];
*/