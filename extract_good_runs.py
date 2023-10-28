import sys, os
import math
import time
import json
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

if len(sys.argv) <= 2: exit()
room = sys.argv[2]
filename = None
if len(sys.argv) > 3:
    filename = sys.argv[3]
if room == 'all': room = True

plotter = render.Plotter()

def _filter(x):
    return room is True or x.room == room

room_offsets = {
'g-00': (-355, 469),
'g-01': (-457, 469),
'g-02': (-586, 456),
'g-03b': (-750,388),
'g-04': (-846,456),
'g-05': (-980,419),
'g-06': (-1095,379),
}

room_offsets = {k:(v[0]*8, v[1]*8) for k,v in room_offsets.items()}

lock_blocks = {
'g-00': [(560,240)],
'g-01': [(608,24), (120,160)],
'g-03b': [(384,416)],
'g-05': [(88,0)],
}

fixed_blocks = {
'g-00': [
    (312,320,32,16),
    (200,248,16,16),
    (352,104,32,16),
    (720,336,48,16),
    (0,96,48,16),
    ],
'g-01': [
    (600,272,32,16),
    (456,568,32,16),
    (248,472,32,16),
    (400,424,16,16),
    (352,320,16,16),
    (400,272,16,16),
    (328,256,16,16),
    (376,232,16,16),
    (304,216,16,16),
    (360,200,16,16),
    (312,176,16,16),
    (360,152,32,16),
    (768,96,48,16),
    (768,248,16,160),
    (768,512,16,16),
    (0,160,48,16),
    (0,0,16,136),
    ],
'g-03b': [
    (1328,432,32,16),
    (1224,352,32,16),
    (1312,280,32,16),
    (1184,208,32,16),
    (1304,128,32,16),
    (992,136,32,16),
    (456,208,32,16),
    (552,192,32,16),
    (784,120,16,16),
    (688,104,32,16),
    (456,208,32,16),
    (304,392,32,16),
    (1312,512,48,32),
    (1408,120,16,72),
    (104,504,56,32),
    (144,504,16,40),
    (0,528,160,16),
    (224,496,16,48),
    (224,528,1096,16),
    (1408,512,16,32),
    (1408,528,72,16),
    ],
'g-05': [
    (824,456,32,16),
    (496,496,32,16),
    (1064,152,16,16),
    (760,192,32,16),
    (416,264,32,16),
    (272,416,16,16),
    (1032,400,40,16),
    (1056,296,16,88),
    (0,144,40,16),
    (24,144,16,88),
#    (336,56,32,488),
    ]
}

room_tiles = defaultdict(set)
fixed_tiles = defaultdict(set)

room_plotters = defaultdict(render.Plotter)

def map_tile(x,y):
    return math.floor(x/8), math.floor(y/8)

for run in runs:
    if tuw.ControlFlags.dead in run.control_flags:
        continue

    run_room = run.room_order[0]
    for state in run.states:
        box = render.Plotter._state_box(state)
        center = [box[0] + box[2]/2, box[1]-box[3]/2]
#        center = [box[0] + box[2]/2, box[1]]
        center = map_tile(*center)
        room_tiles[run_room].add(tuple(center))

    room_plotters[run_room].add_run(run, lambda x: True)

for room_name, tiles in room_tiles.items():
    xoff, yoff = room_offsets.get(room_name, (0,0))
    for x, y in lock_blocks.get(room_name, []):
        for dx in [8,16]:
            for dy in [8,16]:
                pos = map_tile(xoff+x+dx, yoff+y+dy)
                tiles.add(pos)

    for x, y, w, h in fixed_blocks.get(room_name, []):
        for dx in range(w):
            for dy in range(h):
                pos = map_tile(xoff+x+dx, yoff+y+dy)
                fixed_tiles[room_name].add(pos)
                try:
                    tiles.remove(pos)
                except KeyError: pass

if filename is not None:
    print(f'dumping to {filename}')
    room_tiles = {k:list(v) for k,v in room_tiles.items()}
    fixed_tiles = {k:list(v) for k,v in fixed_tiles.items()}
    data = {k: {
        'initial_tiles':room_tiles[k],
        'fixed_tiles':fixed_tiles.get(k, []),
        } for k in room_tiles.keys()}
    with open(filename, 'w') as fp:
        json.dump(data, fp)

for room_name, plotter in room_plotters.items():
    if not room_name in {'g-00'}:
        continue
    plotter.finalize()
    plotter.render(f'{room_name}.png', show=False)

