#!/bin/bash

# Define the number of repetitions and the range for n
REPETITIONS=10
START_N=2
END_N=22

# Loop through each even value of n
for (( n=START_N; n<=END_N; n+=2 ))
do
    # Create the output directory for the current value of n
    OUTPUT_DIR="./res/SAT/$n"
    echo "Creating directory $OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR"

    echo "Running SAT experiments for n = $n..."

    # Loop for the specified number of repetitions
    for (( i=1; i<=REPETITIONS; i++ ))
    do
        echo "  - Repetition $i/$REPETITIONS"
        
        # Run the Docker command. The output file is n.json in the container's res/SAT directory.
        # This will map to the local ./res/SAT/$n.json file.
        docker-compose run --rm --remove-orphans solve-SAT "$n" --random_seed
        
        # Wait a moment to ensure the file is fully written by the container.
        sleep 1

        FILE_PATH="../../res/SAT/$n.json"

        # Check for the file.
        if [ -f "$FILE_PATH" ]; then
            # Move the file to the specific repetition directory.
            mv "$FILE_PATH" "$OUTPUT_DIR/run_$i.json"
        else
            echo "Error: Output file $FILE_PATH not found after run."
            # Aggiungi qui un'istruzione per la gestione dell'errore, ad esempio saltando al prossimo n o uscendo.
            # break # Esempio: esce dal loop interno se il file non viene trovato
        fi
    done
done

echo "All experiments completed."
echo "Results are saved in individual JSON files within subdirectories of res/SAT/."