% Parameters

par int: n; 

int: nMatches = (n - 1) * n div 2;

set of int: Matches = 1..nMatches;

% Array of zeros

array[Matches] of int: zeros = [0 | i in 1..nMatches];

%CONTRADICTION
var int: m;

constraint m = 5; % Set the value of n
constraint m = 10; % CONTRADICTORY CONSTRAINT: This makes the model unsatisfiable!

% Define the objective function as n
solve minimize m;

output [
    show(zeros) ++
    "\nObjective function: " ++ show(n)
];