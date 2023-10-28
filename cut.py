import sys, os
import time

from collections import defaultdict

import moviepy.editor


numbers = [413, 420, 612, 720, 1025, 1337, 1413, 1612, 1420, 2012, 2020, 2600, 7859]


import tuw
import tuw.clusters

infiles = []
output_file = 'output.mp4'
for name in sys.argv[1:]:
    if 'mp4' in name:
        output_file = name
    elif '.txt' in name:
        with open(name, 'r') as fp:
            for line in fp.read().split('\n'):
                line = line.strip()
                if line != '' and line[0] != '#':
                    infiles.append(line)
    elif 'dump' in name:
        infiles.append(name)
    else:
        print(f"Warning: can't handle input file {name}")

base = os.path.expanduser('~/Videos/Streams')
stamp_file = os.path.join(base, 'recording_data.txt')
video_index = defaultdict(dict)
with open(stamp_file, 'r') as fp:
    raw = fp.read()
for line in raw.split():
    vidname, event, stamp = [x.strip('"') for x in line.split(',')]
    video_index[vidname][event] = float(stamp)


def get_clip_info(video_index, start, end):
    #TODO: handle corner cases where a run spans 2 videos
    #or extends past the edge of a video
    for vidname, events in video_index.items():
        if events['start'] <= start and events['stop'] >= end:
            return vidname, events['start']
    raise RuntimeError(f"Couldn't find video matching stamps {start}, {end}")


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

        if (tuw.ControlFlags.dead in state.control_flags
            or (len(self.states) > 0 and state.deaths != self.states[-1].deaths)
                ):
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

    def get_segments(self):
        result = []

        #this sure is a hideous way of removing paused segments
        #that aren't part of the beginning or end of a run
        paused = self.states[0].control_flags.value&8
        left = self.states[0]
        for state in self.states[1:]:
            tpaused = state.control_flags.value&8
            if tpaused and not paused: #pause
                result.append([left, state])
            if not tpaused and paused: #unpause
                left = state
            paused = tpaused

        if len(result) > 0:
            if result[-1][0] == left:
                result[-1][1] = self.states[-1]
            else:
                result.append([left, self.states[-1]])
        else:
            return [(self.states[0].timestamp,self.states[-1].timestamp)]

        result = [(a.timestamp, b.timestamp) for a,b in result]
        return result


export_runs = []

for infile in infiles:
    start_time = time.time()
    states = tuw.StateDump(infile)
    end_time = time.time()

    print(f'{len(states.states)} states loaded in {end_time-start_time:.2f} s')
    print(states.map)
    print(states.chapter)
    print(states.rooms)

    runs = states.extract_sequences(ClipRun)
    print(f'{len(runs)} total runs')


    cluster_runs = []
    longest_fails = []

    room_map = defaultdict(list)
    for run in runs:
        for room in run.rooms:
            room_map[room].append(run)

    for room, room_runs in room_map.items():
        try:
            grp = tuw.clusters.GroupClusters(room_runs)
            count = len(grp.labels_by_size)
            N = int(count/6)
            cluster_runs.extend(grp.get_best_runs(N, lambda x:x.run.states[0].sequence))
        except Exception as e:
            print(f'Failed to cluster on {room}: {e}')

        sub_runs = list(filter(lambda x: len(x.rooms) == 1, room_runs))
        if len(sub_runs) >= 10:
            longest = max(sub_runs, key= lambda x: x.get_length())
            longest_fails.append(longest)


    counts = defaultdict(lambda:0)
    if False:
        for idx, run in enumerate(runs):
            if run.states[0].deaths in (20,):
                export_runs.append(run)
    else:
        for idx, run in enumerate(runs):
            include = False
            if len(run.rooms) >1 or idx == 0 or idx == len(runs)-1:
                counts['room change'] += 1
                include = True
            elif run.state_change_flags.value & 0xcf:
                counts['state change'] += 1
        #        print(run.state_change_flags)
                include = True
            elif run.collection_flags.value & 0x7f:
                counts['collection'] += 1
        #        print(run.collection_flags)
                include = True
            elif idx < len(runs)-1 and not run.match_spawn(runs[idx+1]):
                counts['spawn change next'] += 1
                include = True
            elif idx > 0 and not run.match_spawn(runs[idx-1]) and not (run.state_change_flags.value&0x01 == 0):
                counts['spawn change prev'] += 1
                include = True
            elif run in cluster_runs:
                counts['clusters'] += 1
        #        print(f'{idx}: from cluster')
                include = True
            elif run in longest_fails:
                counts['long fails'] += 1
        #        print(f'{idx}: from longest fails')
                include = True
            elif run.states[0].deaths in numbers:
                include = True
                counts['numbers'] += 1

            if include:
                export_runs.append(run)

    for key, val in counts.items():
        print(f'{key}: {val} runs')

    print(f'{len(export_runs)=}')

source_video_map = {}
clips = []
segments = []
for run in export_runs:

    for start, end in run.get_segments():
        vidname, video_start_time = get_clip_info(video_index, start, end)

        start -= video_start_time
        end -= video_start_time

        if not vidname in source_video_map.keys():
            source_video_map[vidname] = moviepy.editor.VideoFileClip(vidname)

        base = source_video_map[vidname]

        if end < 0: continue
        if start > base.duration: continue

        if start < 0:
            print(f'start clipped from {start} to 0')
            start = 0
        if end > base.duration:
            print(f'end clipped from {end} to {base.duration}')
            end = base.duration

        segments.append((start, end, base))

for start, end, base in segments:
    clip = base.subclip(start, end)
    clips.append(clip)


print(f'{len(clips)=})')

out_clip = moviepy.editor.concatenate_videoclips(clips)
out_clip.write_videofile(output_file)

