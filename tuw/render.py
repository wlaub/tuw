
from collections import defaultdict

from PIL import Image, ImageDraw

from . import tuw


class Bounds():
    def __init__(self):
        self.left = None
        self.right = None
        self.top = None
        self.bottom = None

    def update(self, xpos, ypos):
        if self.left is None or self.left > xpos:
            self.left = xpos
        if self.right is None or self.right < xpos:
            self.right = xpos

        if self.bottom is None or self.bottom > ypos:
            self.bottom = ypos
        if self.top is None or self.top < ypos:
            self.top = ypos

    def expand(self, value):
        self.left -= value
        self.right += value
        self.top += value
        self.bottom -= value


class Plotter():
    def __init__(self):
        self.bounds = Bounds()
        self.states = []
        self.images = defaultdict(self.new_image)
        self.spawn_points = []

    @staticmethod
    def _state_box(x):
        pos = (x.xpos-4, x.ypos)
        h = 11
        if tuw.StatusFlags.crouched in x.status_flags:
            h = 6
        if tuw.PlayerState.star_fly == x.state:
            h = 8
        return (*pos, 8, h)

    def new_image(self):
        result = Image.new('RGBA',
            (int(self.bounds.right), int(self.bounds.top)), color=(0,0,0,0))
        return result

    def add_run(self, run, _filter = lambda x: True):
        if _filter(run.states[0]):
            self.spawn_points.append(run.states[0])

        for state in run.states:
            if _filter(state):
                self.add_state(state)

    def add_state(self, state):
        self.states.append(state)
        self.bounds.update(state.xpos, state.ypos)

    def normalize(self):
        for state in self.states:
            state.xpos -= self.bounds.left
            state.ypos -= self.bounds.bottom

        self.bounds.right -= self.bounds.left
        self.bounds.top -= self.bounds.bottom
        self.bounds.left = 0
        self.bounds.bottom = 0


    def finalize(self):
        self.bounds.expand(32)

        self.normalize()

    def render(self, filename, show=False):

        for x in self.states:
            rect = self._state_box(x)
            rect = list(map(int, rect))
            im = Image.new('RGBA', rect[2:],
                color=(0,0,0,16))
            self.images[0].alpha_composite(im, dest=tuple(rect[:2]))


            if tuw.ControlFlags.dead in x.control_flags:
                im = Image.new('RGBA', rect[2:],
                    color=(255,0,0,128))
                self.images[1].alpha_composite(im, dest=tuple(rect[:2]))

        for state in self.spawn_points:
           rect = self._state_box(x)
           rect = list(map(int, rect))
           im = Image.new('RGBA', rect[2:],
                color=(0,0,255,255))
           self.images[2].alpha_composite(im, dest=tuple(rect[:2]))




        final = self.new_image()
        for layer, im in sorted(self.images.items()):
            final.alpha_composite(im)

        if show:
            final.show()
        final.save(filename, 'png')




