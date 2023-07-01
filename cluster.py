
import sys, os
import time

from collections import defaultdict

from matplotlib import pyplot as plt

import tuw
from tuw import clusters

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


room_map = defaultdict(list)
for run in runs:
    for room in run.rooms:
        room_map[room].append(run)

for room, runs in room_map.items():
    print(f'{room}: {len(runs)}')

if len(sys.argv) == 2: exit()
room = sys.argv[2]

grp = clusters.GroupClusters(room_map[room])

label_map = grp.labels_by_size

fig = plt.figure()
ax = fig.add_subplot(projection='3d')
ax.set_proj_type('ortho')

#ax.scatter(*(list(zip(*clst.centroids_))[:3]), c='r')

for label, lpoints in label_map[:4]:
    ax.scatter(*(list(zip(*lpoints))[:3]), alpha=1)



plt.show()

