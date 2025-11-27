import json
import os
from pulp import value

def match_ID(i,j,n):
    return ((i-1)*n+j)-(i*(i+1))//2


def build_inverse_tables(n):
    M = n * (n - 1) // 2
    T1 = [0] * (M + 1)
    T2 = [0] * (M + 1)

    for i in range(1, n):
        for j in range(i + 1, n + 1):
            m = match_ID(i, j, n)
            T1[m] = i
            T2[m] = j

    return T1, T2

def extract_schedule_from_matches(match_period, T1, T2, data, circle_schedule):
    """
    Extract schedule from match_period variables
    Returns schedule in format: [period][week] = [team1, team2]
    where team numbers are 1-indexed
    """
    n_teams = data['n_teams']
    n_weeks = data['n_weeks']
    n_periods = data['n_periods']
    M = n_teams * (n_teams - 1) // 2
    
    # Initialize schedule structure: schedule[period][week] = [home, away]
    schedule = []
    for p in range(n_periods):
        period_schedule = []
        for w in range(n_weeks):
            period_schedule.append([])
        schedule.append(period_schedule)
    
    # Create reverse mapping: match_id -> week
    match_to_week = {}
    for week, match_list in circle_schedule.items():
        for match_id in match_list:
            match_to_week[match_id] = week
    
    # Extract assignments from decision variables
    for m in range(1, M + 1):
        for p in range(n_periods):
            if match_period[m, p].varValue and match_period[m, p].varValue > 0.5:
                # Find which week this match belongs to
                if m in match_to_week:
                    w = match_to_week[m]
                    # Get teams for this match (already 1-indexed from T1, T2)
                    team1 = T1[m]
                    team2 = T2[m]
                    # Store as [home, away] - using team1 as home by default
                    schedule[p][w] = [team1, team2]
                break
    
    return schedule

def apply_swaps(schedule, swap_vars, data):
    """
    Apply home/away swaps to the schedule based on swap variable values.
    
    Returns:
        Updated schedule with swaps applied
    """
    n_periods = data['n_periods']
    n_weeks = data['n_weeks']
    
    # Create a copy of the schedule to modify
    new_schedule = []
    for p in range(n_periods):
        period_schedule = []
        for w in range(n_weeks):
            if schedule[p][w]:
                period_schedule.append(schedule[p][w][:])  # Copy the match
            else:
                period_schedule.append([])
        new_schedule.append(period_schedule)
    
    # Apply swaps
    for (p, w), swap_var in swap_vars.items():
        if swap_var.varValue and swap_var.varValue > 0.5:  # Swap is active
            if new_schedule[p][w]:
                # Swap home and away teams
                home, away = new_schedule[p][w]
                new_schedule[p][w] = [away, home]
    
    return new_schedule

def create_solution_data(solver_name, schedule, obj, optimal, solve_time):
    """
    Create solution data in the format expected by save_solution
    """
    return {
        solver_name: {
            "time": solve_time,
            "optimal": optimal,
            "obj": obj,
            "sol": schedule
        }
    }


def create_data(n_teams):
    n_weeks = n_teams - 1
    n_periods = n_teams // 2
    data = {
            'n_teams': n_teams,
            'n_weeks': n_weeks,
            'n_periods': n_periods,
            'teams': list(range(n_teams)),
            'weeks': list(range(n_weeks)),
            'periods': list(range(n_periods))
        }
    return data


def save_solution(solution_data, filepath):
    """
    Save solution to JSON file in the required format
    """
    # Load existing data if file exists
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = {}
    else:
        data = {}

    data.update(solution_data)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Solution saved to {filepath}")


def display_schedule(schedule, n_teams, n_weeks, n_periods):
    """
    Display schedule as a table with periods as rows and weeks as columns
    schedule format: List[List[List[int]]] - [period][week][matches]
    """
    if not schedule:
        print("No feasible solution to display")
        return

    print(f"TOURNAMENT SCHEDULE - {n_teams} Teams")

    # Header
    header = f"{'Period':<12}"
    for w in range(n_weeks):
        header += f"{'Week' + str(w+1):<15}"
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    # Schedule rows
    for period in range(n_periods):
        row = f"{period+1:<12}"
        for week in range(n_weeks):
            match = schedule[period][week]
            if match and len(match) == 2:
                # match is directly [team1, team2]
                match_str = f"{match[0]} vs {match[1]}"
            else:
                match_str = "---"
            row += f"{match_str:<15}"
        print(row)

    print(f"\n{'='*60}")


def analyze_home_away_balance(schedule, n_teams, n_weeks, n_periods):
    """
    Analyze and display home-away balance statistics
    """
    home_count = [0] * n_teams
    away_count = [0] * n_teams
    
    # Count home and away games for each team
    for period in range(n_periods):
        for week in range(n_weeks):
            match = schedule[period][week]
            if match and len(match) == 2:
                home_team = match[0] - 1  # Convert to 0-indexed
                away_team = match[1] - 1  # Convert to 0-indexed
                home_count[home_team] += 1
                away_count[away_team] += 1
    
    print("\nHOME-AWAY BALANCE ANALYSIS:")
    print("-" * 50)
    print(f"{'Team':<6} {'Home':<6} {'Away':<6} {'Balance':<8}")
    print("-" * 50)
    
    total_imbalance = 0
    for team in range(n_teams):
        balance = abs(home_count[team] - away_count[team])
        total_games = home_count[team] + away_count[team]
        total_imbalance += balance
        
        print(f"{team+1:<6} {home_count[team]:<6} {away_count[team]:<6} {balance:<8}")
    
    print("-" * 50)
    print(f"Total imbalance: {total_imbalance}")
    print(f"Average imbalance per team: {total_imbalance / n_teams:.2f}")
    
    return total_imbalance
