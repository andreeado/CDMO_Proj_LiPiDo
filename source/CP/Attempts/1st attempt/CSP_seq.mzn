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

set of int: Team = 1..n_teams;
set of int: Week = 1..n_weeks;
set of int: Period = 1..n_periods;
set of int: Slot = 1..2;  % 1 = home, 2 = away

% Decision variables: which team is in each slot
% schedule[w,p,s] = team playing in week w, period p, slot s
array[Week, Period, Slot] of var Team: schedule;

% CONSTRAINT 1: Every team plays exactly once per week (using alldifferent on slices)
constraint forall(w in Week) (
    alldifferent([schedule[w,p,s] | p in Period, s in Slot])
);

% CONSTRAINT 2: Every team plays at most twice in same period (REDUNDANT - handled by symmetry breaking)

% CONSTRAINT 3&4: Every team plays every other team exactly once (no self-play)
constraint forall(t in Team) (
    alldifferent([t] ++ [
        if schedule[w,p,1] = t then schedule[w,p,2] 
        else schedule[w,p,1] endif
        | w in Week, p in Period where schedule[w,p,1] = t \/ schedule[w,p,2] = t
    ])
);

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
        " (home) vs Team " ++ show(schedule[w,p,2]) ++ " (away)\n"
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