"""Braille Renderer, Gradient Color Engine, and Frame Diffing."""

from typing import Literal, TypedDict

import numpy as np

_BRAILLE_BITS = np.array(
    [
        [0x01, 0x08],
        [0x02, 0x10],
        [0x04, 0x20],
        [0x40, 0x80],
    ],
    dtype=np.uint8,
)


class _Preset(TypedDict, total=False):
    type: Literal["spatial", "kinetic"]
    anchors: np.ndarray
    stops: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]


_PRESETS: dict[str, _Preset] = {
    "spatial": {
        "type": "spatial",
        "anchors": np.array(
            [[20, 0, 80], [0, 245, 255], [255, 80, 120]], dtype=np.float32
        ),
    },
    "neon": {
        "type": "spatial",
        "anchors": np.array(
            [[255, 0, 255], [0, 255, 255], [255, 255, 0]], dtype=np.float32
        ),
    },
    "sunset": {
        "type": "spatial",
        "anchors": np.array(
            [[255, 80, 0], [255, 0, 128], [40, 0, 100]], dtype=np.float32
        ),
    },
    "ocean": {
        "type": "spatial",
        "anchors": np.array(
            [[0, 255, 128], [0, 128, 255], [0, 40, 120]], dtype=np.float32
        ),
    },
    "forest": {
        "type": "spatial",
        "anchors": np.array(
            [[34, 139, 34], [154, 205, 50], [0, 50, 0]], dtype=np.float32
        ),
    },
    "kinetic": {
        "type": "kinetic",
        "stops": (
            np.array([0.0, 0.3, 0.6, 1.0], dtype=np.float32),
            np.array([26, 127, 0, 255], dtype=np.float32),
            np.array([5, 0, 245, 255], dtype=np.float32),
            np.array([51, 255, 255, 255], dtype=np.float32),
        ),
    },
    "fire": {
        "type": "kinetic",
        "stops": (
            np.array([0.0, 0.4, 0.8, 1.0], dtype=np.float32),
            np.array([40, 255, 255, 255], dtype=np.float32),
            np.array([0, 80, 200, 255], dtype=np.float32),
            np.array([0, 0, 0, 255], dtype=np.float32),
        ),
    },
}

_RESET = "\x1b[0m"
_BOLD_ON = "\x1b[1m"
_BRAILLE_BASE = 0x2800
_BRAILLE_DOT_THRESHOLD = 0.25
_BRIGHTNESS_LEVELS = 2
_COLOR_STEP = 32

_BRAILLE_LOOKUP = np.array([chr(_BRAILLE_BASE + i) for i in range(256)], dtype=object)


class Renderer:
    """Stateful renderer with frame diffing."""

    def __init__(self, cols: int, rows: int, color_mode: str = "spatial") -> None:
        self.cols, self.rows = cols, rows
        self.color_mode = color_mode if color_mode in _PRESETS else "spatial"
        self._prev_chars: np.ndarray = np.full((rows, cols), "", dtype=str)
        self._prev_rgb: np.ndarray = np.zeros((rows, cols, 3), dtype=np.uint8)
        self._prev_bold: np.ndarray = np.zeros((rows, cols), dtype=bool)
        self._precomputed_rgb = self._precompute_gradient(cols, rows)

    def _precompute_gradient(self, cols: int, rows: int) -> np.ndarray:
        """Pre-compute positional RGB gradient for spatial modes."""
        preset = _PRESETS[self.color_mode]
        if preset["type"] != "spatial":
            return np.array([], dtype=np.uint8)

        anchors = preset["anchors"]
        hx = np.linspace(0.0, 1.0, cols, dtype=np.float32)[np.newaxis, :]
        hy = np.linspace(0.0, 1.0, rows, dtype=np.float32)[:, np.newaxis]

        w0 = (1.0 - hx) * (1.0 - hy)
        w1 = hx * (1.0 - hy)
        w2 = hy * np.ones_like(hx)

        total = w0 + w1 + w2
        rgb = (
            (w0 / total)[:, :, np.newaxis] * anchors[0]
            + (w1 / total)[:, :, np.newaxis] * anchors[1]
            + (w2 / total)[:, :, np.newaxis] * anchors[2]
        )
        return self._quantize_rgb(np.clip(rgb, 0, 255).astype(np.uint8))

    def _compute_kinetic_rgb(self, intensity_cell: np.ndarray) -> np.ndarray:
        """Map intensity to kinetic colormap."""
        stops_i, stops_r, stops_g, stops_b = _PRESETS[self.color_mode]["stops"]
        r = np.interp(intensity_cell, stops_i, stops_r)
        g = np.interp(intensity_cell, stops_i, stops_g)
        b = np.interp(intensity_cell, stops_i, stops_b)
        return self._quantize_rgb(np.stack([r, g, b], axis=-1).astype(np.uint8))

    def _quantize_rgb(self, rgb: np.ndarray) -> np.ndarray:
        return (rgb // _COLOR_STEP * _COLOR_STEP).astype(np.uint8)

    def _encode_braille(self, intensity: np.ndarray) -> np.ndarray:
        """Convert virtual intensity map to Braille bitmask."""
        bitmask = np.zeros((self.rows, self.cols), dtype=np.uint8)
        for dr in range(4):
            for dc in range(2):
                sub = intensity[dr::4, dc::2]
                h, w = min(sub.shape[0], self.rows), min(sub.shape[1], self.cols)
                active = sub[:h, :w] > _BRAILLE_DOT_THRESHOLD
                if np.any(active):
                    bitmask[:h, :w] |= active.astype(np.uint8) * _BRAILLE_BITS[dr, dc]
        return bitmask

    def _cell_intensity(self, intensity: np.ndarray) -> np.ndarray:
        """Downsample virtual intensity to terminal cell intensity."""
        h4, w2 = self.rows * 4, self.cols * 2
        trimmed = intensity[:h4, :w2]
        cell = trimmed.reshape(self.rows, 4, self.cols, 2)
        return cell.max(axis=(1, 3))

    def render_frame(self, intensity: np.ndarray) -> str:
        """Generate ANSI frame string for changed cells."""
        if intensity.shape != (self.rows * 4, self.cols * 2):
            return ""
        if (
            self._prev_chars.shape != (self.rows, self.cols)
            or self._prev_rgb.shape != (self.rows, self.cols, 3)
            or self._prev_bold.shape != (self.rows, self.cols)
        ):
            self._reset_frame_cache()

        bitmask = self._encode_braille(intensity)
        chars = _BRAILLE_LOOKUP[bitmask]

        cell_int = self._cell_intensity(intensity)
        display_int = np.round(cell_int * (_BRIGHTNESS_LEVELS - 1)) / (
            _BRIGHTNESS_LEVELS - 1
        )

        if _PRESETS[self.color_mode]["type"] == "kinetic":
            rgb = self._compute_kinetic_rgb(display_int)
        else:
            rgb = self._precomputed_rgb.copy()

        bold = cell_int > 0.7
        blank = bitmask == 0
        rgb[blank] = 0
        bold[blank] = False

        changed = (
            (chars != self._prev_chars)
            | np.any(rgb != self._prev_rgb, axis=2)
            | (bold != self._prev_bold)
        )

        changed_cells = np.argwhere(changed)

        if len(changed_cells) == 0:
            return ""

        parts: list[str] = []
        prev_row = prev_col = -2
        last_R = last_G = last_B = -1
        last_bold = False

        p_chars = self._prev_chars
        p_rgb = self._prev_rgb
        p_bold = self._prev_bold

        for row, col in changed_cells:
            c = chars[row, col]
            R, G, B = rgb[row, col]
            is_bold = bold[row, col]
            ci = cell_int[row, col]

            if row != prev_row or col != prev_col + 1:
                parts.append(f"\x1b[{row + 1};{col + 1}H")
            prev_row, prev_col = row, col

            if ci <= 0.02:
                if last_R != -1 or last_bold:
                    parts.append(_RESET)
                    last_R = last_G = last_B = -1
                    last_bold = False
                parts.append(" ")
            else:
                if is_bold != last_bold:
                    parts.append(_BOLD_ON if is_bold else "\x1b[22m")
                    last_bold = is_bold

                if R != last_R or G != last_G or B != last_B:
                    parts.append(f"\x1b[38;2;{R};{G};{B}m")
                    last_R, last_G, last_B = R, G, B

                parts.append(c)

        if parts:
            parts.append(_RESET)

        p_chars[:] = chars
        p_rgb[:] = rgb
        p_bold[:] = bold

        return "".join(parts)

    def _reset_frame_cache(self) -> None:
        self._prev_chars = np.full((self.rows, self.cols), "", dtype=str)
        self._prev_rgb = np.zeros((self.rows, self.cols, 3), dtype=np.uint8)
        self._prev_bold = np.zeros((self.rows, self.cols), dtype=bool)

    def resize(self, cols: int, rows: int, color_mode: str | None = None) -> None:
        """Handle terminal resize."""
        self.cols, self.rows = cols, rows
        if color_mode is not None and color_mode in _PRESETS:
            self.color_mode = color_mode

        self._reset_frame_cache()
        self._precomputed_rgb = self._precompute_gradient(cols, rows)
