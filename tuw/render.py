
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

    def _rect(self, layer, rect, color):
        im = Image.new('RGBA',
            (int(rect[2]), int(rect[3])),
            color = color
            )
        self.images[layer].alpha_composite(im,
            dest = (int(rect[0]), int(rect[1]))
            )

    def _circle(self, layer, pos, radius, color):
        if len(pos) == 2:
            xpos, ypos = pos
        else:
            xpos = pos[0]+pos[2]/2
            ypos = pos[1]+pos[3]/2

        im = Image.new('RGBA',
            (int(xpos+2*radius), int(ypos+2*radius)),
            color = (0,0,0,0)
            )
        draw = ImageDraw.Draw(im)
        draw.ellipse((0,0,int(radius*2), int(radius*2)), fill=color)
        self.images[layer].alpha_composite(im,
            dest = (int(xpos-radius), int(ypos-radius))
            )


    def render(self, filename, show=False):

        for x in self.states:
            rect = self._state_box(x)

            self._rect(0, rect, (0,0,0,16))

            if tuw.ControlFlags.dead in x.control_flags:
                self._rect(10, rect, (255,0,0,128))


            if x.state == tuw.PlayerState.dash:
                self._circle(5, rect, 3, (0,255,0,8))
            elif x.state == tuw.PlayerState.dream_dash:
                self._circle(5, rect, 3, (255,255,255,4))
            elif x.state == tuw.PlayerState.red_dash:
                self._circle(-10, rect, 8, (200,0,0,32))
            elif x.state == tuw.PlayerState.boost:
                self._circle(-11, rect, 8, (0,128,32,32))
            elif x.state == tuw.PlayerState.star_fly:
                self._circle(-11, rect, 6, (255,255,0,32))




        for state in self.spawn_points:
            rect = self._state_box(state)
            self._rect(20, rect, (0,0,255,255))


        final = self.new_image()
        for layer, im in sorted(self.images.items()):
            final.alpha_composite(im)

        final.save(filename, 'png')
        if show:
            final.show()




