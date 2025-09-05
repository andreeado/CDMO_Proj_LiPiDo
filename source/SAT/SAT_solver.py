from z3 import *
from itertools import combinations
import time
import math
from constraints import *
from utils import *
import json
import os
from argparse import ArgumentParser

exactly_one = exactly_one_he
at_most_one = at_most_one_seq
at_most_k = at_most_k_seq
at_least_k = at_least_k_seq


def STS_SAT(n, time_limit=300, random_seed=False):
    start_time = time.time()
    
    W = n - 1
    P = n // 2
    M = n * (n - 1) // 2
    T1, T2 = build_inverse_tables(n)

    print(f"Solving for {n} teams ===")
    print(f"Teams: {n}, Weeks: {W}, Periods: {P}, Matches: {M}")
    print(f"Time limit: {time_limit}s")
    print(f"Random seed: {random_seed}")

    # PHASE 1: Find a feasible schedule
    print("\n=== PHASE 1: Finding feasible schedule ===")

    # Generate fixed schedule from circle method
    circle_schedule_weeks = {}
    circle_schedule_full = circle_method(n)
    for (w, p), m in circle_schedule_full.items():
        if w not in circle_schedule_weeks:
            circle_schedule_weeks[w] = []
        circle_schedule_weeks[w].append(m)
    
    s = Solver()
    s.set("timeout", time_limit * 1000) # set time_limite (in milliseconds)
    if random_seed:
        s.set("random_seed", int(time.time()))

    # Variable
    # match_period[m][p] is True if match m is in period p
    match_period = [[Bool(f"match_{m}_period_{p}") 
                     for p in range(P)] 
                     for m in range(M + 1)]
    
    # Constraints
    # 1. Each match from the circle schedule must be assigned to exactly one period
    for w in range(W):
        matches_in_week = circle_schedule_weeks[w]
        for m in matches_in_week:
            s.add(exactly_one([match_period[m][p] for p in range(P)], f"one_period_m{m}"))

    # 2. Each period must contain exactly one match from each week
    for w in range(W):
        for p in range(P):
            matches_in_week = circle_schedule_weeks[w]
            s.add(exactly_one([match_period[m][p] for m in matches_in_week], f"one_match_per_slot_w{w}_p{p}"))
    
    # 3. Each team plays at most two match in the same period
    for p in range(P):
        for t in range(1, n + 1):
            team_plays_in_period = []
            for w in range(W):
                matches_in_week = circle_schedule_weeks[w]
                for m in matches_in_week:
                    if T1[m] == t or T2[m] == t:
                        team_plays_in_period.append(match_period[m][p])
            s.add(at_most_k(team_plays_in_period, 2, f"at_most_two_play_t{t}_p{p}"))

    # Implied constraints
    # Each team has exactly one defective period (appears exactly once in that period)
    for t in range(1, n + 1):
        defective_indicators = []
        for p in range(P):
            defective_p = Bool(f"defective_p{p}_t{t}")
            defective_indicators.append(defective_p)
            
            appearances = []
            for w in range(W):
                matches_in_week = circle_schedule_weeks[w]
                for m in matches_in_week:
                    if T1[m] == t or T2[m] == t:
                        appearances.append(match_period[m][p])
            
            s.add(defective_p == exactly_one(appearances, f"defective_p{p}_t{t}_implies_exactly_one"))
        
        s.add(exactly_one(defective_indicators, f"exactly_one_defective_period_t{t}"))

    # Symmetry breaking constraints
    # Fix the first week's periods assignments
    first_week_matches = circle_schedule_weeks[0]
    for p in range(P):
        match_in_period = first_week_matches[p]
        s.add(match_period[match_in_period][p] == True)
    

    print("Solving scheduling phase...")
    schedule_result = s.check()
    phase1_time = time.time() - start_time
    
    # Handle unsat case
    if schedule_result == unsat:
        print(f"No feasible schedule found in {phase1_time:.2f}s")
        return None, phase1_time
    
    # Handle timeout case
    if schedule_result == unknown:
        print(f"Phase 1 timed out.")
        return None, time_limit
    
    schedule_model = s.model()
    print(f"Feasible schedule found in {phase1_time:.2f}s")
    
    # Extract the feasible schedule
    feasible_schedule = {}
    for w in range(W):
        matches_in_week = circle_schedule_weeks[w]
        for m in matches_in_week:
            for p in range(P):
                if is_true(schedule_model.evaluate(match_period[m][p])):
                    feasible_schedule[(w, p)] = m
                    break

    # PHASE 2: Optimize home/away assignments using binary search
    print("\n=== PHASE 2: Optimizing home/away assignments ===")
    
    remaining_time = time_limit - phase1_time
    if remaining_time <= 0:
        print("No time remaining for optimization")
        swap = [BoolVal(False) for _ in range(M + 1)]
        results = (schedule_model, feasible_schedule, None, swap)
        return results, time.time() - start_time

    # Compute the initial imbalance of the feasible solution
    initial_imbalance, _ = calculate_imbalance(n, feasible_schedule, None, None)
    print(f"Initial imbalance (no swaps): {initial_imbalance}")

    # Binary search bounds
    lower_bound = 0
    upper_bound = initial_imbalance
    
    best_solution = None
    best_imbalance = initial_imbalance

    # Swap variables
    swap = [Bool(f"swap_m{m}") for m in range(M + 1)]

    # Pre-compute the home_vars for each team
    team_home_vars = [[] for t in range(n + 1)]
    for t in range(1, n + 1):
        vars_t = []
        for (w, p), m in feasible_schedule.items():
            if T1[m] == t:
                vars_t.append(Not(swap[m]))
            elif T2[m] == t:
                vars_t.append(swap[m])
        team_home_vars[t] = vars_t


    max_team_imbalance = min(n - 1, initial_imbalance)

    print(f"Starting binary search optimization (bounds: {lower_bound}-{upper_bound})")
    
    while lower_bound <= upper_bound and time.time() - start_time < time_limit - 1:
        mid = (lower_bound + upper_bound) // 2
        print(f"Trying total imbalance <= {mid}")
        
        iteration_time = (time_limit - 1) - (time.time() - start_time)

        opt_solver = Solver()
        opt_solver.set("timeout", int(iteration_time * 1000)) # set time_limite (in milliseconds)
        if random_seed:
            opt_solver.set("random_seed", int(time.time()))
        
        # List of bits for the total imbalance (is the sum of all team imbalances)
        total_imbalance_bits = []
        
        for t in range(1, n + 1):
            # Count home games for team t
            home_count = sum([If(var, 1, 0) for var in team_home_vars[t]])
            
            # Create the imbalance bits directly from home_count
            imbalance_bits = [Bool(f"team{t}_imb_bit_{i}") for i in range(max_team_imbalance)]
            
            # Model the imbalance directly from the home_count value
            # imbalance >= k iff abs(2*home_count - (n-1)) >= k+1
            raw_diff = 2 * home_count - (n-1)
            for k in range(1, max_team_imbalance + 1):
                pos_cond = And(raw_diff >= 0, raw_diff >= k+1)
                neg_cond = And(raw_diff < 0, raw_diff <= -(k+1))
                opt_solver.add(imbalance_bits[k-1] == Or(pos_cond, neg_cond))

            # 4. Add ordering constraint for imbalance_bits
            for i in range(1, len(imbalance_bits)):
                opt_solver.add(Or(Not(imbalance_bits[i]), imbalance_bits[i-1]))
            
            # Add these bits to total imbalance calculation
            total_imbalance_bits.extend(imbalance_bits)
        
        # Now we constrain that the sum of all team imbalances <= mid
        total_imbalance = sum([If(bit, 1, 0) for bit in total_imbalance_bits])
        opt_solver.add(total_imbalance <= mid)

        # Symmetry breaking constraint
        # Maintain the original order for the first match
        opt_solver.add(Not(swap[1]))
        
        # Solve
        opt_result = opt_solver.check()
        
        if opt_result == sat:
            swap_model = opt_solver.model()
            actual_imbalance, team_imbalances = calculate_imbalance(n, feasible_schedule, swap_model, swap)
            
            print(f"Solution found with actual imbalance {actual_imbalance} (target was <= {mid})")
            
            if actual_imbalance <= best_imbalance:
                best_solution = (schedule_model, feasible_schedule, swap_model, swap)
                best_imbalance = actual_imbalance
            
            if actual_imbalance == 0:
                print("Optimal solution found!")
                break
                
            # Update bounds
            upper_bound = min(mid - 1, actual_imbalance - 1)
        else:
            print(f"No solution with imbalance <= {mid}")
            lower_bound = mid + 1
    
    total_time = time.time() - start_time
    print(f"\n=== FINAL RESULTS ===")
    print(f"Total time: {total_time:.2f}s")
    print(f"Phase 1 (scheduling): {phase1_time:.2f}s")
    print(f"Phase 2 (optimization): {total_time - phase1_time:.2f}s")
    
    if best_solution:
        print(f"Best imbalance found: {best_imbalance}")
        return best_solution, total_time
    else:
        print("Using feasible solution with no optimization")
        swap = [BoolVal(False) for _ in range(M + 1)]
        results = (schedule_model, feasible_schedule, None, swap)
        return results, total_time



def format_and_save_solution(n: int, result: tuple, runtime: float, time_limit: int, filepath: str):
    """
    Formats the SAT solver output and saves it to a JSON file.
    """
    if result is None or result[0] is None:
        is_timeout = runtime >= time_limit

        output_data = {
            "z3_sat_solver": {
                "time": time_limit if is_timeout else math.floor(runtime),
                "optimal": not is_timeout,  # True for UNSAT, False for TIMEOUT
                "obj": None,
                "sol": []
            }
        }

    else:
        _, feasible_schedule, swap_model, swap = result
        
        W = n - 1
        P = n // 2
        T1, T2 = build_inverse_tables(n)

        # 1. Format the solution into the required (n/2)x(n-1) matrix
        sol_matrix = [[[] for _ in range(W)] for _ in range(P)]
        for (w, p), m in feasible_schedule.items():
            try:
                swap_val = is_true(swap_model.evaluate(swap[m]))
            except Z3Exception:
                swap_val = False

            home, away = (T2[m], T1[m]) if swap_val else (T1[m], T2[m])
            sol_matrix[p][w] = [home, away]

        # 2. Calculate final metrics
        total_imbalance, _ = calculate_imbalance(n, feasible_schedule, swap_model, swap)
        
        # If timeout is reached without solving, time should be 300 and optimal false.
        is_optimal = runtime < time_limit
        solve_time = math.floor(runtime)
        if not is_optimal:
            solve_time = time_limit

        # 3. Construct the JSON output object
        output_data = {
            "z3_sat_solver": {
                "time": solve_time,
                "optimal": is_optimal,
                "obj": total_imbalance,
                "sol": sol_matrix
            }
        }

    # 4. Load existing data and update it
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        data = {}

    data.update(output_data)

    # 5. Write the updated data back to the file
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
    
    print(f"Solution successfully saved to {filepath}")


if __name__ == "__main__":
    parser = ArgumentParser(description="Solve the Sports Tournament Scheduling problem using a SAT solver.")
    parser.add_argument("n_teams", type=int, help="Number of teams (must be even)")
    parser.add_argument("--time_limit", type=int, default=300, help="Time limit in seconds for the solver")
    parser.add_argument("--random_seed", type=bool, default=False, help="Set a random seed for the solver")
    args = parser.parse_args()

    if args.n_teams % 2 != 0:
        raise ValueError("Number of teams must be an even number.")

    # Run the solver
    result, runtime = STS_SAT(args.n_teams, args.time_limit, args.random_seed)

    
    # Check if the path exists in Docker env
    if os.path.exists("/app/res"):
        res_path = f"/app/res/SAT/{args.n_teams}.json"
    else: # in local env
        res_path = f"../../res/SAT/{args.n_teams}.json"

    format_and_save_solution(
        n=args.n_teams,
        result=result,
        runtime=runtime,
        time_limit=args.time_limit,
        filepath=res_path
    )
