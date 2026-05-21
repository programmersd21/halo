# halo

![Demo](demo.gif)

Terminal flow field screensaver using Perlin noise, Braille cells, and 24-bit ANSI color.

## Features

- Sub-cell Braille rendering with a 2x4 virtual pixel grid per terminal cell.
- Vectorized 3D Perlin noise flow field.
- 24-bit color presets: `spatial`, `neon`, `sunset`, `ocean`, `forest`, `kinetic`, `fire`.
- Frame diffing to emit only changed terminal cells.
- Live terminal resize handling.
- Native Windows Terminal support through VT/ANSI mode.

## Requirements

- Python 3.10 or later
- NumPy 1.24 or later
- A terminal with 24-bit color support

Recommended terminals: Windows Terminal, WezTerm, Alacritty, kitty, Ghostty, iTerm2.

## Installation

```bash
pip install halo
```

From source:

```bash
git clone https://github.com/programmersd21/halo
cd halo
pip install -e .
```

## Usage

```bash
halo
python -m halo
```

```text
options:
  -p, --particles N      particle count, 1-5000          default: 200
  -s, --speed F          velocity multiplier, 0.01-10    default: 1.5
  -d, --decay F          trail persistence, 0.01-0.99    default: 0.86
  -c, --color MODE       color preset                    default: spatial
  -f, --fps N            target frame rate, 1-120        default: 60
      --scale F          noise spatial frequency, 0.01-64 default: 4.0
      --time-step F      noise z-axis step, 0-1          default: 0.003
```

Color modes:

```text
spatial | neon | sunset | ocean | forest | kinetic | fire
```

Examples:

```bash
halo -c neon -p 400
halo -c fire -p 600 -s 2.0
halo -p 150 -c sunset -d 0.96 -s 0.8
halo -c ocean --scale 2.5 -p 500
halo -p 1000 -c kinetic
```

## How It Works

```text
Perlin noise
  -> flow field
  -> particle update
  -> intensity heat map
  -> Braille encoding
  -> color mapping
  -> changed-cell ANSI output
```

Particle state is stored as an `(n, 4)` float32 array:

```text
x, y, vx, vy
```

The renderer keeps previous frame buffers for characters, color, and bold state. On resize, those buffers are reset to the new terminal shape.

## Notes

- Very high particle counts are intentionally rejected to avoid pathological terminal output and memory use.
- Color and brightness output are quantized to keep dense particle fields responsive.
- Frame output is paced against an output budget so large terminals do not flood slower terminal renderers.
- macOS Terminal.app does not support true color reliably; use a true-color terminal.

## License

MIT
