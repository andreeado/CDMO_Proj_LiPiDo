import subprocess
import re
import json
import argparse
import time
from math import floor
import os
import numpy as np

# Detect MiniZinc path
if os.path.exists("/app/res"):
    MINIZINC_PATH = "minizinc"
    MATCH_MODEL_FILE = ["/app/source/CP/global.mzn",
                        "/app/source/CP/count.mzn"]
    SWAP_MODEL_FILE = "/app/source/CP/OPT.mzn"
else:
    MINIZINC_PATH = "C:\\Users\\xPica\\AppData\\Local\\Programs\\MiniZinc\\minizinc.exe"
    MATCH_MODEL_FILE = [
                        "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\global.mzn",
                        "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\count_.mzn",
                        #"C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\naive_noIC.mzn",
                        #"C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\globale_noIC.mzn"
                        ]

    SWAP_MODEL_FILE  = "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\OPT.mzn"

TIME_LIMIT_MS = 300000  # 5 min


# ---------------------------------------------------------
#  Run a MiniZinc model and extract: array solution, time, objective
# ---------------------------------------------------------
def run_minizinc(model_file, n, solver, seed, time_limit=TIME_LIMIT_MS, swap=True):

    cmd = [
        MINIZINC_PATH,
        model_file,
        '-D', f'n={n}',
        '--solver', solver,
        '--time-limit', str(time_limit),
        '--random-seed', str(seed),
        '--statistics'
    ]

    start_time = time.time()
    result = subprocess.run(
        cmd, capture_output=True, text=True,
        timeout=time_limit / 1000 + 30
    )
    wall_time = time.time() - start_time
    output_text = result.stdout + "\n" + result.stderr

    # -------------------------
    #   SOLVER TIME
    # -------------------------
    time_match = re.search(r'%%%mzn-stat:\s*solveTime\s*=\s*(\d+\.\d+)', output_text)
    solver_time = float(time_match.group(1)) if time_match else wall_time
    if "=====UNKNOWN=====" in output_text:
        solver_time = 300  # timeout fallback

    # -------------------------
    #   OBJECTIVE (swap mode only)
    # -------------------------
    if swap:
        obj_match = re.search(r'Objective function:\s*(-?\d+)', output_text)
        obj = int(obj_match.group(1)) if obj_match else None
    else:
        obj = None  # matchvar has no objective

    # -------------------------
    #   SOLUTION PARSING
    # -------------------------

    if swap:
        sol = next(
            (eval(m.group(0)
                  .replace("true", "1")
                  .replace("false", "0"))
             for m in [re.search(r'\[[^\]]*\]', output_text, re.S)]
             if m),
            None
        )

    else:
        # First capture everything between %%%mzn-stat-end and ----------
        pattern = r'%%%mzn-stat-end\s*(.*?)\s*----------'

        match = re.search(pattern, output_text, re.DOTALL)
        if match:
            # Extract all arrays from the captured content
            arrays_text = match.group(1)
            arrays = re.findall(r'\[[^\]]+\]', arrays_text)
            
            x = eval(re.sub(r'\s+', '', arrays[0]))
            y = eval(re.sub(r'\s+', '', arrays[1]))
            match_vars = eval(re.sub(r'\s+', '', arrays[2]))
            sol = (x, y, match_vars)
        else:
            sol = []


    optimal = False
    if swap:
        optimal = '==========' in output_text
    else:
        timeout_flag = '=====UNKNOWN=====' in output_text
        infeasible_flag = '=====UNSATISFIABLE=====' in output_text or 'infeasible' in output_text.lower()

        if timeout_flag:
            # TIMEOUT SOLUTION
            sol = []
            obj = None
            solver_time = 300  # timeout fallback
        if infeasible_flag:
            # INFEASIBLE SOLUTION
            sol = []
            obj = None
            optimal = True

    return {
        "time": floor(solver_time),
        "optimal": optimal,
        "obj": obj,
        "sol": sol,
        "raw": output_text
    }



# ---------------------------------------------------------
#  Build schedule from solutions
# ---------------------------------------------------------


def build_schedule(x, y, match_vars, swap):
    a= len(x)
    n=int((1+np.sqrt(1+8*a))//2)
    nPeriods = n//2
    nWeeks = n-1

    schedule = []
    for p in range(nPeriods):
        row = []
        for w in range(nWeeks):
            ind = p * nWeeks + w
            mindex = match_vars[ind]
            if swap[mindex-1] == 0:
                home = x[ind]
                away = y[ind]
            else:
                home = y[ind]
                away = x[ind]
            row.append([home, away])
        schedule.append(row)

    return schedule


# ---------------------------------------------------------
#  Pretty MiniZinc-like output
# ---------------------------------------------------------

def pretty_print(schedule, objective):
    out = "[\n"
    for p, row in enumerate(schedule, start=1):
        out += "  ["
        out += ", ".join(f" [{h}, {a}]" for h, a in row)
        out += "]"
        out += ",\n" if p < len(schedule) else "\n"
    out += "]\n"
    out += f"Objective function: {objective}\n"
    return out

# ---------------------------------------------------------
#  Main
# ---------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Run two MiniZinc models and combine results.")
    parser.add_argument("n", type=int, help="Number of teams")
    parser.add_argument("solver", type=str, nargs="?", default="gecode")
    parser.add_argument("--seed", type=int, default=55)
    parser.add_argument("--no-opt", action="store_true", default=False, help="Do not optimize objective function")

    args = parser.parse_args()
    
    
    if os.path.exists("/app/res"):
        output_file = f"/app/res/CP/{args.n}.json"
    else:
        output_file = f"C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\res\\CP\\{args.n}.json"

    # Run MiniZinc models

    swap_result = {
    "time": 0,
    "optimal": True,
    "obj": None,
    "sol": [0] * (args.n//2 * (args.n - 1))
    }

    if not args.no_opt:
        swap_result = run_minizinc(SWAP_MODEL_FILE,  args.n, args.solver, args.seed, swap=True)
        if swap_result ["sol"] is None:
            swap_result["obj"] = None
            swap_result["optimal"] = False
            swap_result["sol"] = [0] * (args.n//2 * (args.n - 1))

    output_payload = {}

    for model in MATCH_MODEL_FILE:

        match_result = run_minizinc(model,  args.n, args.solver, args.seed, swap=False)
        model_name = os.path.splitext(os.path.basename(model))[0]

        if match_result["sol"] == []:
            schedule = []
            swap_result["obj"] = None
        else:
            x,y,match_vars =match_result["sol"]
            schedule = build_schedule(
                x=x,
                y=y,
                match_vars=match_vars,
                swap=swap_result["sol"]
            )

        time = int(match_result["time"] + swap_result["time"])
        if time > TIME_LIMIT_MS / 1000:
            time = 300  # timeout fallback
            swap_result["optimal"] = False

        final_data = {
            "time": time,
            "optimal": swap_result["optimal"] or match_result["optimal"],
            "obj": swap_result["obj"],
            "sol": schedule,
        }

        output_payload[args.solver+"_"+model_name] = final_data

    # Save JSON nested under the solver key

    with open(output_file, "w") as f:
        json.dump(output_payload, f, indent=4)
    print(f"Saved {output_file}")

if __name__ == "__main__":
    main()