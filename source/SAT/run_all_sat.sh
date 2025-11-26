#!/bin/bash

# Makes the script more robust: stops if an error occurs
set -e

echo "=== Starting sequential SAT execution from n=2 to n=20 ==="

# Loop from 2 to 20 with step 2 (only even numbers, as required by your Python code)
for n in {2..20..2}
do
    echo "--------------------------------------------------"
    echo "Running SAT solver for $n teams..."
    echo "--------------------------------------------------"
    
    # Executes the docker command as defined in the README
    # Adding --optimality since you were working on the objective function
    # Adding --verbose to see progress in the terminal
    docker-compose run --rm solve-SAT $n --optimality --verbose
    
    echo "Completed n=$n"
    echo "" # Empty line for separation
done

echo "=== All instances have been executed! ==="