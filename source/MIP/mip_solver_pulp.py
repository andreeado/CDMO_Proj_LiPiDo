from argparse import ArgumentParser
import os
from pulp import *
import time, math
import logging
from utils import *


logger = logging.getLogger(__name__)

def solve(solver_name, params, verbose): 
    prob = LpProblem("STS", LpMinimize)
    try:
        data = create_data(params['n_teams'])
        init_time = time.time()
        schedule= generate_circle_schedule(data['n_teams'])
        results = set_constraints_circle(prob, schedule, data)
        match solver_name:
            case 'cbc':
                solver=PULP_CBC_CMD(msg=verbose, timeLimit=params['timeout'], presolve=False, cuts=False, threads=1)
            case 'gurobi':
                solver=GUROBI(msg=verbose, timeLimit=params['timeout'], threads=1)
            case 'HiGHS':
                solver=HiGHS(msg=verbose, timeLimit=math.ceil(params['timeout']), threads=1)
            case _:
                raise KeyError('Unsupported solver')
        prob.solve(solver)
    except MemoryError: 
        return [], "N/A", False, params['timeout']
    
    sol = []
    obj = "None"
    opt = False
    solve_time = math.floor(time.time() - init_time)

    match prob.sol_status:
        # OPTIMAL SOLUTION FOUND
        case const.LpSolutionOptimal:
            sol = extract_schedule(*results)
            obj = 0 if prob.objective.value() is None else round(prob.objective.value())
            if solve_time<300:
                opt = True
        # NOT OPTIMAL SOLUTION FOUND
        case const.LpSolutionIntegerFeasible:
            sol = extract_schedule(*results)
            obj = 0 if prob.objective.value() is None else round(prob.objective.value())
            opt = False
            solve_time = int(params['timeout'])
        # INFEASIBLE SOLUTION
        case const.LpSolutionInfeasible:
            sol = []
            obj = "None"
            opt = True
            solve_time = 0
        # TIMEOUT
        case _:
            sol = []
            obj = "None"
            opt = False
            solve_time = int(params['timeout'])
    return create_solution_data(solver_name, sol, obj, opt, solve_time)


def generate_circle_schedule(n_teams):
        """
        Generate initial opponent schedule using circle method
        Returns: Dictionary mapping (week, team1, team2) -> True for games
        """
        schedule = {}
        # Create teams list: 0 to n-2 in circle, team n-1 fixed
        teams = list(range(n_teams-1))
        fixed_team = n_teams - 1
        
        for week in range(n_teams - 1):
            week_games = []
            
            # Fixed team always plays against team at position 0
            opponent = teams[0]
            week_games.append((fixed_team, opponent))
            
            # Pair remaining teams
            for i in range(1, (n_teams-1)//2 + 1):
                team1 = teams[i]
                team2 = teams[-(i)]
                week_games.append((team1, team2))
            
            # Store games for this week
            for game in week_games:
                t1, t2 = game
                schedule[(week, min(t1, t2), max(t1, t2))] = True
            
            # Rotate teams (first team goes to end, others shift left)
            teams = teams[1:] + [teams[0]] 
        return schedule

def set_constraints_circle(problem, schedule, data):
    n_teams = data['n_teams']
    n_weeks = data['n_weeks']
    n_periods = data['n_periods']
    Teams = data['teams']
    Weeks = data['weeks']
    Periods = data['periods']
    lower_bound = 1
    upper_bound = n_teams - 1 

    # convert circle schedule to week-based format
    circle_schedule_weeks = {}
    for (w, t1, t2) in schedule.keys():
        if w not in circle_schedule_weeks:
            circle_schedule_weeks[w] = []
        circle_schedule_weeks[w].append((t1, t2))

    # --------- DECISION VARIABLES ---------
    # x[i,j,k,p] = 1 if team i plays at home against team j in week k, period p
    x = {}
    for i in Teams:
        for j in Teams:
            for k in Weeks:
                for p in Periods:
                    x[i, j, k, p] = LpVariable(f"x_{i}_{j}_{k}_{p}", cat='Binary')
    
    # auxiliary variables for defective periods. 
    # defective[t,p] = 1 iff team t appears exactly once in period p
    defective = {}
    for t in Teams:
        for p in Periods:
            defective[t, p] = LpVariable(f"defective_{t}_{p}", cat='Binary')

    # auxiliary variables for balance constraints
    # variable to track maximum imbalance
    max_imbalance = LpVariable(name='max_imbalance', lowBound=lower_bound, upBound=upper_bound, cat='Integer')
    
    # positive and negative balance variables
    balance_pos = {}
    balance_neg = {}
    for t in Teams:
        balance_pos[t] = LpVariable(f"balance_pos_{t}", lowBound=0)
        balance_neg[t] = LpVariable(f"balance_neg_{t}", lowBound=0)

    # --------- OBJECTIVE FUNCTION ---------
    # problem += 0, minimize zero (feasibility problem)
    # optimization version
    for t in Teams:
        # each team's imbalance must be <= max_imbalance
        problem += balance_pos[t] + balance_neg[t] <= max_imbalance

    # Minimize the maximum imbalance
    problem += max_imbalance

    # --------- CONSTRAINTS ---------
    # Constraint 1: Each match from circle schedule must be assigned to exactly one period
    for w in range(n_weeks):
        matches_in_week = circle_schedule_weeks[w]
        for t1, t2 in matches_in_week:
            problem += lpSum([x[t1, t2, w, p] + x[t2, t1, w, p] for p in Periods]) == 1
    
    # Constraint 2: Each period must contain exactly one match from each week
    for w in range(n_weeks):
        for p in range(n_periods):
            matches_in_week = circle_schedule_weeks[w]
            problem += lpSum([x[t1, t2, w, p] + x[t2, t1, w, p] for t1, t2 in matches_in_week]) == 1

    # Constraint 3: Each team plays at most 2 matches in the same period
    for p in range(n_periods):
        for t in range(n_teams):
            team_appearances = []
            for w in range(n_weeks):
                matches_in_week = circle_schedule_weeks[w]
                for t1, t2 in matches_in_week:
                    if t1 == t or t2 == t:
                        team_appearances.append(x[t1, t2, w, p] + x[t2, t1, w, p])
            problem += lpSum(team_appearances) <= 2
        
    # Constraint 4: Prevent any games not in circle schedule from being played
    for w in range(n_weeks):
        week_games = set((min(t1,t2), max(t1,t2)) for t1, t2 in circle_schedule_weeks[w])
        
        for t1 in range(n_teams):
            for t2 in range(t1 + 1, n_teams):
                if (t1, t2) not in week_games:
                    problem += lpSum([x[t1, t2, w, p] + x[t2, t1, w, p] for p in Periods]) == 0
    
    # Constraint 5: Each team has exactly one defective period (appears exactly once)
    for t in range(n_teams):
        # Each team has exactly one defective period
        problem += lpSum([defective[t, p] for p in Periods]) == 1
        
        # Link defective variable to team appearances
        for p in range(n_periods):
            team_appearances = []
            for w in range(n_weeks):
                matches_in_week = circle_schedule_weeks[w]
                for t1, t2 in matches_in_week:
                    if t1 == t or t2 == t:
                        team_appearances.append(x[t1, t2, w, p] + x[t2, t1, w, p])
            # lower bound
            problem += lpSum(team_appearances) >= defective[t, p]
            # upper bound
            problem += lpSum(team_appearances) <= 1 + (1 - defective[t, p]) * n_weeks
    
    # Constraint 6: Bound variables to home-away games balance
    for t in Teams:
        home_expr = lpSum([x[t, j, w, p] for j in Teams if j != t for w in Weeks for p in Periods])
        away_expr = lpSum([x[j, t, w, p] for j in Teams if j != t for w in Weeks for p in Periods])
        problem += (home_expr - away_expr == balance_pos[t] - balance_neg[t])

    return x, data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    parser = ArgumentParser()
    parser.add_argument("n_teams", type=int, help="Number of teams (must be even)")

    parser.add_argument("--solver_name", type=str, default="cbc",
                        choices=["cbc", "gurobi", "HiGHS"],
                        help="Solver name (default: cbc)")
    
    args = parser.parse_args()
    if args.n_teams % 2 != 0:
        raise ValueError("Number of teams must be an even integer")
    
    # Set up parameters
    n_teams = args.n_teams
    params = {'timeout': 300,
              'n_teams': n_teams}
    verbose = 1  # Solver verbosity
    result_data = solve(args.solver_name, params, verbose)
    
    # Extract values from the result dictionary
    solver_result = result_data[args.solver_name]
    sol = solver_result["sol"]
    obj = solver_result["obj"]
    opt = solver_result["optimal"]
    solve_time = solver_result["time"]

    print(f"\nSolver results:")
    print(f"Optimal: {opt}")
    print(f"Objective: {obj}")
    print(f"Solve time: {solve_time}")
    
    # Save solution to file
    if os.path.exists("/app/res"):
        # docker
        res_path = f"/app/res/MIP/{args.n_teams}.json"
    else:
        # local
        res_path = f"../../res/MIP/{args.n_teams}.json"
    save_solution(result_data, res_path)

    if sol:
        # Display the schedule
        display_schedule(sol, n_teams, n_teams-1, n_teams//2)
        # Analyze home-away balance
        analyze_home_away_balance(sol, n_teams, n_teams-1, n_teams//2)
    else:
        print("No solution found")