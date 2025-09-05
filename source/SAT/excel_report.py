import pandas as pd
import json
import os
import numpy as np

def generate_excel_report(base_dir):
    """
    Generates an Excel report from SAT solver JSON results.
    """
    all_results = {}

    # Iterate through each team count (n) from 2 to 22 (inclusive), with a step of 2.
    for n in range(2, 23, 2):
        n_dir = os.path.join(base_dir, str(n))

        if not os.path.isdir(n_dir):
            print(f"Directory {n_dir} not found. Skipping n={n}.")
            continue

        times = []
        objs = []

        # Iterate through each run (1 to 20)
        for i in range(1, 21):
            file_path = os.path.join(n_dir, f"run_{i}.json")

            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)

                        # Extract time and objective
                        sat_data = data.get("z3_sat_solver", {})
                        time = sat_data.get("time")
                        obj = sat_data.get("obj")

                        # Handle cases where the solver did not find a solution (obj is null)
                        if obj is None:
                            objs.append(np.nan)
                        else:
                            objs.append(obj)

                        if time is not None:
                            times.append(time)
                        else:
                            times.append(np.nan)

                except json.JSONDecodeError:
                    print(f"Error decoding JSON from file: {file_path}")
                    times.append(np.nan)
                    objs.append(np.nan)
            else:
                # If a run file doesn't exist, append a placeholder.
                times.append(np.nan)
                objs.append(np.nan)

        all_results[f"n={n}_time"] = times
        all_results[f"n={n}_obj"] = objs

    # Create DataFrames from the results
    df_time = pd.DataFrame({k: v for k, v in all_results.items() if "_time" in k})
    df_obj = pd.DataFrame({k: v for k, v in all_results.items() if "_obj" in k})

    # Check if dataframes are empty before proceeding
    if df_time.empty or df_obj.empty:
        print("The DataFrames for times or objectives are empty. Cannot create the report.")
        return

    # Calculate means for times less than 300 and append them to the DataFrame
    mean_time = df_time[df_time < 300].mean(axis=0)
    df_time.loc['Mean'] = mean_time

    # Calculate the percentage of solutions found (time < 300)
    # The number of experiments is the number of rows before adding 'Mean'
    total_experiments = len(df_time) - 1
    solutions_found = (df_time.iloc[:total_experiments] < 300).sum(axis=0)
    percentage_found = (solutions_found / total_experiments) * 100
    df_time.loc['Success Rate (%)'] = percentage_found

    # For the objective values, we just calculate the standard mean
    mean_obj = df_obj.mean(axis=0)
    df_obj.loc['Mean'] = mean_obj.values

    # Rename the columns to be more readable
    df_time.columns = [col.replace("_time", "") for col in df_time.columns]
    df_obj.columns = [col.replace("_obj", "") for col in df_obj.columns]

    # Write the DataFrames to an Excel file with multiple sheets
    # The file will be saved in the parent folder of 'base_dir'
    output_file = os.path.join(base_dir, "..", "SAT_results_modified.xlsx")
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_time.to_excel(writer, sheet_name='Execution Times')
        df_obj.to_excel(writer, sheet_name='Objective Values')

    print(f"Excel report saved to: {output_file}")


if __name__ == "__main__":
    # Ask the user to input the path to the base directory
    base_directory = input("Enter the path to the base directory containing the results (with subdirectories 2, 4, ...): ")
    
    # Check if the entered path is a valid directory
    if os.path.isdir(base_directory):
        generate_excel_report(base_directory)
    else:
        print("Error: The entered path is not a valid directory. Please try again.")