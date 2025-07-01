import pyomo.environ as pyo
from pyomo.opt import SolverStatus, TerminationCondition
import logging
from typing import Dict, List, Tuple, Optional, Any
import time
from source.MIP.constraints import add_constraints

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
        

    def build_model(self, 
                    symmetry_breaking: bool = True,
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
        
        # add constraints
        add_constraints(self.model, symmetry_breaking=symmetry_breaking, symmetry_level=symmetry_level)
        # Objective: Feasibility problem (minimize 0)
        self.model.obj = pyo.Objective(expr=0, sense=pyo.minimize)
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
        
        # Set common options
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
        """Save the solution to a JSON file in the format expected by the checker"""
        if self.solution is None:
            raise ValueError("No solution to save")
        
        import json
        
        # Format for solution checker
        output = {
            "MIP": {
                "sol": self.solution['schedule'] if self.solution['feasible'] else [],
                "time": self.solution['solve_time'],
                "optimal": self.solution['termination_condition'] == 'optimal'
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Solution saved to {filepath}")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO, 
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create and solve a small instance
    n_teams = 6
    
    # Build model
    sts = STSModel(n_teams)
    sts.build_model(symmetry_breaking=True, symmetry_level='auto')

    # Solve model
    solution = sts.solve(solver_name='cbc', time_limit=60)

    # Save solution
    sts.save_solution("solution.json")