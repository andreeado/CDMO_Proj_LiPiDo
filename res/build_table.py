import json
import os
import pandas as pd
from pathlib import Path
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

def load_mip_results(directory="MIP"):
    """Load all JSON files from the MIP directory."""
    results = {}
    mip_path = Path(__file__).parent / directory
    
    for json_file in sorted(mip_path.glob("*.json")):
        n = int(json_file.stem)
        with open(json_file, 'r') as f:
            results[n] = json.load(f)
    
    return results

def extract_approach_info(approach_data):
    """Extract time, optimal flag, and objective value from approach data."""
    time = approach_data.get('time', None)
    optimal = approach_data.get('optimal', False)
    obj = approach_data.get('obj', None)
    
    return {
        'time': time,
        'optimal': optimal,
        'obj': obj
    }

def build_results_table(results):
    """Build a structured table from results."""
    
    # Define approaches and solvers
    solvers = ['cbc', 'gurobi', 'HiGHS']
    variants = ['f', 'opt', 'f_sb', 'opt_sb']
    
    rows = []
    
    for n in sorted(results.keys()):
        data = results[n]
        
        for solver in solvers:
            for variant in variants:
                key = f"{solver}_{variant}"
                
                if key in data:
                    info = extract_approach_info(data[key])
                    
                    # Determine approach name
                    if variant == 'f':
                        approach = f"{solver.upper()} - Feasibility"
                    elif variant == 'opt':
                        approach = f"{solver.upper()} - Optimization"
                    elif variant == 'f_sb':
                        approach = f"{solver.upper()} - Feasibility + SB"
                    elif variant == 'opt_sb':
                        approach = f"{solver.upper()} - Optimization + SB"
                    
                    rows.append({
                        'n': n,
                        'Solver': solver.upper(),
                        'Approach': approach,
                        'Time (s)': info['time'],
                        'Objective Value': info['obj'] if info['obj'] is not None else '-',
                        'Optimal': info['optimal']
                    })
    
    return pd.DataFrame(rows)

def create_excel_table(df, output_file="MIP_results.xlsx"):
    """Create a formatted Excel table with conditional formatting."""
    
    # Reorganize data for better presentation
    # Create pivot-like structure: rows=n, columns=approaches with time and obj
    
    output_path = Path(__file__).parent / output_file
    
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        # Write simple table
        df.to_excel(writer, sheet_name='Raw Data', index=False)
        
        # Create formatted summary table
        create_summary_sheet(writer, df)
    
    print(f"Excel table created: {output_path}")
    return output_path

def create_summary_sheet(writer, df):
    """Create a formatted summary sheet with better layout."""
    
    # Get unique values
    n_values = sorted(df['n'].unique())
    approaches = df['Approach'].unique()
    
    # Create summary data
    summary_rows = []
    
    for n in n_values:
        n_data = df[df['n'] == n]
        
        for approach in sorted(approaches):
            approach_data = n_data[n_data['Approach'] == approach]
            
            if not approach_data.empty:
                row_data = approach_data.iloc[0]
                summary_rows.append({
                    'n': n,
                    'Approach': approach,
                    'Time to Feasibility (s)': row_data['Time (s)'] if 'Feasibility' in approach else '-',
                    'Time to Optimality (s)': row_data['Time (s)'] if 'Optimization' in approach else '-',
                    'Objective Value': row_data['Objective Value'],
                    'Optimal': row_data['Optimal']
                })
    
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_excel(writer, sheet_name='Summary', index=False)
    
    # Format the summary sheet
    workbook = writer.book
    worksheet = writer.sheets['Summary']
    
    # Set column widths
    worksheet.column_dimensions['A'].width = 8
    worksheet.column_dimensions['B'].width = 35
    worksheet.column_dimensions['C'].width = 25
    worksheet.column_dimensions['D'].width = 25
    worksheet.column_dimensions['E'].width = 20
    worksheet.column_dimensions['F'].width = 12
    
    # Format header
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
    
    # Bold optimal objective values
    for row_idx, row in enumerate(summary_df.itertuples(), start=2):
        # Column E is Objective Value (index 5)
        obj_cell = worksheet.cell(row=row_idx, column=5)
        optimal_cell = worksheet.cell(row=row_idx, column=6)
        
        if row.Optimal:
            obj_cell.font = Font(bold=True)
            optimal_cell.value = "Yes"
        else:
            optimal_cell.value = "No"
        
        # Center alignment for n and optimal columns
        worksheet.cell(row=row_idx, column=1).alignment = Alignment(horizontal='center')
        worksheet.cell(row=row_idx, column=6).alignment = Alignment(horizontal='center')

def main():
    """Main function to build the table."""
    print("Loading MIP results...")
    results = load_mip_results()
    
    print(f"Found results for n = {sorted(results.keys())}")
    
    print("Building results table...")
    df = build_results_table(results)
    
    print("Creating Excel file...")
    output_file = create_excel_table(df)
    
    print(f"\nDone! Results saved to: {output_file}")
    print(f"Total entries: {len(df)}")

if __name__ == "__main__":
    main()
