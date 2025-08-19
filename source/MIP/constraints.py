import pyomo.environ as pyo
import logging


logger = logging.getLogger(__name__)


def play_once_rule(model, i, j):
    """
    Each pair of teams (i, j) plays exactly once in the entire schedule.
    """
    if i < j:
        # the sum of matches over all weeks and periods must be exactly 1
        return sum(model.x[i,j,w,p] + model.x[j,i,w,p] 
                          for w in model.Weeks 
                          for p in model.Periods) == 1
    else:
        # to avoid duplicate constraints for i >= j
        return pyo.Constraint.Skip
    
def once_per_week_rule(model, i, w):
    """
    Each team plays exactly once per week (home or away)
    """
    return sum(model.x[i,j,w,p] + model.x[j,i,w,p] 
               for j in model.Teams if j!=i
               for p in model.Periods) == 1

def one_game_per_period_rule(model, w, p):
    """
    Exactly one game (two teams) per period.
    """
    return sum(model.x[i,j,w,p] 
               for i in model.Teams
               for j in model.Teams if i != j) == 1

def max_twice_per_period_rule(model, i, p):
    """
    Each team plays at most twice in the same period over the entire tournament.
    """
    return sum(model.x[i,j,w,p] + model.x[j,i,w,p] 
               for j in model.Teams if j != i
               for w in model.Weeks) <= 2

def no_self_play_rule(model, i, w, p):
    """
    A team cannot play against itself.
    """
    return model.x[i,i,w,p] == 0

def fix_first_week(model, n_teams):
    """
    Fix the entire first week to break symmetries
    """
    n_periods = len(model.Periods)

    # Create pairs: (0,1), (2,3), (4,5), ...
    for p in range(n_periods):
        home_team = 2 * p
        away_team = 2 * p + 1
        
        if away_team < n_teams:
            # Fix this matchup in week 0, period p
            constraint_name = f"fix_week0_period{p}"
            model.add_component(
                constraint_name,
                pyo.Constraint(expr=model.x[home_team, away_team, 0, p] == 1)
            )
            logger.debug(f"Fixed game: Team {home_team} vs Team {away_team} in week 0, period {p}")

def fix_team_order(model, n_teams):
    """
    Fix the order of team 0's opponents to break rotational symmetry.
    Team 0 plays teams 1, 2, ..., n-1 in weeks 0, 1, ..., n-2 respectively.
    """

    for w in range(min(3, n_teams - 1)):  # Fix first 3 weeks only
        opponent = w + 1
        if opponent < n_teams:
            # Team 0 must play against team (w+1) in week w
            constraint_name = f"team0_order_week{w}"
            model.add_component(
                constraint_name,
                pyo.Constraint(
                    expr=sum(model.x[0,opponent,w,p] + model.x[opponent,0,w,p] 
                            for p in model.Periods) == 1
                )
            )


def add_adaptive_symmetry_breaking(model, n_teams: int, level: str = 'auto'):
    """
    Add symmetry breaking constraints based on problem size and level.
    
    Args:
        model: Pyomo model
        n_teams: Number of teams
        level: Symmetry breaking level ('none', 'basic', 'moderate', 'aggressive', 'auto')
    """
    if level == 'none':
        return
    
    if level == 'auto':
        # Automatically choose level based on problem size
        if n_teams <= 6:
            level = 'basic'
        elif n_teams <= 10:
            level = 'moderate'
        else:
            level = 'aggressive'
    
    logger.info(f"Applying {level} symmetry breaking for {n_teams} teams")
    
    if level == 'basic':
        # Just fix one or two games
        model.symmetry1 = pyo.Constraint(expr=model.x[0, 1, 0, 0] == 1)
        if n_teams >= 4:
            model.symmetry2 = pyo.Constraint(expr=model.x[2, 3, 0, 1] == 1)
    
    elif level == 'moderate':
        # Fix first week partially
        fix_first_week(model, min(n_teams, 6))
    
    elif level == 'aggressive':
        # Fix entire first week and team ordering
        fix_first_week(model, n_teams)
        fix_team_order(model)

""" def add_adaptive_symmetry_breaking(model, n_teams):
    if n_teams <= 4:
        # Small tournament: fix one game
        model.symmetry1 = pyo.Constraint(expr=model.x[0, 1, 0, 0] == 1)
        
    elif n_teams <= 8:
        # Medium tournament: fix first two games
        model.symmetry1 = pyo.Constraint(expr=model.x[0, 1, 0, 0] == 1)
        model.symmetry2 = pyo.Constraint(expr=model.x[2, 3, 0, 1] == 1)
        
    else:
        # Large tournament: fix entire first week
        fix_complete_first_week(model, n_teams)
        
        # Additional: fix team 0's position in week 1
        model.symmetry_week1 = pyo.Constraint(
            expr=sum(model.x[0, j, 1, 0] for j in model.Teams if j != 0) == 1
        ) """

        
# add constraints to the model
def add_constraints(model, 
                    symmetry_breaking: bool = True,
                    symmetry_level: str = 'auto') -> None:
    # Validate model has required sets
    if not hasattr(model, 'Teams') or not hasattr(model, 'Weeks') or not hasattr(model, 'Periods'):
        raise ValueError("Model missing required sets")
    
    model.play_once = pyo.Constraint(model.Teams, model.Teams, rule=play_once_rule)
    model.once_per_week = pyo.Constraint(model.Teams, model.Weeks, rule=once_per_week_rule)
    model.one_game_per_period = pyo.Constraint(model.Weeks, model.Periods, rule=one_game_per_period_rule)
    model.max_twice_per_period = pyo.Constraint(model.Teams, model.Periods, rule=max_twice_per_period_rule)
    model.no_self_play = pyo.Constraint(model.Teams, model.Weeks, model.Periods, rule=no_self_play_rule)
    if symmetry_breaking:
        add_adaptive_symmetry_breaking(model, n_teams=len(model.Teams), level=symmetry_level)


