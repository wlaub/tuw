import sys, os
import time

from collections import defaultdict

import moviepy.editor


numbers = {413, 420, 612, 720, 1025, 1337, 1413, 1612, 1420, 2012, 2020, 2600, 7859,
#1094,1097,1100,1102,1112,
#1530,
}


import tuw
import tuw.clusters
import tuw.cut_util

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


export_runs = []
export_conditions = []
counts = defaultdict(lambda:0)

extract_config = {
    'numbers': numbers,
    'state_change': 0xcf,
    'collection': 0x7f,
}

for infile in infiles:

    cut_input =tuw.cut_util.CutInput(infile)
    _runs, _conds, _counts = cut_input.extract_runs(**extract_config)
    for key, val in _counts.items():
        counts[key] += val

    export_runs.extend(_runs)
    export_conditions.extend(_conds)

for key, val in counts.items():
    print(f'{key}: {val} runs')

print(f'{len(export_runs)=}')

#exit()

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

