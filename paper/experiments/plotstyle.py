"""Shared matplotlib style for the paper's figures (IEEE, print-safe).

Colours are the first three slots of the validated categorical palette
(they pass the all-pairs colour-vision checks); every series also gets its
own marker and line style so figures survive grayscale printing.
"""
import matplotlib

SERIES = ["#2a78d6", "#eb6834", "#1baf7a"]   # blue, orange, aqua
MARKERS = ["o", "s", "^"]
LINESTYLES = ["-", "--", ":"]
INK_1, INK_2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def apply_style():
    matplotlib.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"],
        "mathtext.fontset": "stix",
        "font.size": 7.5,
        "axes.titlesize": 8,
        "axes.labelsize": 7.5,
        "xtick.labelsize": 6.8,
        "ytick.labelsize": 6.8,
        "legend.fontsize": 6.5,
        "legend.frameon": False,
        "axes.edgecolor": INK_2,
        "axes.labelcolor": INK_1,
        "axes.titlecolor": INK_1,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.5,
        "axes.axisbelow": True,
        "lines.linewidth": 1.5,
        "pdf.fonttype": 42,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.02,
    })
