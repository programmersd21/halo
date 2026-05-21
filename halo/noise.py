"""Vectorized 3D Perlin Noise Engine."""

from typing import Any

import numpy as np

# Ken Perlin's canonical 256-entry seed, doubled to 512 for direct indexing.
_PERM_BASE = np.array(
    [
        151,
        160,
        137,
        91,
        90,
        15,
        131,
        13,
        201,
        95,
        96,
        53,
        194,
        233,
        7,
        225,
        140,
        36,
        103,
        30,
        69,
        142,
        8,
        99,
        37,
        240,
        21,
        10,
        23,
        190,
        6,
        148,
        247,
        120,
        234,
        75,
        0,
        26,
        197,
        62,
        94,
        252,
        219,
        203,
        117,
        35,
        11,
        32,
        57,
        177,
        33,
        88,
        237,
        149,
        56,
        87,
        174,
        20,
        125,
        136,
        171,
        168,
        68,
        175,
        74,
        165,
        71,
        134,
        139,
        48,
        27,
        166,
        77,
        146,
        158,
        231,
        83,
        111,
        229,
        122,
        60,
        211,
        133,
        230,
        220,
        105,
        92,
        41,
        55,
        46,
        245,
        40,
        244,
        102,
        143,
        54,
        65,
        25,
        63,
        161,
        1,
        216,
        80,
        73,
        209,
        76,
        132,
        187,
        208,
        89,
        18,
        169,
        200,
        196,
        135,
        130,
        116,
        188,
        159,
        86,
        164,
        100,
        109,
        198,
        173,
        186,
        3,
        64,
        52,
        217,
        226,
        250,
        124,
        123,
        5,
        202,
        38,
        147,
        118,
        126,
        255,
        82,
        85,
        212,
        207,
        206,
        59,
        227,
        47,
        16,
        58,
        17,
        182,
        189,
        28,
        42,
        223,
        183,
        170,
        213,
        119,
        248,
        152,
        2,
        44,
        154,
        163,
        70,
        221,
        153,
        101,
        155,
        167,
        43,
        172,
        9,
        129,
        22,
        39,
        253,
        19,
        98,
        108,
        110,
        79,
        113,
        224,
        232,
        178,
        185,
        112,
        104,
        218,
        246,
        97,
        228,
        251,
        34,
        242,
        193,
        238,
        210,
        144,
        12,
        191,
        179,
        162,
        241,
        81,
        51,
        145,
        235,
        249,
        14,
        239,
        107,
        49,
        192,
        214,
        31,
        181,
        199,
        106,
        157,
        184,
        84,
        204,
        176,
        115,
        121,
        50,
        45,
        127,
        4,
        150,
        254,
        138,
        236,
        205,
        93,
        222,
        114,
        67,
        29,
        24,
        72,
        243,
        141,
        128,
        195,
        78,
        66,
        215,
        61,
        156,
        180,
    ],
    dtype=np.int32,
)

_PERM = np.concatenate([_PERM_BASE, _PERM_BASE]).astype(np.int32)


def _fade(t: Any) -> Any:
    """Ken Perlin's quintic smoothstep (C2 continuous)."""
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _lerp(a: Any, b: Any, t: Any) -> Any:
    """Linear interpolation."""
    return a + t * (b - a)


def _grad3d(
    hash_val: np.ndarray, x: np.ndarray, y: np.ndarray, z: np.ndarray
) -> np.ndarray:
    """Vectorized gradient selection using bitmasking."""
    h = hash_val & 15
    u = np.where(h < 8, x, y)
    v = np.where(h < 4, y, np.where((h == 12) | (h == 14), x, z))
    return np.where((h & 1) == 0, u, -u) + np.where((h & 2) == 0, v, -v)


def noise2d(x: np.ndarray, y: np.ndarray, z: float, scale: float = 4.0) -> np.ndarray:
    """
    Evaluate 3D Perlin noise for a 2D grid.

    Returns float array in ~[-1, 1].
    """
    xs, ys, zs = x / scale, y / scale, float(z) / scale

    xi = np.floor(xs).astype(np.int32) & 255
    yi = np.floor(ys).astype(np.int32) & 255
    zi = int(np.floor(zs)) & 255

    xf, yf, zf = xs - np.floor(xs), ys - np.floor(ys), zs - np.floor(zs)

    u, v, w = _fade(xf), _fade(yf), _fade(np.float32(zf))

    # Corner hashes lookups
    A = _PERM[xi] + yi
    AA = _PERM[A] + zi
    AB = _PERM[A + 1] + zi
    B = _PERM[xi + 1] + yi
    BA = _PERM[B] + zi
    BB = _PERM[B + 1] + zi

    # Gradient projections
    g000 = _grad3d(_PERM[AA], xf, yf, zf)
    g100 = _grad3d(_PERM[BA], xf - 1.0, yf, zf)
    g010 = _grad3d(_PERM[AB], xf, yf - 1.0, zf)
    g110 = _grad3d(_PERM[BB], xf - 1.0, yf - 1.0, zf)
    g001 = _grad3d(_PERM[AA + 1], xf, yf, zf - 1.0)
    g101 = _grad3d(_PERM[BA + 1], xf - 1.0, yf, zf - 1.0)
    g011 = _grad3d(_PERM[AB + 1], xf, yf - 1.0, zf - 1.0)
    g111 = _grad3d(_PERM[BB + 1], xf - 1.0, yf - 1.0, zf - 1.0)

    # Trilinear interpolation
    return _lerp(
        _lerp(_lerp(g000, g100, u), _lerp(g010, g110, u), v),
        _lerp(_lerp(g001, g101, u), _lerp(g011, g111, u), v),
        w,
    )
