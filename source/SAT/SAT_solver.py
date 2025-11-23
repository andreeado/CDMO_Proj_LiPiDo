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


def STS_SAT(n, time_limit=300, optimality=False, seed=42, verbose=False):
    start_time = time.time()
    
    W = n - 1
    P = n // 2
    M = n * (n - 1) // 2
    T1, T2 = build_inverse_tables(n)
    if verbose:
        print(f"Solving for {n} teams ===")
        print(f"Teams: {n}, Weeks: {W}, Periods: {P}, Matches: {M}")
        print(f"Time limit: {time_limit}s")
        print(f"Seed: {seed}")

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
    if seed:
        s.set("random_seed", seed)

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
    
    if verbose:
        print("Solving scheduling phase...")
    schedule_result = s.check()
    phase1_time = time.time() - start_time
    
    # Handle unsat case
    if schedule_result == unsat:
        if verbose:    
            print(f"No feasible schedule found in {phase1_time:.2f}s")
        return None, phase1_time
    
    # Handle timeout case
    if schedule_result == unknown:
        if verbose:
            print(f"Phase 1 timed out.")
        return None, time_limit
    
    schedule_model = s.model()
    if verbose:
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
    if optimality:
        if verbose:
            print("\n=== PHASE 2: Optimizing home/away assignments ===")

        remaining_time = time_limit - phase1_time
        if remaining_time <= 0:
            if verbose:
                print("No time remaining for optimization")
            swap = [BoolVal(False) for _ in range(M + 1)]
            results = (schedule_model, feasible_schedule, None, swap)
            return results, time.time() - start_time

        # Compute the initial imbalance of the feasible solution
        initial_imbalance, initial_team_imbalances = compute_imbalance(n, feasible_schedule, None, None)
        best_max_imbalance = max(initial_team_imbalances) if initial_team_imbalances else W

        if verbose:
            print(f"Initial imbalance (no swaps):\t{initial_imbalance}")

        # Binary search bounds
        lower_bound = 0
        upper_bound = W

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
        if verbose:
            print(f"Starting binary search optimization (bounds: {lower_bound}-{upper_bound})")

        while lower_bound <= upper_bound and time.time() - start_time < time_limit - 1:
            mid = (lower_bound + upper_bound) // 2

            if verbose:
                print(f"Trying imbalance <= {mid} for every team\t(total imbalance <= {mid*n})")

            iteration_time = (time_limit - 1) - (time.time() - start_time)

            opt_solver = Solver()
            opt_solver.set("timeout", int(iteration_time * 1000)) # set time_limite (in milliseconds)

            if seed:
                opt_solver.set("random_seed", seed)

            for t in range(1, n + 1):
                # Create the imbalance bits directly from home_count
                imbalance_bits = [Bool(f"team{t}_imb_bit_{i}") for i in range(max_team_imbalance)]
                home_vars_t = team_home_vars[t]

                target = (n - 1) / 2  # ideal values for home/away games

                for k in range(1, max_team_imbalance + 1):
                    conds = []

                    # case too many home games: sum(home_vars_t) >= upper_bound_hg
                    upper_bound_hg = math.ceil(target + k)
                    if upper_bound_hg <= len(home_vars_t):
                        geq_var = Bool(f"too_many_home_t{t}_k{upper_bound_hg}")

                        opt_solver.add(Or(Not(geq_var),
                                          at_least_k(home_vars_t, upper_bound_hg,
                                                     f"t{t}_at_least_{upper_bound_hg}")))

                        if upper_bound_hg > 0:
                            opt_solver.add(Or(geq_var,
                                              at_most_k(home_vars_t, upper_bound_hg - 1,
                                                        f"t{t}_at_most_{upper_bound_hg-1}")))
                        conds.append(geq_var)

                    # case too few home games: sum(home_vars_t) <= lower_bound_hg
                    lower_bound_hg = math.floor(target - k)
                    if lower_bound_hg >= 0:
                        leq_var = Bool(f"too_few_home_t{t}_k{lower_bound_hg}")

                        opt_solver.add(Or(Not(leq_var),
                                          at_most_k(home_vars_t, lower_bound_hg,
                                                    f"t{t}_at_most_{lower_bound_hg}")))

                        if lower_bound_hg < len(home_vars_t):
                            opt_solver.add(Or(leq_var,
                                              at_least_k(home_vars_t, lower_bound_hg + 1,
                                                         f"t{t}_at_least_{lower_bound_hg+1}")))
                        conds.append(leq_var)


                    if conds:
                        opt_solver.add(imbalance_bits[k-1] == Or(*conds))
                    else:
                        opt_solver.add(imbalance_bits[k-1] == False)

                # 4. Add ordering constraint for imbalance_bits
                for i in range(1, len(imbalance_bits)):
                    opt_solver.add(Or(Not(imbalance_bits[i]), imbalance_bits[i-1]))

                # Add constraint imbalance_t <= mid
                for i in range(mid, max_team_imbalance):
                    opt_solver.add(Not(imbalance_bits[i]))

            # Symmetry breaking constraint
            # Maintain the original order for the first match
            opt_solver.add(Not(swap[1]))

            # Solve
            opt_result = opt_solver.check()

            if opt_result == sat:
                swap_model = opt_solver.model()
                actual_imbalance, team_imbalances = compute_imbalance(n, feasible_schedule, swap_model, swap)
                actual_max_team_imbalance = max(team_imbalances) if team_imbalances else 0

                if verbose:
                    print(f"Solution found with total imbalance =\t{actual_imbalance}")
                
                # Give priority to min-max
                if actual_max_team_imbalance < best_max_imbalance:
                    best_max_imbalance = actual_max_team_imbalance
                    best_imbalance = actual_imbalance
                    best_solution = (schedule_model, feasible_schedule, swap_model, swap)
                
                # If actual max is equal => save the solution with the best total imbalance
                elif actual_max_team_imbalance == best_max_imbalance:
                    if actual_imbalance < best_imbalance:
                        best_imbalance = actual_imbalance
                        best_solution = (schedule_model, feasible_schedule, swap_model, swap)
                
                # Goal = total imbalance = 0
                if actual_imbalance == 0:
                    if verbose:
                        print("Optimal solution found!")
                    break

                # Update bounds
                upper_bound = mid-1
            else:
                if verbose:
                    print(f"No solution with imbalance <= {mid} for every team\t(total imbalance <= {mid*n})")
                lower_bound = mid + 1

        total_time = time.time() - start_time
        if verbose:
            print(f"\n=== FINAL RESULTS ===")
            print(f"Total time: {total_time:.2f}s")
            print(f"Phase 1 (scheduling): {phase1_time:.2f}s")
            print(f"Phase 2 (optimization): {total_time - phase1_time:.2f}s")

        if best_solution:
            if verbose:
                print(f"Best imbalance found: {best_imbalance}")
            return best_solution, total_time
        else:
            if verbose:
                print("Using feasible solution with no optimization")
            swap = [BoolVal(False) for _ in range(M + 1)]
            results = (schedule_model, feasible_schedule, None, swap)
            return results, total_time
        
    # If we asked only for the satisfiable solution
    else:
        swap = [BoolVal(False) for _ in range(M + 1)]
        results = (schedule_model, feasible_schedule, None, swap)
        return results, phase1_time



def format_and_save_solution(n: int, result: tuple, runtime: float, time_limit: int, filepath: str, optimality: bool):
    """
    Formats the SAT solver output and saves it to a JSON file.
    """


    is_timeout = runtime >= time_limit
    is_optimal = optimality and (not is_timeout)

    if result is None or result[0] is None:

        output_data = {
            "z3_sat_solver": {
                "time": time_limit if is_timeout else math.floor(runtime),
                "optimal": is_optimal,  # True for UNSAT (if we required optimality), False for TIMEOUT
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
                swap_val = is_true(swap_model.evaluate(swap[m])) if swap_model else False
            except Z3Exception:
                swap_val = False

            home, away = (T2[m], T1[m]) if swap_val else (T1[m], T2[m])
            sol_matrix[p][w] = [home, away]

        # 2. Calculate final metrics
        total_imbalance, _ = compute_imbalance(n, feasible_schedule, swap_model, swap)
        
        # If timeout is reached without solving, time should be 300 and optimal false.
        solve_time = math.floor(runtime)
        if is_timeout:
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
    parser.add_argument("--optimality", action='store_true', help="Search for the optimal solution (default: False)")
    parser.add_argument("--seed", type=int, default=42, help="Set a seed for the solver (default: 42)")
    parser.add_argument("--verbose", action='store_true', help="Receive feedback from the solver (default: False)")

    args = parser.parse_args()

    if args.n_teams % 2 != 0:
        raise ValueError("Number of teams must be an even number.")

    # Run the solver
    result, runtime = STS_SAT(args.n_teams, args.time_limit, args.optimality, args.seed, args.verbose)

    
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
        filepath=res_path,
        optimality=args.optimality
    )
