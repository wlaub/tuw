import os
import time
import subprocess
from collections import defaultdict

import moviepy.editor

import tuw
import tuw.clusters

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




class CutInput:

    def __init__(self, infile):
        self.infile = infile
        self.load()

    def load(self):
        start_time = time.time()
        self.states = states = tuw.StateDump(self.infile)
        end_time = time.time()

        print(f'{len(states.states)} states loaded in {end_time-start_time:.2f} s')
        print(states.map)
        print(states.chapter)
        print(states.rooms)

        self.runs = runs = states.extract_sequences(ClipRun)
        print(f'{len(runs)} total runs')


        self.cluster_runs = cluster_runs = []
        self.longest_fails = longest_fails = []

        self.room_map = room_map = defaultdict(list)
        for run in runs:
            for room in run.rooms:
                room_map[room].append(run)

        self.cluster_map = {}
        for room, room_runs in room_map.items():
            try:
                grp = tuw.clusters.GroupClusters(room_runs)
                for run, cluster in grp.run_map.items():
                    self.cluster_map[run] = (room, cluster)
            except (ValueError, IndexError) as e:
                #print(f'Failed to cluster on {room}: {e}')
                pass
            else:
                count = len(grp.labels_by_size)
                N = int(count/6)
                cluster_runs.extend(grp.get_best_runs(N, lambda x:x.run.states[0].sequence))
            sub_runs = list(filter(lambda x: len(x.rooms) == 1, room_runs))
            if len(sub_runs) >= 10:
                longest = max(sub_runs, key= lambda x: x.get_length())
                longest_fails.append(longest)


    def extract_runs(self, state_change, collection, numbers):
        runs = self.runs

        export_runs = []
        export_conditions = []
        extant_clusters = set()

        counts = defaultdict(lambda:0)
        unique_counts = defaultdict(lambda:0)
        for idx, run in enumerate(runs):
            conditions = set()
            cluster = self.cluster_map.get(run, None)
            if len(run.rooms) >1 or idx == 0 or idx == len(runs)-1:
                conditions.add('room_change')
            if run.state_change_flags.value & state_change:
                conditions.add('state change')
        #        print(run.state_change_flags)
            if run.collection_flags.value & collection:
                conditions.add('collection')
        #        print(run.collection_flags)
            if idx < len(runs)-1 and not run.match_spawn(runs[idx+1]):
                conditions.add('spawn change next')
            if idx > 0 and not run.match_spawn(runs[idx-1]) and not (run.state_change_flags.value&0x01 == 0):
                conditions.add('spawn change prev')
            if run in self.cluster_runs and False:
                conditions.add('cluster')
        #        print(f'{idx}: from cluster')
            if run in self.longest_fails:
                conditions.add('long fail')
        #        print(f'{idx}: from longest fails')
            if run.states[0].deaths in numbers:
                conditions.add('numbers')

            if len(conditions) > 0:
                extant_clusters.add(cluster)
                export_conditions.append(conditions)
                for cond in conditions:
                    counts[cond] += 1
                if len(conditions) == 1:
                    unique_counts[list(conditions)[0]] += 1
                export_runs.append((idx, run))
                if run in self.cluster_runs and not 'cluster' in conditions:
                    counts['cluster'] += 1

        for idx, run in enumerate(runs):
            conditions = set()
            cluster = self.cluster_map.get(run, None)

            if run in self.cluster_runs and not cluster in extant_clusters:
                conditions.add('cluster')

            if len(conditions) > 0:
                extant_clusters.add(cluster)
                export_conditions.append(conditions)
                for cond in conditions:
                    counts[cond] += 1
                if len(conditions) == 1:
                    unique_counts[list(conditions)[0]] += 1
                export_runs.append((idx, run))

        export_runs = sorted(export_runs, key=lambda x: x[0])
        indices, export_runs = list(zip(*export_runs))

#        for key, val in counts.items():
#            print(f'{key}: {val} runs')

#        print(f'{len(export_runs)=}')

        return export_runs, export_conditions, counts, unique_counts



class Clipper:

    def __init__(self, stamp_file_path):
        self.stamp_file_path = os.path.expanduser(stamp_file_path)

        self.stamp_file = stamp_file = os.path.join(self.stamp_file_path, 'recording_data.txt')
        self.video_index = video_index = defaultdict(dict)
        with open(stamp_file, 'r') as fp:
            raw = fp.read()
        for line in raw.split():
            vidname, event, stamp = [x.strip('"') for x in line.split(',')]
            video_index[vidname][event] = float(stamp)

    def get_clip_info(self, start, end):
        #TODO: handle corner cases where a run spans 2 videos
        #or extends past the edge of a video
        for vidname, events in self.video_index.items():
            if events['start'] <= start and events['stop'] >= end:
                return vidname, events['start']
        raise RuntimeError(f"Couldn't find video matching stamps {start}, {end}")

    def compute_clips(self, export_runs):
        self.source_video_map = source_video_map = {}
        segments = []
        for run in export_runs:

            for start, end in run.get_segments():
                vidname, video_start_time = self.get_clip_info(start, end)

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

                segments.append((start, end, base, vidname))

        return segments

    def get_full_output_file(self, output_file):
        output_file = os.path.expanduser(output_file)
        if output_file[0] != '/':
            output_file = os.path.join(self.stamp_file_path, output_file)
        return output_file

    def export_moviepy(self, segments, output_file):
        output_file = self.get_full_output_file(output_file)

        clips = []
        for start, end, base, _ in segments:
            clip = base.subclip(start, end)
            clips.append(clip)

        print(f'{len(clips)=})')

        out_clip = moviepy.editor.concatenate_videoclips(clips)
        out_clip.write_videofile(output_file)

    def export_gpu(self, segments, output_file):
        output_file = self.get_full_output_file(output_file)

        lines = []
        for start, end, base, vidname in segments:
            lines.append(f"file {vidname}")
            lines.append(f'inpoint {start}')
            lines.append(f'outpoint {end}')

        file_list = '\n'.join(lines)

        list_path = os.path.join(self.stamp_file_path, 'my_list.txt')
        with open(list_path, 'w') as fp:
            fp.write(file_list)

        cmd = f'ffmpeg  -y -vsync 0 -hwaccel cuda -hwaccel_output_format cuda -safe 0 -c:v h264_cuvid -f concat -i {list_path} -c:v h264_nvenc -af aresample=async=1000 {output_file} -v quiet -stats'

        result = subprocess.check_output(cmd, shell=True)

