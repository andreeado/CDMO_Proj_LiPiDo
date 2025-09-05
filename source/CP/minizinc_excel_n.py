#!/usr/bin/env python3
import subprocess
import pandas as pd
import time
from pathlib import Path
from statistics import mean, stdev

def run_minizinc(n, solver, seed=1, time_limit=300000, model_file=None):
    """Directly run MiniZinc and parse output, as in minizinc_runner.py."""
    cmd = [
        MINIZINC_PATH,
        model_file,
        '-D', f'n={n}',
        '--solver', solver,
        '--time-limit', str(time_limit),
        '--random-seed', str(seed),
        '--statistics'
    ]
    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=time_limit/1000 + 30)
        wall_time = time.time() - start_time
        output_text = result.stdout + "\n" + result.stderr

        # Extract solve time
        import re
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
            except Exception:
                sol = None

        optimal = '==========' in output_text or 'optimal' in output_text.lower()

        feasible = obj is not None or sol is not None

        return {
            'n': n,
            'solver': solver,
            'seed': seed,
            'time': int(solver_time) if solver_time is not None else None,
            'optimal': optimal,
            'obj': obj,
            'sol': sol,
            'feasible': feasible
        }
    except Exception as e:
        print(f"Error running MiniZinc: {e}")
        return {
            'n': n,
            'solver': solver,
            'seed': seed,
            'time': None,
            'optimal': False,
            'obj': None,
            'sol': None,
            'feasible': False
        }

# ============================================================================
# CONFIGURATION SECTION - Modify these variables as needed
# ============================================================================

# MiniZinc executable path - modify this to point to your MiniZinc installation
MINIZINC_PATH = "C:\\Users\\xPica\\AppData\\Local\\Programs\\MiniZinc\\minizinc.exe" 

# Data file to use (set to None if no data file needed)
DATA_FILE = "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\data.dzn"

# Base directory for models
MODEL_BASE_DIR = "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP"

SOLVERS = ["gecode"]
NS = range(6, 22, 2)
SEEDS = range(0, 100, 11)
TIME_LIMIT_MS = 300000
OUTPUT_FILE = "model_comparison_X.xlsx"
MODELS = [
    "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\O.mzn",
    "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\OCP.mzn",
    "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\noSB.mzn",
    "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\noIMP.mzn",
]

# ============================================================================
# END CONFIGURATION SECTION
# ============================================================================

def main():
    results = []
    for model_file in MODELS:
        model_name = Path(model_file).stem
        for n in NS:
            for solver in SOLVERS:
                for seed in SEEDS:
                    print(f"Running model={model_name}, n={n}, solver={solver}, seed={seed}")
                    res = run_minizinc(n, solver, seed, TIME_LIMIT_MS, model_file=model_file)
                    res['model'] = model_name
                    results.append(res)

    df = pd.DataFrame(results)

    # Save detailed results
    with pd.ExcelWriter(OUTPUT_FILE, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Detailed_Results', index=False)

        summary = df.groupby(['n', 'solver', 'model']).agg(
            optimality_rate=('optimal', 'mean'),
            feasibility_rate=('feasible', 'mean'),
            mean_time=('time', 'mean'),
            stdev_time=('time', 'std')
        ).reset_index()

        # Pivot so each model's stats are flanked horizontally in the same sheet
        summary_pivot = summary.pivot_table(
            index=['n', 'solver'],
            columns='model',
            values=['optimality_rate', 'feasibility_rate', 'mean_time', 'stdev_time']
        )
        # Flatten columns in the desired order
        ordered_stats = ['optimality_rate', 'feasibility_rate', 'mean_time', 'stdev_time']
        summary_pivot = summary_pivot.reindex(columns=[(stat, model) for model in summary['model'].unique() for stat in ordered_stats])
        summary_pivot.columns = [f'{model}_{stat}' for stat, model in summary_pivot.columns]
        summary_pivot = summary_pivot.reset_index()
        summary_pivot.to_excel(writer, sheet_name='Summary_by_model_n_solver', index=False)

    print(f"Results saved to {OUTPUT_FILE}")
    print("Sheets created:")
    print("  - Detailed_Results: All runs")
    print("  - Summary_by_model_n_solver: Grouped statistics for each model, n and solver")

if __name__ == "__main__":
    main()