from argparse import ArgumentParser
import os
from pulp import *
import time, math
import logging
from utils import *

logger = logging.getLogger(__name__)

def solve(solver_name, params, verbose, optimize=False, symmetry_breaking=False): 
    # PHASE 1: FEASIBILITY
    prob = LpProblem("STS_Feasibility", LpMinimize)
    try:
        data = create_data(params['n_teams'])
        init_time = time.time()
        schedule= generate_circle_schedule(data['n_teams'])
        results = set_constraints_circle(prob, schedule, data, symmetry_breaking=symmetry_breaking)
        match solver_name:
            case 'gurobi':
                solver=GUROBI(msg=verbose, timeLimit=params['timeout'], threads=1)
            case 'HiGHS':
                if params.get('n_teams') in [12,18]:
                    solver=HiGHS(msg=verbose, timeLimit=math.ceil(params['timeout']), threads=1, mip_detect_symmetry=False)
                else:
                    solver=HiGHS(msg=verbose, timeLimit=math.ceil(params['timeout']), threads=1)
            case _:
                raise KeyError('Unsupported solver')
        prob.solve(solver)
    except MemoryError: 
        return [], "N/A", False, params['timeout']
    
    sol = []
    opt = False
    solve_time = math.floor(time.time() - init_time)

    # Check if timeout occurred (PuLP may not properly detect Gurobi timeout status)
    timeout_occurred = solve_time >= params['timeout']

    match prob.sol_status:
        # SOLUTION FOUND
        case const.LpSolutionOptimal | const.LpSolutionIntegerFeasible:
            logger.info("Solution found during feasibility phase.")
            x, T1, T2, data, circle_schedule = results
            sol = extract_schedule_from_matches(x, T1, T2, data, circle_schedule)
            obj = None
            opt = True if not timeout_occurred else False
        # INFEASIBLE SOLUTION
        case const.LpSolutionInfeasible:
            # Only mark as infeasible if no timeout occurred
            if not timeout_occurred:
                logger.info("Infeasible solution found during feasibility phase.")
                sol = []
                obj = None
                opt = True
                solve_time = 0
            else:
                # Timeout before finding solution
                logger.info("Timeout occurred before finding solution during feasibility phase.")
                sol = []
                obj = None
                opt = False
        # ANY OTHER CASE FOR SAFETY
        case _:
            sol = []
            obj = None
            opt = False
    
    # PHASE 2: OPTIMIZATION (if requested and time permits)
    if optimize and sol:
        remaining_time = params['timeout'] - solve_time
        
        if remaining_time > 0:            
            # Create new optimization problem
            opt_prob = LpProblem("STS_HomeAway_Optimization", LpMinimize)
            
            try:
                swap_vars = set_optimization(opt_prob, sol, data, symmetry_breaking=symmetry_breaking)
                
                # Configure solver with remaining time
                match solver_name:
                    case 'gurobi':
                        opt_solver = GUROBI(msg=verbose, timeLimit=remaining_time, threads=1)
                    case 'HiGHS':
                        opt_solver = HiGHS(msg=verbose, timeLimit=math.ceil(remaining_time), threads=1)
                    case _:
                        raise KeyError('Unsupported solver')
                
                opt_prob.solve(opt_solver)
                
                # Process optimization results
                if opt_prob.sol_status in [const.LpSolutionOptimal, const.LpSolutionIntegerFeasible]:
                    # Apply swaps to the schedule
                    sol = apply_swaps(sol, swap_vars, data)
                    obj = 0 if opt_prob.objective.value() is None else round(opt_prob.objective.value())
                    opt = (opt_prob.sol_status == const.LpSolutionOptimal)
                    logger.info(f"Optimization completed")
                else:
                    logger.info("Optimization not completed, keeping feasible solution")
                    
            except Exception as e:
                logger.warning(f"Optimization phase failed. Returning feasible solution.")
        else:
            logger.info("No time remaining for optimization phase.")
    
    total_time = math.floor(time.time() - init_time)
    return create_solution_data(solver_name, sol, obj, opt, total_time, optimize=optimize, symmetry_breaking=symmetry_breaking)


def generate_circle_schedule(n_teams):
        """
        Generate initial opponent schedule using circle method
        """
        schedule = {}
        # Create teams list: 0 to n-2 in circle, team n-1 fixed
        teams = list(range(n_teams-1))
        fixed_team = n_teams - 1
        
        for week in range(n_teams - 1):
            week_games = []
            
            # Fixed team always plays against team at position 0
            opponent = teams[0]
            match_id = match_ID(min(fixed_team+1, opponent+1), max(fixed_team+1, opponent+1), n_teams)
            week_games.append(match_id)
            
            # Pair remaining teams
            for i in range(1, (n_teams-1)//2 + 1):
                team1 = teams[i]
                team2 = teams[-(i)]
                t1, t2 = team1 + 1, team2 + 1
                match_id = match_ID(min(t1, t2), max(t1, t2), n_teams)
                week_games.append(match_id)            
            # Store games for this week
            schedule[week] = week_games
            
            # Rotate teams (first team goes to end, others shift left)
            teams = teams[1:] + [teams[0]] 
        return schedule

def set_constraints_circle(problem, schedule, data, symmetry_breaking=False):
    n_teams = data['n_teams']
    n_weeks = data['n_weeks']
    n_periods = data['n_periods']
    Teams = data['teams']
    Periods = data['periods']

    # Total number of matches
    M = n_teams * (n_teams - 1) // 2
    
    # Build inverse tables for match lookup
    T1, T2 = build_inverse_tables(n_teams)

    # --------- DECISION VARIABLES ---------
    # x[m,p] = 1 if match m is played in period p
    x = {}
    for m in range(1, M + 1):
        for p in range(n_periods):
            x[m, p] = LpVariable(f"match_period_{m}_{p}", cat='Binary')
    
    # auxiliary variables for defective periods. 
    # defective[t,p] = 1 iff team t appears exactly once in period p
    defective = {}
    for t in Teams:
        for p in Periods:
            defective[t, p] = LpVariable(f"defective_{t}_{p}", cat='Binary')

    # --------- OBJECTIVE FUNCTION ---------
    problem += 0 #minimize zero (feasibility problem)

    # --------- CONSTRAINTS ---------
    # Constraint 1: Each match must be assigned to exactly one period
    for m in range(1, M + 1):
        problem += lpSum([x[m, p] for p in range(n_periods)]) == 1
    
    # Constraint 2: Each period must contain exactly one match from each week
    for w in range(n_weeks):
        for p in range(n_periods):
            matches_in_week = schedule[w]
            problem += lpSum([x[m, p] for m in matches_in_week]) == 1
    
    # Constraint 3: Each team plays at most 2 matches in the same period
    for p in range(n_periods):
        for t in Teams:
            # Find all matches involving team t (t is 0-indexed, but T1/T2 are 1-indexed)
            team_matches = []
            for m in range(1, M + 1):
                if T1[m] == t+1 or T2[m] == t+1:
                    team_matches.append(x[m, p])
            problem += lpSum(team_matches) <= 2
    
    # Constraint 4: Each team has exactly one defective period (appears exactly once)
    for t in Teams:
        # Each team has exactly one defective period
        problem += lpSum([defective[t, p] for p in range(n_periods)]) == 1
        
        # Link defective variable to team appearances
        for p in range(n_periods):
            # Find all matches involving team t (t is 0-indexed, but T1/T2 are 1-indexed)
            team_matches = []
            for m in range(1, M + 1):
                if T1[m] == t+1 or T2[m] == t+1:
                    team_matches.append(x[m, p])
            team_appearances = lpSum(team_matches)
            
            # Lower bound: if defective, must appear at least once
            problem += team_appearances >= defective[t, p]
            
            # Upper bound: if defective, appear exactly once; otherwise at most 2
            problem += team_appearances <= 1 + (1 - defective[t, p]) * 1

    if symmetry_breaking:
        """ # SYMMETRY BREAKING: first week in consecutive periods starting from 0
        for idx, m in enumerate(schedule[0]):
            period = idx  # Periods 0, 1, 2, ... for matches 0, 1, 2, ...
            problem += x[m, period] == 1 """
        # SYMMETRY BREAKING: first match to first period
        first_match = schedule[0][0]
        problem += x[first_match, 0] == 1

    return x, T1, T2, data, schedule

def set_optimization(problem, feasible_schedule, data, symmetry_breaking=False):
    n_teams = data['n_teams']
    n_weeks = data['n_weeks']
    Teams = data['teams']
    Periods = data['periods']
    lower_bound = 1
    upper_bound = n_teams - 1

    # --------- DECISION VARIABLES ---------
    # swap[p,w] = 1 if we swap home/away for the match in period p, week w
    swap = {}
    for p in Periods:
        for w in range(n_weeks):
            if feasible_schedule[p][w]:  # Only for non-empty slots
                swap[p, w] = LpVariable(f"swap_{p}_{w}", cat='Binary')
    
    # Auxiliary variables for balance optimization
    max_imbalance = LpVariable(name='max_imbalance', lowBound=lower_bound, upBound=upper_bound, cat='Integer')
    balance_pos = {}
    balance_neg = {}
    for t in Teams:
        balance_pos[t] = LpVariable(f"balance_pos_{t}", lowBound=0, cat='Integer')
        balance_neg[t] = LpVariable(f"balance_neg_{t}", lowBound=0, cat='Integer')
    
    # --------- OBJECTIVE FUNCTION ---------
    # Minimize maximum home-away imbalance
    problem += max_imbalance
    
    # --------- CONSTRAINTS ---------
    # Calculate home and away games for each team
    for t in Teams:
        team_id = t + 1  # Convert to 1-indexed
        home_games = []
        away_games = []
        
        for p in Periods:
            for w in range(n_weeks):
                if not feasible_schedule[p][w]:
                    continue
                    
                home_team, away_team = feasible_schedule[p][w]
                
                if home_team == team_id:
                    # Originally home: home if not swapped, away if swapped
                    home_games.append(1 - swap[p, w])
                    away_games.append(swap[p, w])
                elif away_team == team_id:
                    # Originally away: away if not swapped, home if swapped
                    away_games.append(1 - swap[p, w])
                    home_games.append(swap[p, w])
        
        # Balance constraint: home_count - away_count = balance_pos - balance_neg
        home_count = lpSum(home_games) if home_games else 0
        away_count = lpSum(away_games) if away_games else 0
        problem += home_count - away_count == balance_pos[t] - balance_neg[t]
        
        # Link to max imbalance
        problem += balance_pos[t] + balance_neg[t] <= max_imbalance

        if symmetry_breaking:
            # SYMMETRY BREAKING: first cell no swap
            problem += swap[0,0] == 0
    return swap


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    parser = ArgumentParser()
    parser.add_argument("n_teams", type=int, help="Number of teams (must be even)")

    parser.add_argument("--solver_name", type=str, default="gurobi",
                        choices=["gurobi", "HiGHS"],
                        help="Solver name (default: gurobi)")
    
    parser.add_argument("--time_limit", type=int, default=300,
                        help="Time limit in seconds (default: 300)")
    
    # add optimization flag
    parser.add_argument("--optimality", action='store_true',
                        help="Enable optimization phase after feasibility (default: False)")
    
    # add symmetry breaking flag
    parser.add_argument("--sb", action='store_true',
                        help="Enable symmetry breaking (default: False)")
    
    args = parser.parse_args()
    if args.n_teams % 2 != 0:
        raise ValueError("Number of teams must be an even integer")
    
    # Set up parameters
    n_teams = args.n_teams
    timeout = args.time_limit
    params = {'timeout': timeout,
              'n_teams': n_teams}
    verbose = 0  # Solver verbosity
         
    
    result_data = solve(args.solver_name, params, verbose, optimize=args.optimality, symmetry_breaking=args.sb)
    
    # Extract values from the result dictionary
    solver_result = next(iter(result_data.values()))
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