import sys, os
import time
from collections import defaultdict

import tuw
from tuw import render

infile = sys.argv[1]
start_time = time.time()
states = tuw.StateDump(infile)
end_time = time.time()

print(f'{len(states.states)} states loaded in {end_time-start_time:.2f} s')
print(states.map)
print(states.chapter)
print(states.rooms)

runs = states.extract_sequences(tuw.RoomCompleteRun)

print(f'{len(runs)} total runs')

#for run in runs:
#    print(run.control_flags)

if len(sys.argv) == 2: exit()
room = sys.argv[2]
if room == 'all': room = True

plotter = render.Plotter()

def _filter(x):
    return room is True or x.room == room

numbers = [211, 212]

#room_map = defaultdict(list)
for run in runs:
    deaths = set()
    for state in run.states:
        deaths.add(state.deaths)
    print(f'{run.rooms}: {deaths}')

for run in runs:
#    if not tuw.ControlFlags.paused in run.control_flags:
#        continue
#    if not tuw.CollectionFlags.key in run.collection_flags:
#        continue
    if tuw.ControlFlags.dead in run.control_flags:
        continue
    if not room in run.rooms:
        continue

    print(run.room_order)
    print(run.states[0].deaths)
#    include = False
#    for state in run.states:
#        if state.ypos < -3050:
#            include = True
#    if not include:
#        continue

    if room is True or room in run.rooms:
        plotter.add_run(run, _filter)

plotter.finalize()
plotter.render('test.png', show=True)

