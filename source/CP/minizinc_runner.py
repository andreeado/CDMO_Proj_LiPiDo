#!/usr/bin/env python3
import subprocess
import re
import pandas as pd
import time
from pathlib import Path
import argparse

def run_minizinc_with_seed(model_file, data_file, solver, seed, time_limit=300000):
    """Run MiniZinc with a specific random seed and extract timing info."""
    
    cmd = [
        MINIZINC_PATH,
        '--solver', solver,
        '--time-limit', str(time_limit),
        '--random-seed', str(seed),
        '--statistics',
        model_file
    ]
    
    if data_file:
        cmd.append(data_file)
    
    # Debug: print the command being run
    print(f"\n    Command: {' '.join(cmd)}")
    
    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=time_limit/1000 + 30)
        wall_time = time.time() - start_time
        
        # Debug: print return code and first bit of output
        print(f"    Return code: {result.returncode}")
        if result.stdout:
            print(f"    Stdout (first 100 chars): {result.stdout[:100]}")
        if result.stderr:
            print(f"    Stderr (first 200 chars): {result.stderr[:200]}")
        
        # Extract solver time from statistics output
        solver_time = None
        output_text = result.stdout + "\n" + result.stderr  # Combine both streams

        # Look for time in statistics (MiniZinc outputs lines like "%%%mzn-stat: solveTime=0.252511")
        time_match = re.search(r'%%%mzn-stat:\s*solveTime\s*=\s*(\d+\.\d+)', output_text)
        if time_match:
            solver_time = float(time_match.group(1))
        else:
            # Fallback to other patterns if needed
            time_match = re.search(r'time:\s*(\d+\.?\d*)', output_text)
            if time_match:
                solver_time = float(time_match.group(1))
            else:
                time_match = re.search(r'solving:\s*(\d+\.?\d*)', output_text)
                if time_match:
                    solver_time = float(time_match.group(1)) / 1000  # Convert ms to seconds
        
        # Check if solution was found
        solution_found = '=' in result.stdout and '----------' in result.stdout
        optimal = '==========' in result.stdout
        
        return {
            'solver_time_s': solver_time,
            'wall_time_s': wall_time,
            'solution_found': solution_found,
            'optimal': optimal,
            'return_code': result.returncode
        }
        
    except subprocess.TimeoutExpired:
        print("    TIMEOUT")
        return {
            'solver_time_s': time_limit/1000,  # Use time limit as time for timeouts
            'wall_time_s': time_limit/1000,
            'solution_found': False,
            'optimal': False,
            'return_code': 'TIMEOUT'
        }
    except Exception as e:
        print(f"    EXCEPTION: {e}")
        return {
            'solver_time_s': None,
            'wall_time_s': None,
            'solution_found': False,
            'optimal': False,
            'return_code': f'ERROR: {e}'
        }

# ============================================================================
# CONFIGURATION SECTION - Modify these variables as needed
# ============================================================================

# MiniZinc executable path - modify this to point to your MiniZinc installation
MINIZINC_PATH = "C:\\Users\\xPica\\AppData\\Local\\Programs\\MiniZinc\\minizinc.exe"  # Change to full path like "C:\\Program Files\\MiniZinc\\bin\\minizinc.exe"

# Data file to use (set to None if no data file needed)
DATA_FILE = "C:\\Users\\xPica\\Documents\\CDMO_Proj_LiPiDo\\source\\CP\\data.dzn"

# Solver to use
SOLVER = "gecode"

# Random seeds to test
SEEDS = [2,5,7,9,15]  # Seeds from 1 to 15

# Time limit in milliseconds
TIME_LIMIT_MS = 300000  # 5 minutes

# Output Excel file name
OUTPUT_FILE = "model_comparison_BB.xlsx"

# ============================================================================
# END CONFIGURATION SECTION
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='Compare multiple MiniZinc models with different seeds')
    parser.add_argument('models', nargs='+', help='MiniZinc model files (.mzn)')
    
    args = parser.parse_args()
    
    # Use configuration variables instead of command line args
    data_file = DATA_FILE
    solver = SOLVER
    seeds = SEEDS
    time_limit = TIME_LIMIT_MS
    output_file = OUTPUT_FILE
    
    print(f"Comparing {len(args.models)} models with {len(seeds)} seeds each")
    print(f"Models: {[Path(m).stem for m in args.models]}")
    print(f"Data: {data_file}")
    print(f"Solver: {solver}")
    print(f"Seeds: {seeds}")
    print(f"Time limit: {time_limit}ms")
    print(f"Output: {output_file}")
    print("-" * 60)
    
    # Initialize results dictionary
    all_results = {'seed': seeds}
    
    # For each model, run all seeds
    for model_file in args.models:
        model_name = Path(model_file).stem
        print(f"\nRunning model: {model_name}")
        print("-" * 40)
        
        # Initialize columns for this model
        all_results[f'{model_name}_time_s'] = []
        all_results[f'{model_name}_solved'] = []
        all_results[f'{model_name}_optimal'] = []
        
        for i, seed in enumerate(seeds, 1):
            print(f"  Seed {seed} ({i}/{len(seeds)})... ", end='', flush=True)
            
            result = run_minizinc_with_seed(
                model_file, 
                data_file, 
                solver, 
                seed, 
                time_limit
            )
            
            # Store results
            all_results[f'{model_name}_time_s'].append(result['solver_time_s'])
            all_results[f'{model_name}_solved'].append(result['solution_found'])
            all_results[f'{model_name}_optimal'].append(result['optimal'])
            
            # Print progress
            if result['solution_found']:
                time_str = f"{result['solver_time_s']:.3f}s" if result['solver_time_s'] else "N/A"
                optimal_str = " (optimal)" if result['optimal'] else ""
                print(f"✓ {time_str}{optimal_str}")
            else:
                print("✗ failed/timeout")
    
    # Create DataFrame
    df = pd.DataFrame(all_results)
    
    # Calculate summary statistics for each model
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    
    summary_stats = []
    
    for model_file in args.models:
        model_name = Path(model_file).stem
        
        # Get data for this model
        time_col = f'{model_name}_time_s'
        solved_col = f'{model_name}_solved'
        optimal_col = f'{model_name}_optimal'
        
        solved_mask = df[solved_col] == True
        solved_times = df.loc[solved_mask, time_col]
        
        stats = {
            'Model': model_name,
            'Total_Runs': len(df),
            'Solutions_Found': solved_mask.sum(),
            'Optimal_Solutions': (df[optimal_col] == True).sum(),
            'Success_Rate_%': (solved_mask.sum() / len(df)) * 100,
            'Avg_Time_s': solved_times.mean() if len(solved_times) > 0 else None,
            'Min_Time_s': solved_times.min() if len(solved_times) > 0 else None,
            'Max_Time_s': solved_times.max() if len(solved_times) > 0 else None,
            'Std_Dev_s': solved_times.std() if len(solved_times) > 0 else None
        }
        
        summary_stats.append(stats)
        
        print(f"{model_name}:")
        print(f"  Solutions: {stats['Solutions_Found']}/{stats['Total_Runs']} ({stats['Success_Rate_%']:.1f}%)")
        print(f"  Optimal: {stats['Optimal_Solutions']}")
        if stats['Avg_Time_s'] is not None:
            print(f"  Avg time: {stats['Avg_Time_s']:.3f}s")
            print(f"  Time range: {stats['Min_Time_s']:.3f}s - {stats['Max_Time_s']:.3f}s")
        print()
    
    summary_df = pd.DataFrame(summary_stats)
    
    # Find best performing model
    if len(summary_stats) > 0:
        # Sort by success rate, then by average time
        summary_df_sorted = summary_df.sort_values(['Success_Rate_%', 'Avg_Time_s'], 
                                                  ascending=[False, True])
        best_model = summary_df_sorted.iloc[0]['Model']
        print(f"Best performing model: {best_model}")
    
    # Save to Excel with multiple sheets
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        # Main results - each model as columns
        df.to_excel(writer, sheet_name='Detailed_Results', index=False)
        
        # Summary statistics
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        # Create a times-only comparison sheet
        time_columns = ['seed'] + [col for col in df.columns if col.endswith('_time_s')]
        times_df = df[time_columns]
        times_df.to_excel(writer, sheet_name='Times_Comparison', index=False)
        
        # Create a success rate comparison
        success_columns = ['seed'] + [col for col in df.columns if col.endswith('_solved')]
        success_df = df[success_columns]
        success_df.to_excel(writer, sheet_name='Success_Comparison', index=False)
    
    print(f"Results saved to {output_file}")
    print("\nSheets created:")
    print("  - Detailed_Results: All data with model results as columns")
    print("  - Summary: Statistics summary for each model")
    print("  - Times_Comparison: Just the timing data")
    print("  - Success_Comparison: Just the success/failure data")

if __name__ == "__main__":
    main()