from argparse import ArgumentParser
import pyomo.environ as pyo
from pyomo.opt import SolverStatus, TerminationCondition
import logging
from typing import Dict, List, Optional, Any
import time
from constraints import add_constraints
import os
import json

logger = logging.getLogger(__name__)

class STSModel():
    """
    A class to represent a sports tournament scheduling model using Pyomo.
    Solver independent, can be used with any solver that supports Pyomo.
    """

    def __init__(self, n_teams: int):
        """
        Initialize the STS model
        
        Args:
            n_teams: Number of teams (must be even)
        """
        if n_teams % 2 != 0:
            raise ValueError("Number of teams must be even")
        
        self.n_teams = n_teams
        self.n_weeks = n_teams - 1
        self.n_periods = n_teams // 2
        self.model = None
        self.solution = None
        
        logger.info(f"Initialized STS model: {n_teams} teams, {self.n_weeks} weeks, {self.n_periods} periods")
    
    def _extract_schedule(self) -> List[List[List[int]]]:
        if self.model is None:
            raise ValueError("Model not built")
        
        schedule = []
        for period in range(self.n_periods):
           period_matches = []
           for week in range(self.n_weeks):
               for i in self.model.Teams:
                   for j in self.model.Teams:
                       if i != j and pyo.value(self.model.x[i, j, week, period]) > 0.5:
                           period_matches.append([i+1, j+1])
           schedule.append(period_matches)
        return schedule

    def build_model(self, 
                    symmetry_breaking: bool = False,
                    symmetry_level: str = 'auto') -> pyo.ConcreteModel:
        logger.info("Building STS model")
        self.model = pyo.ConcreteModel("STS")

        # sets
        self.model.Teams = pyo.RangeSet(0, self.n_teams-1)
        self.model.Weeks = pyo.RangeSet(0, self.n_weeks-1)
        self.model.Periods = pyo.RangeSet(0, self.n_periods-1)

        # decision variables
        # x[i,j,k,p] = 1 if team i plays at home against team j in week k, period p
        # x[i,j,k,p] = 0 otherwise
        self.model.x = pyo.Var(self.model.Teams, self.model.Teams, self.model.Weeks, self.model.Periods, 
                         domain=pyo.Binary)
        
        # auxiliary variables for optimization
        self.model.d_pos = pyo.Var(self.model.Teams, domain=pyo.NonNegativeIntegers)
        self.model.d_neg = pyo.Var(self.model.Teams, domain=pyo.NonNegativeIntegers)

        # add constraints
        add_constraints(self.model, symmetry_breaking=symmetry_breaking, symmetry_level=symmetry_level)
        # Lower bound = n
        lb = self.n_teams

        # Upper bound = n * (n - 1)
        ub = self.n_teams * (self.n_teams - 1)

        # Objective: sum of deviations
        expr = sum(self.model.d_pos[i] + self.model.d_neg[i] for i in self.model.Teams)
        self.model.obj = pyo.Objective(expr=expr, sense=pyo.minimize)

        # Add an explicit constraint for the bounds
        self.model.obj_lower_bound = pyo.Constraint(expr=expr >= lb)
        self.model.obj_upper_bound = pyo.Constraint(expr=expr <= ub)


        # Objective: Feasibility problem (minimize 0)
        # self.model.obj = pyo.Objective(expr=0, sense=pyo.minimize)

        # Objetive: Optimization problem (balances home-away matches)
        """ self.model.obj = pyo.Objective(expr=sum(self.model.d_pos[i]+ self.model.d_neg[i] 
                                                for i in self.model.Teams), sense=pyo.minimize) """
        return self.model
    
    def solve(self, solver_name: str = 'cbc', 
             solver_options: Optional[Dict[str, Any]] = None,
             time_limit: Optional[int] = 300,
             mip_gap: Optional[float] = 0.01,
             tee: bool = False) -> Dict:
        """
        Solve the model using the specified solver
        
        Args:
            solver_name: Name of the solver ('gurobi', 'cplex', 'cbc', 'glpk', 'scip', etc.)
            solver_options: Dictionary of solver-specific options
            time_limit: Time limit in seconds
            mip_gap: MIP optimality gap
            tee: Whether to display solver output
            
        Returns:
            Dictionary with solution information
        """
        if self.model is None:
            raise ValueError("Model must be built before solving")
        
        logger.info(f"Solving with {solver_name}...")
        
        # Create solver
        solver = pyo.SolverFactory(solver_name)
        
        if solver_options is None:
            solver_options = {}
        
        # Handle solver-specific option names
        if solver_name == 'gurobi':
            if time_limit:
                solver_options['TimeLimit'] = time_limit
            if mip_gap:
                solver_options['MIPGap'] = mip_gap
        elif solver_name == 'cplex':
            if time_limit:
                solver_options['timelimit'] = time_limit
            if mip_gap:
                solver_options['mip.tolerances.mipgap'] = mip_gap
        elif solver_name == 'cbc':
            if time_limit:
                solver_options['seconds'] = time_limit
            if mip_gap:
                solver_options['ratioGap'] = mip_gap
        elif solver_name == 'glpk':
            if time_limit:
                solver_options['tmlim'] = time_limit
            if mip_gap:
                solver_options['mipgap'] = mip_gap
        
        # Apply solver options
        for key, value in solver_options.items():
            solver.options[key] = value
        
        # Solve
        start_time = time.time()
        results = solver.solve(self.model, tee=tee)
        solve_time = time.time() - start_time
        
        # Extract solution
        solution_info = {
            'solver': solver_name,
            'solve_time': solve_time,
            'termination_condition': str(results.solver.termination_condition),
            'status': str(results.solver.status),
        }
        
        if (results.solver.termination_condition == TerminationCondition.optimal or
            results.solver.termination_condition == TerminationCondition.feasible):
            
            # Extract schedule
            schedule = self._extract_schedule()
            solution_info['schedule'] = schedule
            solution_info['feasible'] = True
            
            # Get objective value if exists
            if hasattr(self.model, 'obj'):
                solution_info['objective_value'] = pyo.value(self.model.obj)

                
        else:
            solution_info['feasible'] = False
            solution_info['schedule'] = None
        
        self.solution = solution_info
        logger.info(f"Solving complete: {solution_info['termination_condition']} in {solve_time:.2f}s")
        
        return solution_info
    

    def save_solution(self, filepath: str) -> None:
        if self.solution is None:
            raise ValueError("No solution to save")
        
        # Format for solution checker
        solver_name = self.solution['solver']
        output = {
            solver_name: {
                "time": self.solution['solve_time'],
                "optimal": self.solution['termination_condition'] == 'optimal',
                "obj": self.solution['objective_value'] if 'objective_value' in self.solution else None,
                "sol": self.solution['schedule'] if self.solution['feasible'] else []
            }
        }
        # Load existing data if file exists
        
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        data.update(output)
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Solution saved to {filepath}")

    def display_schedule(self) -> None:
        """
        Display schedule as a table with weeks as rows and periods as columns

        """
        if self.solution is None or not self.solution['feasible']:
            print("No feasible solution to display")
            return
        
        schedule = self.solution['schedule']
        
        print(f"TOURNAMENT SCHEDULE - {self.n_teams} Teams")
        
        # Header
        header = f"{'Period':<12}"
        for p in range(self.n_weeks):
            p+=1
            header += f"{'Week' + str(p):<15}"
        print("-" * len(header))
        print(header)
        print("-" * len(header))
        
        # Schedule rows
        for period in range(self.n_periods):
            row = f"{period+1:<12}"
            for week in range(self.n_weeks):
                matches = schedule[period][week]
                if matches:
                    # Should be exactly one match per period
                    match_str = f"{matches[0]} vs {matches[1]}"
                else:
                    match_str = "---"
                row += f"{match_str:<15}"
            print(row)
        
        print(f"\n{'='*60}")
    

    

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    parser = ArgumentParser()
    parser.add_argument("n_teams", type=int, help="Number of teams (must be even)")

    parser.add_argument("--symmetry_breaking", action="store_true",
                        help="Apply symmetry breaking (default: False)")

    parser.add_argument("--symmetry_level", type=str, default="auto",
                        choices=["auto", "basic", "moderate", "aggressive"],
                        help="Symmetry level (default: auto)")

    parser.add_argument("--solver_name", type=str, default="cbc",
                        choices=["cbc", "gurobi"],
                        help="Solver name (default: cbc)")
    args = parser.parse_args()

    # Build model
    sts = STSModel(args.n_teams)
    sts.build_model(symmetry_breaking=args.symmetry_breaking, symmetry_level=args.symmetry_level)

    # Solve model
    solution = sts.solve(solver_name=args.solver_name, time_limit=300)
    
    if solution['feasible']:
        # Display
        print("\n" + "="*80)
        sts.display_schedule()
        
        if os.path.exists("/app/res"):
            # Running in Docker
            res_path = f"/app/res/MIP/{args.n_teams}.json"
        else:
            # Running locally
            res_path = f"../../res/MIP/{args.n_teams}.json"
        # Save
        sts.save_solution(res_path)
    else:
        print(f"No feasible solution found. Status: {solution['termination_condition']}")