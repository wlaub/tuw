import sys, os
import time

from collections import defaultdict

import moviepy.editor

import tuw
import tuw.cut_util

####
# Load run files
####

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

inputs = []
for infile in infiles:

    cut_input =tuw.cut_util.CutInput(infile)
    inputs.append(cut_input)

####
# Extract runs
####

numbers = {413, 420, 612, 720, 1025, 1337, 1413, 1612, 1420, 2012, 2020, 2600, 7859,
#1094,1097,1100,1102,1112,
#1530,
}

extract_config = {
    'numbers': numbers,
    'state_change': 0xcf,
    'collection': 0x7f,
}

export_runs = []
counts = defaultdict(lambda:0)

for cut_input in inputs:
    _runs, _counts, _ = cut_input.extract_runs(**extract_config)
    for key, val in _counts.items():
        counts[key] += val

    start_time = time.time()
    export_runs.extend(_runs)
    end_time = time.time()

for key, val in counts.items():
    print(f'{key}: {val} runs')

export_runs = [x.run for x in export_runs]

print(f'{len(export_runs)=}')

####
# Generate video
####

clipper = tuw.cut_util.Clipper('~/Videos/Streams')
segments = clipper.compute_clips(export_runs)
clipper.export_moviepy(segments, output_file)

exit(0)

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

