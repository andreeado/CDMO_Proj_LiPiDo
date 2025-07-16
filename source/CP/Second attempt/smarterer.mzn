% CSPLib Problem 026 — Round Robin Tournament
% http://www.csplib.org/Problems/prob026/
% Home/Away Tournament Scheduler with Dual Encoding
% n teams, n-1 weeks, n/2 periods per week, 2 slots per period
% Slot 1: home team, Slot 2: away team (plays at slot 1 team's venue)

include "alldifferent.mzn";
include "global_cardinality.mzn";
include "table.mzn";

int: n_teams;
constraint n_teams mod 2 = 0;
constraint n_teams >= 4;
int: n_weeks = n_teams - 1;
int: n_periods = n_teams div 2;
int: n_matches = (n_teams - 1) * n_teams div 2;

set of int: Team = 1..n_teams;
set of int: Week = 1..n_weeks;
set of int: Period = 1..n_periods;
set of int: Slot = 1..2;  % 1 = home, 2 = away
set of int: Match = 0..n_matches-1;

% Precompute match numbers for efficiency
array[Team, Team] of int: match_lookup = 
    array2d(Team, Team, [
        if t1 < t2 then n_matches - ((n_teams - (t1-1)) * (n_teams - (t1-1) - 1)) div 2 + (t2 - t1 - 1)
        elseif t1 > t2 then n_matches - ((n_teams - (t2-1)) * (n_teams - (t2-1) - 1)) div 2 + (t1 - t2 - 1)
        else -1 endif
        | t1 in Team, t2 in Team
    ]);

% Pre-compute match data
array[1..n_matches] of int: match_t1 = [t1 | t1 in Team, t2 in Team where t1 < t2];
array[1..n_matches] of int: match_t2 = [t2 | t1 in Team, t2 in Team where t1 < t2];
array[1..n_matches] of int: match_nums = [match_lookup[t1,t2] | t1 in Team, t2 in Team where t1 < t2];

% Create table for channeling constraint (team1, team2, match)
% Include both orientations to handle home/away
array[1..2*n_matches, 1..3] of int: match_table = 
    array2d(1..2*n_matches, 1..3, 
        [if row <= n_matches then
            if col = 1 then match_t1[row]
            elseif col = 2 then match_t2[row]
            else match_nums[row] endif
         else
            let { int: idx = row - n_matches } in
            if col = 1 then match_t2[idx]
            elseif col = 2 then match_t1[idx]
            else match_nums[idx] endif
         endif | row in 1..2*n_matches, col in 1..3]);

% Decision variables
array[Week, Period, Slot] of var Team: schedule;
array[Week, Period] of var Match: match_vars;

% CHANNELING: Use table constraint for efficiency
constraint forall(w in Week, p in Period) (
    table([schedule[w,p,1], schedule[w,p,2], match_vars[w,p]], match_table)
);

% CONSTRAINT 1: Every team plays exactly once per week
constraint forall(w in Week) (
    alldifferent([schedule[w,p,s] | p in Period, s in Slot])
);

% CONSTRAINT 2: All matches are different
constraint alldifferent([match_vars[w,p] | w in Week, p in Period]);

% CONSTRAINT 3: Cardinality constraint for period usage (replaces bool2int sums)
constraint forall(p in Period) (
    let {
        array[Team] of int: expected_count = [
            if t = 2*p-1 \/ t = 2*p then 1 else 2 endif | t in Team
        ]
    } in
    global_cardinality([schedule[w,p,s] | w in Week, s in Slot], Team, expected_count)
);

% SYMMETRY BREAKING 1: Team 1 structured placement
constraint forall(w in Week) (
    schedule[w, (w div 2) + 1, 1] = 1
);

% SYMMETRY BREAKING 2: Match ordering
constraint forall(w in 1..n_teams-1) (
    match_vars[w, 1] = match_lookup[1, w+1]
);

% SYMMETRY BREAKING 3: First week matches
constraint forall(p in Period) (
    match_vars[1,p] = match_lookup[2*p-1, 2*p]
);

% Search strategy - prioritize early weeks and match variables
solve :: int_search(
    [match_vars[w,p] | w in Week, p in Period], 
    first_fail, 
    indomain_min
) satisfy;

% Output
output [
    "Home/Away Tournament Schedule:\n",
    "(" ++ show(n_teams) ++ " teams, " ++ show(n_weeks) ++ " weeks, " ++ 
    show(n_periods) ++ " periods per week)\n\n"
] ++
[
    "Week " ++ show(w) ++ ":\n" ++
    concat([
        "  Period " ++ show(p) ++ ": Team " ++ show(schedule[w,p,1]) ++ 
        " (home) vs Team " ++ show(schedule[w,p,2]) ++ " (away) [Match #" ++ show(match_vars[w,p]) ++ "]\n"
        | p in Period
    ]) ++ "\n"
    | w in Week
] ++
["\nPeriod usage analysis:\n"] ++
[
    "Period " ++ show(p) ++ ": " ++
    show([sum(w in Week where schedule[w,p,1] = t \/ schedule[w,p,2] = t)(1) | t in Team]) ++
    " (defective: " ++ show(2*p-1) ++ "," ++ show(2*p) ++ ")\n"
    | p in Period
] ++
["\nHome/Away balance per team:\n"] ++
[
    "Team " ++ show(t) ++ ": " ++
    show(sum(w in Week, p in Period where schedule[w,p,1] = t)(1)) ++ " home, " ++
    show(sum(w in Week, p in Period where schedule[w,p,2] = t)(1)) ++ " away\n"
    | t in Team
];