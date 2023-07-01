import sys, os
import time

from collections import defaultdict

import moviepy.editor

import tuw
import tuw.clusters

infile = sys.argv[1]
video_file = sys.argv[2]
video_start_time = float(sys.argv[3])

start_time = time.time()
states = tuw.StateDump(infile)
end_time = time.time()

print(f'{len(states.states)} states loaded in {end_time-start_time:.2f} s')
print(states.map)
print(states.chapter)
print(states.rooms)

class ClipRun(tuw.StateSequence):
    """
    A run is a state sequence terminated by a death and having length of
    at least 2 states.
    Includes all ending death states for timing purposes.
    """
    def __init__(self):
        super().__init__()
        self.ending = False

    def valid(self):
        return len(self.states) > 1

    def add_state(self, state):
        if self.done: return

        if tuw.ControlFlags.dead in state.control_flags:
            self.ending = True
            if len(self.states) == 0:
                self.done = True
        elif self.ending:
            self.done = True

        self._add_state(state)

    def match_spawn(self, other):
        dx = self.states[0].xpos - other.states[0].xpos
        dy = self.states[0].ypos - other.states[0].ypos

        dist = dx*dx + dy*dy
        return dist < 8*8


runs = states.extract_sequences(ClipRun)
print(f'{len(runs)} total runs')


cluster_runs = []
longest_fails = []

room_map = defaultdict(list)
for run in runs:
    for room in run.rooms:
        room_map[room].append(run)

for room, runs in room_map.items():
    grp = tuw.clusters.GroupClusters(runs)
    cluster_runs.extend(grp.get_best_runs(5))

    sub_runs = filter(lambda x: len(x.rooms) == 1, runs)
    longest = max(sub_runs, key= lambda x: x.get_length())
    longest_fails.append(longest)

export_runs = []
for idx, run in enumerate(runs):
#    print(run.states[0].sequence, run.states[-1].sequence)
    include = False
#    if idx in [6]: include = True
    if len(run.rooms) >1 or idx == 0 or idx == len(runs)-1:
        include = True
    if run.state_change_flags.value & 0xef:
        print(run.state_change_flags)
        include = True
    if run.collection_flags.value & 0x7f:
        print(run.collection_flags)
        include = True
    if idx < len(runs)-1:
        next_run = runs[idx+1]
        if not run.match_spawn(next_run):
            include = True

    if not include and run in cluster_runs:
        print(f'{idx}: from cluster')
        include = True
    if not include and run in longest_fails:
        print(f'{idx}: from longest fails')
        include = True


    if include:
        export_runs.append(run)


print(len(export_runs))

base = moviepy.editor.VideoFileClip(video_file)
clips = []
for run in export_runs:
    start = run.states[0].timestamp-video_start_time
    end = run.states[-1].timestamp-video_start_time

    if end < 0: continue
    if start > base.duration: continue

    if start < 0:
        print(f'start clipped from {start} to 0')
        start = 0
    if end > base.duration:
        print(f'end clipped from {end} to {base.duration}')
        end = base.duration

    clip = base.subclip(start, end)
    clips.append(clip)


print(len(clips))

out_clip = moviepy.editor.concatenate_videoclips(clips)
out_clip.write_videofile('output.mp4')

