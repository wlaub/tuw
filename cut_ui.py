import sys, os
import time

os.environ['FFMPEG_BINARY'] = 'ffmpeg'

from collections import defaultdict

import moviepy.editor

import FreeSimpleGUI as sg
import tkinter as fk
import tkfilebrowser as tkfb

import tuw
import tuw.cut_util




class ValidMixin():

    def set_valid(self, valid):
        self.valid = valid
        if not valid:
            self.BackgroundColor = '#ffcccc'
        else:
            self.BackgroundColor = 'white'
        self.Widget.configure(background=self.BackgroundColor)

class DListbox(sg.Listbox, ValidMixin):

    def setup(self):
        self.bind('<Delete>', '+listbox_delete')
        self.bind('<Up>', '+listbox_up')
        self.bind('<Down>', '+listbox_down')

    def delete_selection(self):
        values = self.get_list_values()
        remove = self.get()
        for item in remove: values.remove(item)
        self.update(values)

    def move_selection(self, amt):
        values = self.get_list_values()
        selection = self.get()
        for move in selection:
            idx = values.index(move)
            if amt < 0:
                if idx == 0:
                    return
                new_idx = max(idx+amt,0)
                values.remove(move)
                values.insert(new_idx, move)
            elif amt > 0:
                if idx == len(values)-1:
                    return
                new_idx = min(idx+amt+1, len(values))
                values.insert(new_idx, move)
                values.remove(move)

        selection_indices = [values.index(x) for x in selection]
        self.update(values, set_to_index=selection_indices)

    def scroll_selection(self, amt):
        values = self.get_list_values()
        def _inc(x):
            x+= amt
            if x < 0:
                x = 0
            if x >= len(values):
                x = len(values) - 1
            return x
        indices = [_inc(x) for x in self.get_indexes()]
        self.update(values, set_to_index = indices, scroll_to_index = indices[0]-7)

    def add_items_unique(self, items):
        values = self.get_list_values()
        for item in items:
            if len(item) > 0 and  not item in values:
                values.append(item)
        self.update(values)

class Layout():

    def __init__(self, app):
        self.app = app
        self.max_width = 150


    def get_config(self):
        result = sg.Column(
layout = [[
    sg.Multiline(
        default_text = self.app.serialize_numbers(),
        size = (21,10),
        expand_y = True,
        key = 'numbers',
        enable_events = True,
        ),
    sg.Column(
        layout=[[sg.Checkbox(x.name,
                default = x.value&self.app.state_change_flags,
                key = f'state_change_flags+{x.value}',
                enable_events = True,
                )]
    for x in tuw.StateChangeFlags]
    ),
    sg.Column(
        layout=[[sg.Checkbox(x.name,
                default = x.value&self.app.collection_flags,
                key = f'collection_flags+{x.value}',
                enable_events = True,
                )]
    for x in tuw.CollectionFlags]
    ),
    sg.Column(
        layout=[[sg.Checkbox(k,
                default = v,
                key = f'condition_flags+{k}',
                enable_events = True,
                )]
    for k,v in self.app.conditions.items()]
    ),


]]
            )
        return result

    def get_extract(self):
        result = sg.Column(
layout = [[
    sg.Table(
        values = [],
        headings = ['Condition', '#', '*'],
        cols_justification = ['r','l','l'],
        auto_size_columns = False,
        num_rows = 13,
        col_widths = [17,5,5],
        expand_y = True,
        key = 'extract_counts',
        ),
    DListbox(
        values = [],
        size = (8,10),
        expand_y = True,
        key = 'selected_runs',
        select_mode = sg.LISTBOX_SELECT_MODE_SINGLE,
        enable_events = True,
        ),
    sg.Text(
        key = 'run_detail',
        size = (40,10),
        expand_y = True,
        )
]]
            )
        return result

    def get_output(self):
        result = sg.Column( expand_x = True,
            layout=[
[
sg.Input(key = 'outfile',
    default_text = "_.mp4",
    size = (40, 3),
    enable_events = True,
    ),
sg.Button('Go', key='do_cut', enable_events=True),
]
            ])
        return result

    def get_inputs(self):
        result = sg.Column( expand_x = True,
            layout=[
[
sg.Column(layout=[
    [sg.Button('Add files', key='add_files', enable_events=True)],
    [sg.Button('Sort', key='sort_files', enable_events=True)],
]
),
DListbox(key = 'infiles',
    values = self.app.infiles,
    size = (self.max_width, 7),
    select_mode = sg.LISTBOX_SELECT_MODE_SINGLE,
    enable_events = True,
    ),
]
            ])

        return result

    def get_clusters(self):
        result = sg.Column(
layout = [[
    DListbox(
        values = [],
        size = (8,17),
        expand_y = True,
        key = 'cluster_rooms',
        select_mode = sg.LISTBOX_SELECT_MODE_SINGLE,
        enable_events = True,
        ),
    DListbox(
        values = [],
        size = (8,10),
        expand_y = True,
        key = 'room_clusters',
        select_mode = sg.LISTBOX_SELECT_MODE_SINGLE,
        enable_events = True,
        ),
    sg.Text(
        key = 'cluster_detail',
        size = (24,10),
        expand_y = True,
        ),
    DListbox(
        values = [],
        size = (8,10),
        expand_y = True,
        key = 'cluster_runs',
        select_mode = sg.LISTBOX_SELECT_MODE_SINGLE,
        enable_events = True,
        ),

]]
            )
        return result



    def get_layout(self):
        return [[self.get_inputs(), ],
                [self.get_config(), self.get_extract(),],
                [self.get_clusters()],
                [self.get_output()],
#                [sg.Output(size=(self.max_width, 10), expand_x=True, echo_stdout_stderr=True)],
                ]
        pass

TUW_OUTPUTS = os.path.expanduser('~/.local/share/Steam/steamapps/common/Celeste/tuw_outputs')
STAMP_FILE_PATH = '~/Videos/Streams'

class App():

    def __init__(self):
        self.infiles = []

        self.state_change_flags = 0xcf
        self.collection_flags = 0x7f
        self.numbers = [413, 420, 612, 720, 1025, 1337, 1413, 1612, 1420, 2012, 2020, 2600, 7859,]

        self.conditions = {
            'room_change': True,
            'state_change': True,
            'collection': True,
            'spawn_change': True,
            'clusters': True,
            'long_fail': True,
            }

        self.input_map = {}
        self.export_runs = []

        self.layout = Layout(self).get_layout()

        self.cluster_room_list = []
        self.cluster_room_selection = None
        self.cluster_run_list = []
        self.cluster_run_selection = None


    def serialize_numbers(self):
        return ', '.join(str(x) for x in self.numbers)

    def deserialize_numbers(self):
        raw = self.window['numbers'].get()
        try:
            self.numbers = [int(x.strip()) for x in raw.split(',')]
        except Exception as e:
            pass
        else:
            self.extract()

    def update_run_detail(self):
        idx = self.window['selected_runs'].get_indexes()
        if len(idx) == 0:
            self.window['run_detail'].update('Run Details:')

        idx = idx[0]
        run = self.export_runs[idx]

        text = f'Run Details:\n{run.format()}'

        self.window['run_detail'].update(text)

    def extract(self):
        infiles = self.window['infiles'].get_list_values()
        self.export_runs = export_runs = []
        self.export_counts = counts = defaultdict(lambda:0)
        unique_counts = defaultdict(lambda:0)

        total_runs = 0
        for infile in infiles:
            cut_input = self.input_map[infile]
            total_runs += len(cut_input.runs)
            _runs, _counts, _ucounts = cut_input.extract_runs(
                    numbers = self.numbers,
                    state_change_flags = self.state_change_flags,
                    collection_flags = self.collection_flags,
                    **self.conditions
                    )
            for key, val in _counts.items():
                counts[key] += val
            for key, val in _ucounts.items():
                unique_counts[key] += val


            start_time = time.time()
            export_runs.extend(_runs)
            end_time = time.time()

        rows = []
        rows.append(['Total Runs', len(export_runs), total_runs])
        for key, val in sorted(counts.items()):
            rows.append([key, val, unique_counts[key]])

        self.window['extract_counts'].update(rows)

        self.window['selected_runs'].update([x.death_count for x in export_runs])

    def update_cluster_rooms(self):
        self.cluster_room_list = []
        for _, cut_input in self.input_map.items():
            input_cms = cut_input.room_to_clusters.items()
            self.cluster_room_list.extend(input_cms)

        if len(self.cluster_room_list) == 0:
            room_options = []
        else:
            room_options, _ = zip(*self.cluster_room_list)
        self.window['cluster_rooms'].update(room_options)

    def update_cluster_room_selection(self):
        room = self.window['cluster_rooms'].get_indexes()
        if len(room) == 0: return
        room_idx = room[0]

        if room_idx == self.cluster_room_selection:
            return

        self.cluster_room_selection = room_idx
        cm = self.cluster_room_list[room_idx][1]

        values = list(x[0] for x in cm.clusters_by_size)
        self.window['room_clusters'].update(values)

    def update_cluster_selection(self):
        label = self.window['room_clusters'].get()
        if len(label) == 0: return
        label = label[0]

        cm = self.cluster_room_list[self.cluster_room_selection][1]

        runs = cm.cluster_to_runs[label]

        self.cluster_run_list = runs
        self.window['cluster_runs'].update([x.states[0].deaths for x in runs])

        centroid = cm.grp.clst.centroids_[label]
        def fmt_centroid(x):
            return [
                f'Length: {x[0]:.0f} px',
                f'Start: {x[1]:.1f}, {x[2]:.1f}',
                f'End: {x[3]:.1f}, {x[4]:.1f}'
                ]


        lines = []
        lines.append(f'{len(runs)} runs')
        lines.extend(fmt_centroid(centroid))

        text = '\n'.join(lines)
        self.window['cluster_detail'].update(text)


    def do_cut(self):
        out_file = self.window['outfile'].get()
        if not out_file.endswith('.mp4'):
            print(f'Invalid output filename {out_file}')
            return

        if len(self.export_runs) == 0:
            print(f'Nothing to export')
            return

        runs = [x.run for x in self.export_runs]

        try:
            start_time = time.time()
            clipper = tuw.cut_util.Clipper(STAMP_FILE_PATH)
            segments = clipper.compute_clips(runs)
            clipper.export_moviepy(segments, out_file)
            duration = time.time()-start_time
            print(f'Finished in {duration:.1f} s')
        except Exception as e:
            print(f'Export failed: {e}')

    def sort_files(self, files):
        times = [os.path.getctime(x) for x in files]
        files = list(sorted(zip(times, files)))
        _, files = list(zip(*files))
        return files

    def update_inputs(self):
        for infile in self.window['infiles'].get_list_values():
            if not infile in self.input_map.keys():
                try:
                    self.input_map[infile] = tuw.cut_util.CutInput(infile)
                except Exception as e:
                    print(f"Couldn't load {infile}: {e}")
        self.extract()
        self.update_cluster_rooms()

    def sort_inputs(self):
        files = self.window['infiles'].get_list_values()
        if len(files) == 0:
            return
        files = self.sort_files(files)
        self.window['infiles'].update(files)
        self.extract()

    def add_files(self):
        files = tkfb.askopenfilenames(initialdir = TUW_OUTPUTS, parent=self.window.TKroot, filetypes=[("*.dump", "*.dump"), ("All files","")])
        if len(files) == 0:
            return
        files = self.sort_files(files)
        self.window['infiles'].add_items_unique(files)

        self.update_inputs()

    def run(self):
        self.window = window = sg.Window("cut_ui", self.layout, location=(0,0))
        self.window.Finalize()

        for key in ['infiles', 'selected_runs']:
            self.window[key].setup()

        while True:
            event, values = window.read()
            base_event = event
            args = []
            if event != None:
                event, *args = event.split('+')
            print(event, args)

            if event == sg.WIN_CLOSED or event == 'Exit':
                break
            elif event == 'infiles':
                if 'listbox_delete' in args:
                    self.window[event].delete_selection()
                if 'listbox_up' in args:
                    self.window[event].move_selection(-1)
                if 'listbox_down' in args:
                    self.window[event].move_selection(1)
                self.extract()
            elif event == 'add_files':
                self.add_files()
            elif event == 'state_change_flags':
                mask = int(args[0])
                if self.window[base_event].get():
                    self.state_change_flags |= mask
                else:
                    self.state_change_flags &= ~mask
                self.extract()
            elif event == 'collection_flags':
                mask = int(args[0])
                if self.window[base_event].get():
                    self.collection_flags |= mask
                else:
                    self.collection_flags &= ~mask
                self.extract()
            elif event == 'condition_flags':
                self.conditions[args[0]] = self.window[base_event].get()
                self.extract()
            elif event == 'numbers':
                self.deserialize_numbers()
            elif event == 'do_cut':
                self.do_cut()
            elif event == 'sort_files':
                self.sort_inputs()
            elif event == 'selected_runs':
                if 'listbox_up' in args:
                    self.window[event].scroll_selection(-1)
                if 'listbox_down' in args:
                    self.window[event].scroll_selection(1)
                self.update_run_detail()
            elif event == 'room_clusters':
                self.update_cluster_selection()
            elif event == 'cluster_rooms':
                self.update_cluster_room_selection()


        window.close()

sg.theme('SystemDefault 1')

app = App()

app.run()


