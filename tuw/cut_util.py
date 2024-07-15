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


class RunInclusion:
    def __init__(self, index, run, conditions):
        self.index = index
        self.run = run
        self.conditions = conditions
        self.death_count = run.states[0].deaths

    def format(self):
        lines = []

        lines.append(', '.join(self.run.room_order))
        dur = self.run.get_duration()
        lines.append(f'{dur:.2f} s')
        length = self.run.get_length()/1000
        lines.append(f'{length:.2f} kpx')


        lines.append('')
        condition_keys = ['room_change', 'state change', 'collection', 'spawn change prev', 'spawn change next', 'cluster', 'long fail', 'numbers']
        condition_lines = [x for x in condition_keys if x in self.conditions]
        lines.extend(condition_lines)

        return '\n'.join(lines)

class ClusterManager:
    def __init__(self, room, room_runs):
        self.room = room
        self.room_runs = room_runs
        self.run_to_cluster = {}
        self.cluster_to_runs = defaultdict(list)

        self.cluster_runs = []

    def compute_clusters(self):
        try:
            grp = self.grp = tuw.clusters.GroupClusters(self.room_runs)
            for run, cluster in grp.run_map.items():
                self.run_to_cluster[run] = cluster
                self.cluster_to_runs[cluster].append(run)

            self.clusters_by_size = self.grp.labels_by_size

        except (ValueError, IndexError) as e:
            #print(f'Failed to cluster on {room}: {e}')
            raise
        else:
            self.select_clusters()

    def select_clusters(self):
        count = len(self.grp.labels_by_size)
        N = int(count/6)
        self.cluster_runs = self.grp.get_best_runs(N, lambda x:x.run.states[0].sequence)


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


        self.room_map = room_map = defaultdict(list)
        for run in runs:
            for room in run.rooms:
                room_map[room].append(run)

        self.flag_changes = tuw.FlagSet()
        for run in runs:
            self.flag_changes.merge_into_self(run.flag_changes)

        self.compute_clusters()

    def compute_clusters(self):

        self.room_to_clusters = {}

        self.cluster_runs = cluster_runs = []
        self.longest_fails = longest_fails = []

        self.cluster_map = {}
        for room, room_runs in self.room_map.items():
            cm = ClusterManager(room, room_runs)
            try:
                cm.compute_clusters()
                self.room_to_clusters[room] = cm
            except:
                pass
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


    def extract_runs(self, state_change_flags, collection_flags, numbers, flag_whitelist = None,
                    room_change = True, state_change = True,
                    collection = True, spawn_change = True,
                    clusters = True, long_fail = True,):
        runs = self.runs

        export_runs = []
        extant_clusters = set()

        included_runs = set()

        flag_changes = False
        if tuw.StateChangeFlags.flag.value & state_change_flags != 0:
            flag_changes = True

        counts = defaultdict(lambda:0)
        unique_counts = defaultdict(lambda:0)
        for idx, run in enumerate(runs):
            conditions = set()
            cluster = self.cluster_map.get(run, None)

            if room_change:
                if len(run.rooms) >1 or idx == 0 or idx == len(runs)-1:
                    conditions.add('room_change')
            if state_change:
                run_change_flags = run.state_change_flags.value & state_change_flags
                if run_change_flags:
                    if flag_changes and run_change_flags == tuw.StateChangeFlags.flag.value:
                        if flag_whitelist is not None:
                            passing_flags = run.flag_changes.flags_changed.keys() & flag_whitelist
                            if len(passing_flags) > 0:
                                conditions.add('state change')
                        else:
                            conditions.add('state change')
                    else:
                        conditions.add('state change')
            if collection:
                if run.collection_flags.value & collection_flags:
                    conditions.add('collection')
            if spawn_change:
                if idx < len(runs)-1 and not run.match_spawn(runs[idx+1]):
                    conditions.add('spawn change next')
                if idx > 0 and not run.match_spawn(runs[idx-1]) and not (run.state_change_flags.value&0x01 == 0):
                    conditions.add('spawn change prev')
            if long_fail:
                if run in self.longest_fails:
                    conditions.add('long fail')
            if run.states[0].deaths in numbers:
                conditions.add('numbers')

            if len(conditions) > 0:
                extant_clusters.add(cluster)
                for cond in conditions:
                    counts[cond] += 1
                if len(conditions) == 1:
                    unique_counts[list(conditions)[0]] += 1

#                export_runs.append((idx, run))

                export_runs.append(RunInclusion(idx, run, conditions))
                included_runs.add(idx)

                if run in self.cluster_runs and not 'cluster' in conditions:
                    counts['cluster'] += 1

        if clusters:
            for idx, run in enumerate(runs):
                if idx in included_runs:
                    continue
                conditions = set()
                cluster = self.cluster_map.get(run, None)

                if run in self.cluster_runs and not cluster in extant_clusters:
                    conditions.add('cluster')

                if len(conditions) > 0:
                    extant_clusters.add(cluster)
                    for cond in conditions:
                        counts[cond] += 1
                    if len(conditions) == 1:
                        unique_counts[list(conditions)[0]] += 1
#                    export_runs.append((idx, run))
                    export_runs.append(RunInclusion(idx, run, conditions))
                    included_runs.add(idx)

        export_runs = list(sorted(export_runs, key=lambda x: x.index))

        return export_runs, counts, unique_counts, extant_clusters



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
        out_clip.write_videofile(output_file, codec='h264_nvenc', logger=None)

    def _export_gpu(self, segments, output_file):
        output_file = self.get_full_output_file(output_file)

        video_list= []
        for start, end, base, vidname in segments:
            if not vidname in video_list:
                video_list.append(vidname)

        def input_map(x):
            return f'-hwaccel cuda -hwaccel_output_format cuda -c:v h264_cuvid -i {x}'

        input_term = ' '.join([input_map(x) for x in video_list])

        lines = []
        labels = []
        for sidx, (start, end, base, vidname) in enumerate(segments):
            index = video_list.index(vidname)
            vlabel = f'[v{sidx}]'
            alabel = f'[a{sidx}]'
            lines.append(f'[{index}:v]trim={start}:{end},setpts=PTS-STARTPTS{vlabel};')
            lines.append(f'[{index}:a]atrim={start}:{end},asetpts=PTS-STARTPTS{alabel};')
            labels.append(vlabel)
            labels.append(alabel)

        end_term = ''.join(labels)+f'concat=n={len(segments)}:v=1:a=1'
        lines.append(end_term)

        complex_filter = ''.join(lines)

        cmd = f'ffmpeg -y -vsync 0 {input_term} -filter_complex "{complex_filter}" -c:v h264_nvenc {output_file} -v quiet -stats'

        result = subprocess.check_output(cmd, shell=True)


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

        cmd = f'ffmpeg -y -vsync 0 -hwaccel cuda -hwaccel_output_format cuda -safe 0 -c:v h264_cuvid -f concat -i {list_path} -c:v h264_nvenc -af aresample=async=1000 {output_file} -v quiet -stats'

        result = subprocess.check_output(cmd, shell=True)

