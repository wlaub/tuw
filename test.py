import sys, os
import time

import tuw

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

if len(sys.argv) == 2: exit()
room = sys.argv[2]
if room == 'all': room = True

from matplotlib import pyplot as plt
from matplotlib import ticker, patches

fig, ax = plt.subplots(1,1)

for run in runs:
    if room is True or room in run.rooms:
        run.plot(ax)

ax.set_aspect('equal')
ax.xaxis.set_major_locator(ticker.MultipleLocator(base=8))
ax.yaxis.set_major_locator(ticker.MultipleLocator(base=8))
ax.grid(True, which='major', axis='both')
ax.set_axisbelow(True)

plt.show()

