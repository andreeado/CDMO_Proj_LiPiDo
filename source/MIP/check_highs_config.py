#!/usr/bin/env python3
import highspy

h = highspy.Highs()
opts = h.getOptions()

print("HiGHS Configuration:")
print("-" * 50)
print(f"random_seed: {opts.random_seed}")
print(f"mip_detect_symmetry: {opts.mip_detect_symmetry}")
print(f"threads: {opts.threads}")
print(f"parallel: {opts.parallel}")
print(f"presolve: {opts.presolve}")
print(f"mip_heuristic_effort: {opts.mip_heuristic_effort}")
