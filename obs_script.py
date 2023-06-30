import time
import mmap
import struct
import platform
import obspython as obs

class Handler():
    def __init__(self):
        self.fp = None
        self.last_sequence = None

    def open(self):
        if self.fp is not None:
            return

        if platform.system() == 'Linux':
            self.fx = open('/tmp/celeste_tuw.share', 'r+b')
            self.fp = mmap.mmap(self.fx.fileno(), 0)
        else:
            self.fp = mmap.mmap('celeste_tuw', 0)

    def close(self):
        self.fp.close()
        if platform.system() == 'Linux':
            self.fx.close()
        self.fp = None

    def read(self):

        self.fp.seek(0)
        size_raw = self.fp.read(2)
        size = struct.unpack('=H', size_raw)[0]

        if size == 0:
            return None

        raw = self.fp.read(size)

        sequence, timestamp, gametime, deaths = struct.unpack('=Idqi', raw[:24])
        raw = raw[24:]

        if sequence == self.last_sequence:
            return None

        self.last_sequence = sequence

        room, raw = raw.split(b'\x00', maxsplit=1)
        room = room.decode('ascii')

        player_state_fmt = '=fffffffiiBB'
        size = struct.calcsize(player_state_fmt)
        player_state = struct.unpack(player_state_fmt, raw[:size])
        raw = raw[size:]
        (xpos, ypos, xvel, yvel, samina, xlift, ylift, state, dashes, control, status) = player_state

        input_state_fmt = '=BBff'
        size = struct.calcsize(input_state_fmt)
        input_state = struct.unpack(input_state_fmt, raw[:size])
        raw = raw[size:]

        if len(raw) > 0 and raw[0] == 1:
            size = int(raw[1])
            raw = raw[2:]
            collection_flags = int(raw[0])
            state_change_flags = int(raw[1])
            raw = raw[size:]

        strings = [x.decode('ascii') for x in raw.split(b'\x00')]

        lines = [
            str(deaths),
            strings[1], strings[0]
            ]

        return '\n'.join(lines)


handler = Handler()

def script_unload():
    print('Unloading')
    obs.timer_remove(do_tick)
    handler.close()
    set_message('')

def script_load(settings):
    obs.timer_add(do_tick, 50)
    set_message('')
    handler.open()

def script_description():
    return 'A script.'

def set_message(message):
    source = obs.obs_get_source_by_name('Status Text')
    settings = obs.obs_source_get_settings(source)
    try:
        obs.obs_data_set_string(settings, 'text', message)
    except Exception as e:
        print(e)
    obs.obs_source_update(source, settings)
    obs.obs_data_release(settings)
    obs.obs_source_release(source)


def do_tick():
    handler.open()

    message = handler.read()
    if message is None: return

    set_message(message)

