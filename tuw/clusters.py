
from collections import defaultdict

import sklearn.cluster as skcluster

from matplotlib import pyplot as plt

from . import tuw

class RunStats:
    def __init__(self, idx, run):
        self.idx = idx
        self.run = run
        self.point = self.get_point()

    def get_point(self):
        point = (self.run.get_length(),
                self.run.states[-1].xpos, self.run.states[-1].ypos,
                self.run.states[0].xpos, self.run.states[0].ypos)
        return point

    def ingest_cluster(self, clusters):
        self.label = clusters.labels_[self.idx]
        self.centroid = clusters.centroids_[self.label]
        self.dist = sum([(x-y)**2 for x,y in zip(self.point, self.centroid)])

class GroupClusters:
    def __init__(self, runs):
        self.runs = runs

        self.run_stats = []
        for idx, run in enumerate(runs):
            self.run_stats.append(RunStats(idx, run))

        points = [x.point for x in self.run_stats]
        self.clst = get_clusters(points)

        for stats in self.run_stats:
            stats.ingest_cluster(self.clst)

        self.stats_map = defaultdict(list)
        for stats in self.run_stats:
            self.stats_map[stats.label].append(stats)

        #labels by size
        label_map = defaultdict(list)
        for idx, label in enumerate(self.clst.labels_):
            label_map[label].append(points[idx])

        label_map.pop(-1, None)

        self.labels_by_size = sorted(label_map.items(), key=lambda x: len(x[1]), reverse=True)

    def get_best_runs(self, n, metric = lambda x: x.dist):
        #runs closest to each cluster centroid
        self.best_map = {}
        for label, stats in self.stats_map.items():
            best = min(stats, key=metric)
            self.best_map[label] = best

        self.best_runs_by_size = [self.best_map[label] for label, _ in self.labels_by_size]


        return [x.run for x in self.best_runs_by_size[:n]]


def get_points(runs):
    result = []
    for run in runs:
        point = (run.get_length(),
                run.states[-1].xpos, run.states[-1].ypos,
                run.states[0].xpos, run.states[0].ypos)
        result.append(point)

    return result


def get_clusters(points):
    hdb = skcluster.HDBSCAN(min_cluster_size=2, store_centers = 'centroid')
    hdb.fit(points)
    return hdb

