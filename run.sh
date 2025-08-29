#!/bin/bash
set -e

APPROACH=$1
shift

case "$APPROACH" in
  MIP)
    python source/MIP/mip_model.py "$@"
    ;;
  CP)
    python source/CP/cp_model.py "$@"
    ;;
  SAT)
    python source/SAT/sat_model.py "$@"
    ;;
  all)
    for inst in {1..14}; do
      echo "Running MIP on instance $inst"
      python source/MIP/mip_model.py $inst
    done

    for inst in {1..14}; do
      echo "Running CP on instance $inst"
      python source/CP/cp_model.py $inst
    done

    for inst in {1..18}; do
      echo "Running SAT on instance $inst"
      python source/SAT/sat_model.py $inst
    done
    ;;
  *)
esac