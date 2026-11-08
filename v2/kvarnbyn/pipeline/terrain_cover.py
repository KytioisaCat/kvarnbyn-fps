"""First rock/vegetation pass; appearance only, never changes LiDAR heights.

The broad envelopes locate Lilla Glasberget and Glasberget, not surveyed
outcrop boundaries. Joel's description + local references justify exposed rock
with wooded ledges. Raw slope and land cover still control each envelope.
"""
import numpy as np


def smoothstep(a, b, value):
    t = np.clip((value - a) / (b - a), 0., 1.)
    return t * t * (3. - 2. * t)


def exposure(x, z, slope, land):
    x, z = np.asarray(x), np.asarray(z)
    # Broad, continuous patches: no random tile/checkerboard classification.
    lilla = 1. - smoothstep(.65, 1.1, np.hypot((x - 242.) / 83., (z - 155.) / 74.))
    glas = 1. - smoothstep(.65, 1.1, np.hypot((x - 650.) / 270., (z - 555.) / 220.))
    # Joels clarification: the steep face seen across the villas from the
    # upper Görjelycksgatan spawn. It is NW of the larger backdrop envelope.
    glas_front = 1. - smoothstep(.6, 1.1, np.hypot((x - 490.) / 130., (z - 260.) / 135.))
    envelope = np.maximum.reduce([lilla, glas, glas_front])
    patches = .5 + .25 * np.sin(x * .067 + z * .031) + .25 * np.sin(x * .029 - z * .083)
    slabs = envelope * smoothstep(.08, .55, slope) * (.45 + .55 * patches)
    cliffs = smoothstep(.55, 1.15, slope)
    # Classified urban ground must not become a cliff simply from road grading.
    natural = 1. - smoothstep(.25, .65, land[:, 0])
    return np.clip(np.maximum.reduce([land[:, 3], cliffs, slabs]) * natural, 0., 1.)
