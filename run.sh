#!/bin/bash
set -e

APPROACH=$1
shift

case "$APPROACH" in
  MIP)
    python source/MIP/mip_solver_pulp.py "$@"
    ;;
  CP)
    python source/CP/minizinc_runner.py "$@"
    ;;
  SAT)
    python source/SAT/SAT_solver.py "$@"
    ;;
  all)
    for inst in {2..20..2}; do
      echo "Running CP on instance $inst"
      python source/CP/minizinc_runner.py $inst "$@"
    done

    for inst in {2..20..2}; do
      for solver in gurobi HiGHS; do
        echo "Running MIP on instance $inst with solver $solver"
        python source/MIP/mip_solver_pulp.py $inst --solver_name $solver "$@"
      done
    done

    for inst in {2..20..2}; do
      echo "Running SAT on instance $inst"
      python source/SAT/SAT_solver.py $inst "$@"
    done
    ;;
  *)
esac