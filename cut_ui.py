import sys, os
import time

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

    def add_items_unique(self, items):
        values = self.get_list_values()
        for item in items:
            if len(item) > 0 and  not item in values:
                values.append(item)
        self.update(values)

class Layout():

    def __init__(self, app):
        self.app = app

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
]]
            )
        return result

    def get_output(self):
        result = sg.Column( expand_x = True,
            layout=[
[
sg.Input(key = 'outfile',
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
sg.Button('Add files', key='add_files', enable_events=True),
DListbox(key = 'infiles',
    values = self.app.infiles,
    size = (200, 3),
    select_mode = sg.LISTBOX_SELECT_MODE_SINGLE,
    enable_events = True,
    ),
]
            ])

        return result

    def get_layout(self):
        return [[self.get_inputs(), ], [self.get_config(), self.get_extract(), self.get_output()]]
        pass

TUW_OUTPUTS = os.path.expanduser('~/.local/share/Steam/steamapps/common/Celeste/tuw_outputs')
STAMP_FILE_PATH = '~/Videos/Streams'

class App():

    def __init__(self):
        self.infiles = []

        self.state_change_flags = 0xcf
        self.collection_flags = 0x7f
        self.numbers = [413, 420, 612, 720, 1025, 1337, 1413, 1612, 1420, 2012, 2020, 2600, 7859,]

        self.input_map = {}
        self.export_runs = []

        self.layout = Layout(self).get_layout()


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

    def extract(self):
        infiles = self.window['infiles'].get_list_values()
        self.export_runs = export_runs = []
        self.export_conditions = export_conditions = []
        self.export_counts = counts = defaultdict(lambda:0)
        unique_counts = defaultdict(lambda:0)

        total_runs = 0
        for infile in infiles:
            cut_input = self.input_map[infile]
            total_runs += len(cut_input.runs)
            _runs, _conds, _counts, _ucounts = cut_input.extract_runs(
                    numbers = self.numbers,
                    state_change = self.state_change_flags,
                    collection = self.collection_flags,
                    )
            for key, val in _counts.items():
                counts[key] += val
            for key, val in _ucounts.items():
                unique_counts[key] += val


            start_time = time.time()
            export_runs.extend(_runs)
            export_conditions.extend(_conds)
            end_time = time.time()

        rows = []
        rows.append(['Total Runs', len(export_runs), total_runs])
        for key, val in counts.items():
            rows.append([key, val, unique_counts[key]])

        self.window['extract_counts'].update(rows)

    def do_cut(self):
        out_file = self.window['outfile'].get()
        if not out_file.endswith('.mp4'):
            print(f'Invalid output filename {out_file}')
            return

        if len(self.export_runs) == 0:
            print(f'Nothing to export')
            return

        try:
            clipper = tuw.cut_util.Clipper(STAMP_FILE_PATH)
            segments = clipper.compute_clips(self.export_runs)
            clipper.export_moviepy(segments, out_file)
        except Exception as e:
            print(f'Export failed: {e}')

    def update_inputs(self):
        for infile in self.window['infiles'].get_list_values():
            if not infile in self.input_map.keys():
                try:
                    self.input_map[infile] = tuw.cut_util.CutInput(infile)
                except Exception as e:
                    print(f"Couldn't load {infile}: {e}")
        self.extract()

    def add_files(self):
        files = tkfb.askopenfilenames(initialdir = TUW_OUTPUTS, parent=self.window.TKroot, filetypes=[("*.dump", "*.dump"), ("All files","")])
        if len(files) == 0:
            return
        self.window['infiles'].add_items_unique(files)

        self.update_inputs()

    def run(self):
        self.window = window = sg.Window("cut_ui", self.layout, location=(0,0))
        self.window.Finalize()

        for key in ['infiles']:
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
            elif event == 'numbers':
                self.deserialize_numbers()
            elif event == 'do_cut':
                self.do_cut()

        window.close()

sg.theme('SystemDefault 1')

app = App()

app.run()

