"""Colour arithmetic the likeness fit and check share, in numpy alone: sRGB to linear and back, linear RGB to CIE Lab
(D65 white, the CIE's own constants) and back.

    linear(srgb)       srgb(linear)       lab(linear)       linear_of_lab(lab)

Arrays of any shape whose last axis is the three channels, values 0..1 (Lab: L 0..100).
"""
import numpy as np

# sRGB's primaries to CIE XYZ under D65 (IEC 61966-2-1), and the D65 white.
TO_XYZ = np.array([[0.4124564, 0.3575761, 0.1804375],
                   [0.2126729, 0.7151522, 0.0721750],
                   [0.0193339, 0.1191920, 0.9503041]])
WHITE = TO_XYZ.sum(axis=1)
# CIE Lab's break between its cube root and its linear toe.
EPSILON = 216.0 / 24389.0
KAPPA = 24389.0 / 27.0


def linear(srgb):
    """sRGB-encoded values as linear light."""
    srgb = np.asarray(srgb, dtype=float)
    return np.where(srgb <= 0.04045, srgb / 12.92, ((srgb + 0.055) / 1.055) ** 2.4)


def srgb(light):
    """Linear light as sRGB-encoded values, clipped to 0..1."""
    light = np.clip(np.asarray(light, dtype=float), 0.0, 1.0)
    return np.where(light <= 0.0031308, light * 12.92, 1.055 * light ** (1 / 2.4) - 0.055)


def lab(light):
    """Linear RGB as CIE Lab."""
    ratio = (np.asarray(light, dtype=float) @ TO_XYZ.T) / WHITE
    bent = np.where(ratio > EPSILON, np.cbrt(ratio), (KAPPA * ratio + 16.0) / 116.0)
    return np.stack([116.0 * bent[..., 1] - 16.0, 500.0 * (bent[..., 0] - bent[..., 1]),
                     200.0 * (bent[..., 1] - bent[..., 2])], -1)


def linear_of_lab(values):
    """CIE Lab as linear RGB, clipped to 0..1."""
    values = np.asarray(values, dtype=float)
    middle = (values[..., 0] + 16.0) / 116.0
    bent = np.stack([middle + values[..., 1] / 500.0, middle, middle - values[..., 2] / 200.0], -1)
    ratio = np.where(bent ** 3 > EPSILON, bent ** 3, (116.0 * bent - 16.0) / KAPPA)
    return np.clip((ratio * WHITE) @ np.linalg.inv(TO_XYZ).T, 0.0, 1.0)
