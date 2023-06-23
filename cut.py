import sys, os
import time

import moviepy.editor

import tuw

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
        self.rooms = set()
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

        self.states.append(state)
        self.rooms.add(state.room)

    def match_spawn(self, other):
        dx = self.states[0].xpos - other.states[0].xpos
        dy = self.states[0].ypos - other.states[0].ypos

        dist = dx*dx + dy*dy
        return dist < 8*8


runs = states.extract_sequences(ClipRun)
print(f'{len(runs)} total runs')

export_runs = []
for idx, run in enumerate(runs):
#    print(run.states[0].sequence, run.states[-1].sequence)
    include = False
    if len(run.rooms) >1 or idx == 0 or idx == len(runs)-1:
        include = True
    if idx < len(runs)-1:
        next_run = runs[idx+1]
        if not run.match_spawn(next_run):
            include = True

    if include:
        export_runs.append(run)

base = moviepy.editor.VideoFileClip(video_file)
clips = []
for run in export_runs:
    start = run.states[0].timestamp-video_start_time
    end = run.states[-1].timestamp-video_start_time
    clip = base.subclip(start, end)
    clips.append(clip)

out_clip = moviepy.editor.concatenate_videoclips(clips)
out_clip.write_videofile('output.mp4')

