import os, sys
import struct
import enum

class ControlFlags(enum.Flag):
    dead = 128
    control = 64
    cutscene = 32
    transition = 16

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
        self.state = PlayerState(state)
        raw = raw[size:]

        input_state_fmt = '=BBff'
        size = struct.calcsize(input_state_fmt)
        (buttons, directions, self.xaim, self.yaim) = struct.unpack(input_state_fmt, raw[:size])
        self.button_flags = ButtonFlags(buttons)
        self.direction_flags = DirectionFlags(directions)
        raw = raw[size:]

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
                except Exception as e:
                    raise

        self.chapter = self.states[0].strings[0]
        self.map = self.states[0].strings[1]





