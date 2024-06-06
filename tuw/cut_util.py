import time
from collections import defaultdict

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
        for idx, run in enumerate(runs):
            conditions = set()
            cluster = self.cluster_map.get(run, None)
            if len(run.rooms) >1 or idx == 0 or idx == len(runs)-1:
                conditions.add('room_change')
            elif run.state_change_flags.value & state_change:
                conditions.add('state change')
        #        print(run.state_change_flags)
            elif run.collection_flags.value & collection:
                conditions.add('collection')
        #        print(run.collection_flags)
            elif idx < len(runs)-1 and not run.match_spawn(runs[idx+1]):
                conditions.add('spawn change next')
            elif idx > 0 and not run.match_spawn(runs[idx-1]) and not (run.state_change_flags.value&0x01 == 0):
                conditions.add('spawn change prev')
            elif run in self.cluster_runs and False:
                conditions.add('cluster')
        #        print(f'{idx}: from cluster')
            elif run in self.longest_fails:
                conditions.add('long fail')
        #        print(f'{idx}: from longest fails')
            elif run.states[0].deaths in numbers:
                conditions.add('numbers')

            if len(conditions) > 0:
                extant_clusters.add(cluster)
                export_conditions.append(conditions)
                for cond in conditions:
                    counts[cond] += 1
                export_runs.append((idx, run))

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
                export_runs.append((idx, run))

        export_runs = sorted(export_runs, key=lambda x: x[0])
        indices, export_runs = list(zip(*export_runs))

#        for key, val in counts.items():
#            print(f'{key}: {val} runs')

#        print(f'{len(export_runs)=}')

        return export_runs, export_conditions, counts
