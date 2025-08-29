% CSPLib Problem 026 — Round Robin Tournament
% http://www.csplib.org/Problems/prob026/
% Home/Away Tournament Scheduler
% n teams, n-1 weeks, n/2 periods per week, 2 slots per period
% Slot 1: home team, Slot 2: away team (plays at slot 1 team's venue)
include "alldifferent.mzn";
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

% Function to calculate match number (adjusted for 1-based teams)
function int: match_number(int: t1, int: t2) = 
  n_matches - ((n_teams - (t1-1)) * (n_teams - (t1-1) - 1)) div 2 + (t2 - t1 - 1);

% Create lookup table for valid (team1, team2, match_number) triples
array[1..n_matches] of int: table_t1 = [t1 | t1 in Team, t2 in Team where t1 < t2];
array[1..n_matches] of int: table_t2 = [t2 | t1 in Team, t2 in Team where t1 < t2];
array[1..n_matches] of int: table_match = [match_number(t1, t2) | t1 in Team, t2 in Team where t1 < t2];

% Decision variables: which team is in each slot
% schedule[w,p,s] = team playing in week w, period p, slot s
array[Week, Period, Slot] of var Team: schedule;

% NEW: Match variables for dual encoding
array[Week, Period] of var Match: match_vars;

% CHANNELING CONSTRAINT: Link schedule variables to match variables
constraint forall(w in Week, p in Period) (
    exists(i in 1..n_matches) (
        schedule[w,p,1] = table_t1[i] /\ 
        schedule[w,p,2] = table_t2[i] /\ 
        match_vars[w,p] = table_match[i]
    ) \/
    exists(i in 1..n_matches) (
        schedule[w,p,1] = table_t2[i] /\ 
        schedule[w,p,2] = table_t1[i] /\ 
        match_vars[w,p] = table_match[i]
    )
);

% CONSTRAINT 1: Every team plays exactly once per week (using alldifferent on slices)
constraint forall(w in Week) (
    alldifferent([schedule[w,p,s] | p in Period, s in Slot])
);

% CONSTRAINT 2: Every team plays at most twice in same period (REDUNDANT - handled by symmetry breaking)
% CONSTRAINT 3&4: Every team plays every other team exactly once (no self-play)
% REPLACED BY: All matches are different using match variables
constraint alldifferent([match_vars[w,p] | w in Week, p in Period]);

% SYMMETRY BREAKING: Defective teams pattern
% In period p, teams 2p-1 and 2p are defective (appear only once across tournament)
constraint forall(p in Period) (
    let {
        int: defective1 = 2*p - 1,
        int: defective2 = 2*p
    } in (
        % Defective teams appear exactly once in their designated period
        sum(w in Week, s in Slot) (bool2int(schedule[w,p,s] = defective1)) = 1 /\
        sum(w in Week, s in Slot) (bool2int(schedule[w,p,s] = defective2)) = 1 /\
        % All other teams appear exactly twice in this period
        forall(t in Team where t != defective1 /\ t != defective2) (
            sum(w in Week, s in Slot) (bool2int(schedule[w,p,s] = t)) = 2
        )
    )
);

% ADDITIONAL SYMMETRY BREAKING: Team 1 structured placement
% Team 1 plays at home: week 1 in period 1, weeks 2-3 in period 2, weeks 4-5 in period 3, etc.
constraint forall(w in Week) (
    schedule[w, (w div 2) + 1, 1] = 1
);

% NEW SYMMETRY BREAKING: Match ordering from original model
% The match '1 versus t' (with t > 1) appears at week t-1
constraint forall(w in Week where w < n_teams) (
    count([match_vars[w,p] | p in Period], match_number(1, w+1)) = 1
);

% Search strategy - exploit problem structure
solve satisfy;
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
    "Period " ++ show(p) ++ " usage per team: " ++
    show([sum(w in Week, s in Slot) (bool2int(schedule[w,p,s] = t)) | t in Team]) ++
    "\n"
    | p in Period
] ++
["\nHome/Away balance per team:\n"] ++
[
    "Team " ++ show(t) ++ ": " ++
    show(sum(w in Week, p in Period) (bool2int(schedule[w,p,1] = t))) ++ " home, " ++
    show(sum(w in Week, p in Period) (bool2int(schedule[w,p,2] = t))) ++ " away\n"
    | t in Team
];