import subprocess
import re
import json
import argparse
import time
from math import floor
import os

# Save solution to file
if os.path.exists("/app/res"):
    # docker
    MINIZINC_PATH = "minizinc"
else:
    # local
    MINIZINC_PATH = "C:\\Users\\xPica\\AppData\\Local\\Programs\\MiniZinc\\minizinc.exe"

# Save solution to file
if os.path.exists("/app/res"):
    # docker
    MODEL_FILE = "/app/source/CP/model.mzn"
else:
    # local
    MODEL_FILE = "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\model.mzn"

TIME_LIMIT_MS = 300000  # 5 minutes

def run_minizinc(n, solver, seed=777, time_limit=TIME_LIMIT_MS):
    cmd = [
        MINIZINC_PATH,
        MODEL_FILE,
        '-D', f'n={n}',
        '--solver', solver,
        '--time-limit', str(time_limit),
        '--random-seed', str(seed),
        '--statistics'
    ]
    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=time_limit/1000 + 30)
    wall_time = time.time() - start_time
    output_text = result.stdout + "\n" + result.stderr

    # Extract solve time
    time_match = re.search(r'%%%mzn-stat:\s*solveTime\s*=\s*(\d+\.\d+)', output_text)
    solver_time = float(time_match.group(1)) if time_match else wall_time

    # If MiniZinc timed out, set time to 300
    timeout_flag = '=====UNKNOWN=====' in output_text
    if timeout_flag:
        solver_time = 300

    # Parse objective value
    obj_match = re.search(r'Objective function:\s*(-?\d+)', output_text)
    if obj_match:
        obj = int(obj_match.group(1))
    else:
        obj = None

    # Find the solution block after %%%mzn-stat-end and before Objective function
    sol_match = re.search(r'%%%mzn-stat-end\s*\n(\[[\s\S]*?\])\s*Objective function:', output_text)
    sol = None
    if sol_match:
        sol_str = sol_match.group(1)
        try:
            sol = eval(sol_str.replace('\n', '').replace(' ', ''))
        except Exception as e:
            sol = None

    optimal = '==========' in output_text or 'optimal' in output_text.lower()

    return {
        solver: {
            "time": floor(solver_time),
            "optimal": optimal,
            "obj": obj,
            "sol": sol
        }
    }

def main():
    parser = argparse.ArgumentParser(description='Run MiniZinc model and output JSON.')
    parser.add_argument('n', type=int, help='Number of teams')
    parser.add_argument('solver', type=str, nargs='?', default='gecode', help='MiniZinc solver name')
    parser.add_argument('--seed', type=int, default=1, help='Random seed')
    parser.add_argument('--output', type=str, default=None, help='Output JSON file')
    args = parser.parse_args()

    solver = args.solver if args.solver else 'gecode'
    result = run_minizinc(args.n, solver, args.seed)
    result_data = result
    if os.path.exists("/app/res"):
        # docker
        res_path = f"/app/res/CP/{args.n}.json"
    else:
        # local
        res_path = f"res/CP/{args.n}.json"
    with open(res_path, 'w') as f:
        json.dump(result_data, f, indent=4)
    print(f"Results saved to {res_path}")

if __name__ == "__main__":
    main()