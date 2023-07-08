import sys, os
import time

import tuw
from tuw import plots

infile = sys.argv[1]
start_time = time.time()
states = tuw.StateDump(infile)
end_time = time.time()

print(f'{len(states.states)} states loaded in {end_time-start_time:.2f} s')
print(states.map)
print(states.chapter)
print(states.rooms)

runs = states.extract_sequences(tuw.Run)
print(f'{len(runs)} total runs')

#for run in runs:
#    print(run.control_flags)

if len(sys.argv) == 2: exit()
room = sys.argv[2]
if room == 'all': room = True

plotter = plots.Plotter()


for run in runs:
    if room is True or room in run.rooms:
        plotter.plot(run)

plotter.show()
