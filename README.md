# CDMO_Proj_LiPiDo

A Combinatorial Decision Making and Optimization project implementing three different approaches: Mixed Integer Programming (MIP), Constraint Programming (CP), and Boolean Satisfiability (SAT).

## Project Structure

```
├── res/              # Results
│   ├── MIP/
│   ├── CP/
│   └── SAT/
├── source/
│   ├── MIP/          # Mixed Integer Programming implementation
│   ├── CP/           # Constraint Programming implementation
│   └── SAT/          # SAT solver implementation
├── run.sh            
├── Dockerfile        
└── compose.yml       
```

## Prerequisites

- Docker
- Docker Compose

## Quick Start

### 1. Build

```bash
docker-compose build
```

### 2. Run

#### Run MIP on a specific instance:
```bash
docker-compose run solve-mip <n_teams> --solver_name <cbc|gurobi|HiGHS>
```

#### Run CP on a specific instance:
```bash
docker-compose run solve-cp <n_teams>
```
To give all the parameters to the solver:
```bash
docker-compose run solve-cp <n_teams> [solver] --seed <seed>
```
Default: `time_limit=300`, `random_seed=False`.

#### Run SAT on a specific instance:
```bash
docker-compose run solve-SAT <n_teams>
```
To give all the parameters to the solver:
```bash
docker-compose run solve-SAT <n_teams> --time_limit <time_limit> --optimality --random_seed --verbose
```
Default: `time_limit=300`, `optimality=False`, `random_seed=False`, `verbose=False`

### 3. Run All Approaches on All Instances

```bash
docker-compose run solve-all
```

## Output

Results will be saved in the `res/` directory. The `res/` directory is mounted as a volume to persist results.
- MIP results in `res/MIP/`
- CP results in `res/CP/`
- SAT results in `res/SAT/`