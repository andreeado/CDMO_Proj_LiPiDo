from z3 import *


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

def calculate_imbalance(n, fixed_schedule, swap_model, swap):
    T1, T2 = build_inverse_tables(n)
    
    total_imbalance = 0
    team_imbalances = []
    
    for t in range(1, n + 1):
        home_games = 0
        
        for (w, p), m in fixed_schedule.items():
            if swap_model:
                swap_val = is_true(swap_model.evaluate(swap[m]))
            else:
                swap_val = False
                
            # Team t is home if: (t is T1 and not swapped) OR (t is T2 and swapped)
            if (T1[m] == t and not swap_val) or (T2[m] == t and swap_val):
                home_games += 1
        
        away_games = (n - 1) - home_games
        imbalance = abs(2 * home_games - (n - 1)) - 1
        if imbalance < 0:
            imbalance = 0
        total_imbalance += imbalance
        team_imbalances.append(imbalance)
    
    return total_imbalance, team_imbalances

def circle_method_fixed_schedule(n):
    weeks = n - 1
    periods = n // 2
    schedule = {}

    teams_list = list(range(1, n))
    
    for w in range(weeks):
        # Match for the fixed team n
        team_n_opponent = teams_list[w]
        i, j = min(team_n_opponent, n), max(team_n_opponent, n)
        schedule[(w, 0)] = match_ID(i, j, n)

        # Rotational matches
        for p in range(1, periods):
            t1_idx = (w + p) % (weeks)
            t2_idx = (w - p + weeks) % (weeks)
            
            t1 = teams_list[t1_idx]
            t2 = teams_list[t2_idx]

            i, j = min(t1, t2), max(t1, t2)
            schedule[(w, p)] = match_ID(i, j, n)
    
    return schedule

def print_schedule_optimized(n, fixed_schedule, swap_model, swap):
    weeks = n - 1
    periods = n // 2
    T1, T2 = build_inverse_tables(n)

    schedule = [["" for _ in range(weeks)] for _ in range(periods)]
    
    for (w, p), m in fixed_schedule.items():
        if swap_model:
            swap_val = is_true(swap_model.evaluate(swap[m]))
        else:
            swap_val = False
            
        if not swap_val:
            home, away = T1[m], T2[m]
        else:
            home, away = T2[m], T1[m]
            
        schedule[p][w] = f"{home} vs {away}"

    header_labels = [f"Week {i+1}" for i in range(weeks)]
    cell_width = max(
        8,
        max((len(s) for row in schedule for s in row), default=0),
        max((len(h) for h in header_labels), default=0)
    ) + 3
    left_width = max(10, len(f"Period {periods}") + 2)

    header = " " * left_width + "".join(h.ljust(cell_width) for h in header_labels)
    print(header)

    for p in range(periods):
        left = f"Period {p+1}".ljust(left_width)
        row = left + "".join(schedule[p][w].ljust(cell_width) for w in range(weeks))
        print(row)