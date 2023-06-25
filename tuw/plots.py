
from collections import defaultdict

from matplotlib import pyplot as plt
from matplotlib import patches, ticker
from matplotlib.collections import PatchCollection

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


class Plotter():
    patch_kwargs = {
        'k': {
            'alpha': 0.01,
            'zorder': 2,
            },
        'r': {
            'alpha': 0.5,
            'zorder': 10
            },
        'b': {
            'alpha': 0.5,
            'zorder': 10
            },

        }
    default_kwargs = {
        'alpha' : 0.01,
        'zorder': 2,
        }

    def __init__(self):
        self.patches = defaultdict(list)
        self.bg_patches = defaultdict(list)
        self.fig, self.ax = plt.subplots(1,1)
        self.bounds = Bounds()

    @staticmethod
    def _state_box(x):
        pos = (x.xpos-4, -x.ypos)
        h = 11
        if tuw.StatusFlags.crouched in x.status_flags:
            h = 6
        if tuw.PlayerState.star_fly == x.state:
            h = 8
        return patches.Rectangle(pos, 8, h)

    def _add_point(self, x, c):
        patch = self._state_box(x)
        self.bounds.update(x.xpos, -x.ypos)
        self.patches[c].append(patch)

        pos = (x.xpos, -x.ypos+6)

        if x.state == tuw.PlayerState.red_dash:
            self.bg_patches['r'].append(patches.Circle(pos, 8))
        elif x.state == tuw.PlayerState.boost:
            self.bg_patches['g'].append(patches.Circle(pos, 8))
        elif x.state == tuw.PlayerState.star_fly:
            self.bg_patches['y'].append(patches.Circle(pos, 4))






    def plot(self, seq):
        x = seq.states[0]
        self._add_point(x, 'b')

        for x in seq.states[1:]:
            if not tuw.ControlFlags.dead in x.control_flags:
                self._add_point(x, 'k')
            else:
                self._add_point(x, 'r')


    def show(self):
        pcs = {}
        bg_pcs = {}
        for k, v in self.patches.items():
            pcs[k] = PatchCollection(v, facecolors=k,
                            linewidths=0,
                            **self.patch_kwargs.get(k, self.default_kwargs))

        for k,v in self.bg_patches.items():
            kwargs = dict(self.patch_kwargs.get(k, self.default_kwargs))
            kwargs['zorder'] = 1
            bg_pcs[k] = PatchCollection(v, facecolors=k,
                            linewidths=0, **kwargs)

        for k, v in pcs.items():
            self.ax.add_collection(v)
        for k, v in bg_pcs.items():
            self.ax.add_collection(v)


        self.ax.set_xlim(self.bounds.left, self.bounds.right)
        self.ax.set_ylim(self.bounds.bottom, self.bounds.top)

        self.ax.set_aspect('equal')
        self.ax.xaxis.set_major_locator(ticker.MultipleLocator(base=8))
        self.ax.yaxis.set_major_locator(ticker.MultipleLocator(base=8))
        self.ax.grid(True, which='major', axis='both')
        self.ax.set_axisbelow(True)

        plt.show()



