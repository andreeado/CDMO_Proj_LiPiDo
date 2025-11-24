import subprocess
import re
import json
import argparse
import time
from math import floor
import os

# Detect MiniZinc path
if os.path.exists("/app/res"):
    MINIZINC_PATH = "minizinc"
    MATCH_MODEL_FILE = "/app/source/CP/match_model.mzn"
    SWAP_MODEL_FILE = "/app/source/CP/swap_model.mzn"
else:
    MINIZINC_PATH = "C:\\Users\\xPica\\AppData\\Local\\Programs\\MiniZinc\\minizinc.exe"
    MATCH_MODEL_FILE = "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\ZZZ\\def.mzn"
    SWAP_MODEL_FILE  = "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\ZZZ\\OPT.mzn"

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
                  .replace("true", "True")
                  .replace("false", "False"))
             for m in [re.search(r'\[[^\]]*\]', output_text, re.S)]
             if m),
            None
        )

    else:
        # Pattern to capture two arrays
        pattern = r'%%%mzn-stat-end\s*(\[[^\]]+\])\s*(\[[^\]]+\])'

        match = re.search(pattern, output_text, re.DOTALL)
        if match:
            x = eval(re.sub(r'\s+', '', match.group(1)))
            y = eval(re.sub(r'\s+', '', match.group(2)))
            match_vars = eval(re.sub(r'\s+', '', match.group(3)))
            sol = x,y,match_vars
        else:
            sol = None


    # -------------------------
    #   OPTIMAL FLAG
    # -------------------------
    optimal = ("==========" in output_text) or ("optimal" in output_text.lower())

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
    nPeriods = x.shape[0]
    nWeeks = x.shape[1]

    schedule = []
    for p in range(nPeriods):
        row = []
        for w in range(nWeeks):
            mindex = match_vars[w,p]
            if swap[mindex] == 0:
                home = x[w,p]
                away = y[w,p]
            else:
                home = y[w,p]
                away = x[w,p]
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

    args = parser.parse_args()

    # Run MiniZinc models

    match_result = run_minizinc(MATCH_MODEL_FILE, args.n, args.solver, args.seed, swap=False)

    print(match_result)

    swap_result = run_minizinc(SWAP_MODEL_FILE,  args.n, args.solver, args.seed, swap=True)

    print(swap_result)



    if match_result["sol"] is None:
        raise RuntimeError("Match model returned no solution.")
    if swap_result["sol"] is None:
        raise RuntimeError("Swap model returned no solution.")

    x,y,match_vars =match_result["sol"]

    # Combine
    schedule = build_schedule(
        x=x,
        y=y,
        match_vars=match_vars,
        swap=swap_result["sol"]
    )

    final_data = {
        "time": match_result["time"] + swap_result["time"],
        "optimal": swap_result["optimal"],
        "obj": swap_result["obj"],
        "result": schedule,
  }

    # Save JSON
    with open(args.output, "w") as f:
        json.dump(final_data, f, indent=4)
    print(f"Saved {args.output}")

if __name__ == "__main__":
    main()
