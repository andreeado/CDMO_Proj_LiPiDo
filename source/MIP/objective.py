class ConstraintsBuilder():
    def __init__(self, model):
        self.model = model

    def add_constraints(self):
        # Example of adding a constraint
        self.model.add_constraint("x + y <= 10")
        self.model.add_constraint("x - y >= 2")

    def set_objective(self, objective_function):
        self.model.set_objective(objective_function)

    def max_one_match_per_team_per_week_constr(self, m):
        """
         Maximum one match for each team per week (home or away)
        """

        def _max_one_match_per_team_per_week_rule(m, team_i, week_k):
            return sum(m.is_match_this_week_var[team_i, team_j, week_k]
                       for team_j in m.teams_range_set) + \
                sum(m.is_match_this_week_var[team_j, team_i, week_k]
                    for team_j in m.teams_range_set) <= 1

        m.max_one_match_per_team_per_week_constr = pe.Constraint(m.teams_range_set, m.weeks_range_set,
                                                                 rule=_max_one_match_per_team_per_week_rule)
        return m