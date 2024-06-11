import os, sys
import struct
import enum

class ControlFlags(enum.Flag):
    dead = 128
    control = 64
    cutscene = 32
    transition = 16
    paused = 8

class StatusFlags(enum.Flag):
    holding = 128
    crouched = 64
    facing_left = 32
    wall_left = 16
    wall_right = 8
    coyote = 4
    safe_ground = 2
    ground = 1

class ButtonFlags(enum.Flag):
    quick_restart = 128
    pause = 64
    escape = 32
    crouch_dash = 16
    talk = 8
    grab = 4
    dash = 2
    jump = 1

class DirectionFlags(enum.Flag):
    up = 8
    down = 4
    left = 2
    right = 1

class CollectionFlags(enum.Flag):
    follower = 128
    UNUSED = 64
    heart = 32
    tape = 16
    key_lost = 8
    key = 4
    seeds = 2
    berry = 1

class StateChangeFlags(enum.Flag):
    clutter_switch = 128
    textbox = 64
    spawn = 32
    flag = 16
    fake_wall = 8
    cutscene = 4
    dash_block = 2
    respawn_change = 1

class PlayerState(enum.Enum):
    normal = 0
    climb = 1
    dash = 2
    swim = 3
    boost = 4 #green bubble
    red_dash = 5 #red bubble
    hit_squash = 6
    launch = 7
    pickup = 8
    dream_dash = 9
    summit_launch = 10
    dummy = 11
    intro_walk = 12
    intro_jump = 13
    intro_respawn = 14
    intro_wake_up = 15
    bird_dash_tutorial = 16
    frozen = 17
    reflection_fall = 18
    star_fly = 19
    temple_fall = 20
    cassette_fly = 21
    attract = 22

class GameState():
    __slots__ = (
        'sequence',
        'timestamp',
        'time',
        'deaths',
        'room',
        'xpos', 'ypos',
        'xvel', 'yvel',
        'stamina', 'xlift', 'ylift',
        'state',
        'dashes',
        'control_flags', 'status_flags',
        'button_flags', 'direction_flags',
        'xaim', 'yaim',
        'collection_flags', 'state_change_flags',
        'strings',
        )
    def __init__(self, raw):
        self.sequence, self.timestamp, self.time, self.deaths = struct.unpack('=Idqi', raw[:24])
        raw = raw[24:]

        room, raw = raw.split(b'\x00', maxsplit=1)
        self.room = room.decode('ascii')

        player_state_fmt = '=fffffffiiBB'
        size = struct.calcsize(player_state_fmt)
        (   self.xpos, self.ypos, self.xvel, self.yvel,
            self.stamina, self.xlift, self.ylift,
            state, self.dashes, control, status) = struct.unpack(player_state_fmt, raw[:size])
        self.control_flags = ControlFlags(control)
        self.status_flags = StatusFlags(status)
        try:
            self.state = PlayerState(state)
        except ValueError:
            self.state = state
        raw = raw[size:]

        input_state_fmt = '=BBff'
        size = struct.calcsize(input_state_fmt)
        (buttons, directions, self.xaim, self.yaim) = struct.unpack(input_state_fmt, raw[:size])
        self.button_flags = ButtonFlags(buttons)
        self.direction_flags = DirectionFlags(directions)
        raw = raw[size:]

        if len(raw) > 0 and raw[0] == 1:
            size = int(raw[1])
            raw = raw[2:]
            self.collection_flags = CollectionFlags(int(raw[0]))
            self.state_change_flags = StateChangeFlags(int(raw[1]))
            raw = raw[size:]
        else:
            self.collection_flags = CollectionFlags(0)
            self.state_change_flags = StateChangeFlags(0)

        self.strings = [x.decode('ascii') for x in raw.split(b'\x00')][:-1]

class StateDump():
    def __init__(self, filename):
        self.states = []
        self.rooms = set()
        with open(filename, 'rb') as fp:
            while True:
                try:
                    size_raw = fp.read(2)
                    if len(size_raw) == 0:
                        break

                    size = struct.unpack('=H', size_raw)[0]

                    raw = fp.read(size)
                    state = GameState(raw)
                    self.states.append(state)

                    self.rooms.add(state.room)
                except struct.error as e:
                    print(f'malformed packet? {e}')
                    pass
                except Exception as e:
                    raise

        self.chapter = self.states[0].strings[0]
        self.map = self.states[0].strings[1]

    def extract_sequences(self, SequenceClass):
        result = []
        seq = SequenceClass()
        for state in self.states:
            seq.add_state(state)
            if seq.done:
                if seq.valid():
                    result.append(seq)
                seq = SequenceClass()

        if (len(result) == 0 or result[-1] != seq) and seq.valid():
            result.append(seq)

        return result

class StateSequence():
    """
    A sequence of states with logic for segmenting and validation. Pass as an
    argument to StateDump.extract_sequences to get a list of StateSequences.

    add_state takes a state, adds it if appropriate, and updates self.done if
    it terminates the sequence.

    valid() returns False if the sequence is not valid and should be discarded
    """

    def __init__(self):
        self.states = []
        self.done = False

        self.rooms = set()
        self.room_order = []
        self.control_flags = ControlFlags(0)
        self.collection_flags = CollectionFlags(0)
        self.state_change_flags = StateChangeFlags(0)

        self.length = None

    def valid(self):
        raise NotImplementedError

    def add_state(self, state):
        raise NotImplementedError

    def _add_state(self, state):
        self.states.append(state)
        self.rooms.add(state.room)
        if len(self.room_order) == 0 or self.room_order[-1] != state.room:
            self.room_order.append(state.room)
        self.control_flags |= state.control_flags
        self.collection_flags |= state.collection_flags
        self.state_change_flags |= state.state_change_flags

    def get_duration(self):
        return self.states[-1].timestamp - self.states[0].timestamp

    def get_length(self):
        if self.length is not None: return self.length

        self.length = 0
        for a,b in zip(self.states[:-1], self.states[1:]):
            self.length += (a.xpos-b.xpos)**2 + (a.ypos-b.ypos)**2

        return self.length

    def plot(self, ax):
        xvals = []
        yvals = []
        for x in self.states:
            xvals.append(x.xpos)
            yvals.append(-x.ypos)

        from matplotlib import patches
        from matplotlib.collections import PatchCollection
        rects = []
        for x in self.states:
            rect = patches.Rectangle((x.xpos-4, -x.ypos), 8,8)
            rects.append(rect)
        pc = PatchCollection(rects, facecolor='k', alpha=0.01)
        ax.add_collection(pc)

        ax.scatter(xvals, yvals, s=1, c='k', alpha=0)


class Run(StateSequence):
    """
    A run is a state sequence terminated by a death and having length of
    at least 2 states.
    """
    def __init__(self):
        super().__init__()

    def valid(self):
        return len(self.states) > 1

    def add_state(self, state):
        if self.done: return

        if ControlFlags.dead in state.control_flags:
            self.done = True

        self._add_state(state)

class RoomRun(Run):

    def add_state(self, state):
        if len(self.rooms) > 0 and not state.room in self.rooms:
            self.done = True
        elif len(self.states) > 0 and self.states[-1].deaths != state.deaths:
            self.done = True
            self.control_flags |= ControlFlags.dead
        else:
            super().add_state(state)

class RoomCompleteRun(RoomRun):

    def valid(self):
        return super().valid() and not ControlFlags.dead in self.control_flags


