"""Entrypoint, Terminal Context, and Event Loop."""

import argparse
import os
import shutil
import signal
import sys
import time

from .engine import FlowEngine
from .renderer import Renderer

_IS_WINDOWS = os.name == "nt"

if not _IS_WINDOWS:
    import termios
    import tty

_HIDE_CURSOR = "\x1b[?25l"
_SHOW_CURSOR = "\x1b[?25h"
_CLEAR_SCREEN = "\x1b[2J"
_HOME = "\x1b[H"
_RESET_ALL = "\x1b[0m"
_ALT_SCREEN = "\x1b[?1049h"
_NORM_SCREEN = "\x1b[?1049l"
_TERMINAL_OUTPUT_BUDGET = 1_500_000
_MAX_PARTICLES = 5_000
_MAX_FPS = 120
_MAX_SPEED = 10.0
_MAX_SCALE = 64.0
_MAX_TIME_STEP = 1.0

_RESIZE_PENDING: bool = False


def _sigwinch_handler(signum: int, frame) -> None:
    global _RESIZE_PENDING
    _RESIZE_PENDING = True


def _enable_windows_ansi() -> None:
    """Enable VT/ANSI processing and optimize process priority on Windows."""
    try:
        import ctypes
        import ctypes.wintypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]

        stdout_handle = kernel32.GetStdHandle(-11)
        mode = ctypes.wintypes.DWORD(0)
        kernel32.GetConsoleMode(stdout_handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(stdout_handle, mode.value | 0x0004 | 0x0008)

        stdin_handle = kernel32.GetStdHandle(-10)
        kernel32.GetConsoleMode(stdin_handle, ctypes.byref(mode))
        kernel32.SetConsoleMode(stdin_handle, (mode.value & ~0x0040) | 0x0080)

        kernel32.SetPriorityClass(kernel32.GetCurrentProcess(), 0x00008000)

        try:
            winmm = ctypes.windll.winmm
            winmm.timeBeginPeriod(1)
        except Exception:
            pass

        kernel32.SetConsoleOutputCP(65001)
    except Exception:
        pass


class _UnixRawMode:
    """Context manager for terminal raw mode on Unix."""

    def __init__(self) -> None:
        self._fd: int | None = None
        self._old: list | None = None

    def __enter__(self) -> "_UnixRawMode":
        try:
            self._fd = sys.stdin.fileno()
            self._old = termios.tcgetattr(self._fd)  # type: ignore[attr-defined]
            tty.setcbreak(self._fd)  # type: ignore[attr-defined]
        except Exception:
            self._old = None
        return self

    def __exit__(self, *_) -> None:
        if self._old is not None and self._fd is not None:
            try:
                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._old)  # type: ignore[attr-defined]
            except Exception:
                pass


def _get_terminal_size() -> tuple[int, int]:
    size = shutil.get_terminal_size(fallback=(80, 24))
    cols = max(size.columns, 10)
    rows = max(size.lines - 1, 5)
    return cols, rows


def _bounded_int(name: str, minimum: int, maximum: int):
    def parse(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{name} must be an integer") from exc
        if parsed < minimum or parsed > maximum:
            raise argparse.ArgumentTypeError(
                f"{name} must be between {minimum} and {maximum}"
            )
        return parsed

    return parse


def _bounded_float(name: str, minimum: float, maximum: float):
    def parse(value: str) -> float:
        try:
            parsed = float(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{name} must be a number") from exc
        if parsed < minimum or parsed > maximum:
            raise argparse.ArgumentTypeError(
                f"{name} must be between {minimum:g} and {maximum:g}"
            )
        return parsed

    return parse


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="halo",
        description="Terminal flow field screensaver.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "-p",
        "--particles",
        type=_bounded_int("particles", 1, _MAX_PARTICLES),
        default=200,
        help=f"particle count, 1-{_MAX_PARTICLES}",
    )
    p.add_argument(
        "-s",
        "--speed",
        type=_bounded_float("speed", 0.01, _MAX_SPEED),
        default=1.5,
        help=f"velocity multiplier, 0.01-{_MAX_SPEED:g}",
    )
    p.add_argument(
        "-d",
        "--decay",
        type=_bounded_float("decay", 0.01, 0.99),
        default=0.86,
        help="trail persistence, 0.01-0.99",
    )
    p.add_argument(
        "-c",
        "--color",
        default="spatial",
        choices=["spatial", "neon", "sunset", "ocean", "forest", "kinetic", "fire"],
        help="gradient mode",
    )
    p.add_argument(
        "-f",
        "--fps",
        type=_bounded_int("fps", 1, _MAX_FPS),
        default=60,
        help=f"target frame rate, 1-{_MAX_FPS}",
    )
    p.add_argument(
        "--scale",
        type=_bounded_float("scale", 0.01, _MAX_SCALE),
        default=4.0,
        help=f"noise spatial frequency, 0.01-{_MAX_SCALE:g}",
    )
    p.add_argument(
        "--time-step",
        type=_bounded_float("time-step", 0.0, _MAX_TIME_STEP),
        default=0.003,
        help=f"noise z-axis step, 0-{_MAX_TIME_STEP:g}",
    )
    return p


def main() -> None:
    global _RESIZE_PENDING
    args = _build_arg_parser().parse_args()
    frame_dur = 1.0 / args.fps

    if _IS_WINDOWS:
        _enable_windows_ansi()
    else:
        signal.signal(signal.SIGWINCH, _sigwinch_handler)  # type: ignore[attr-defined]

    raw_ctx = _UnixRawMode() if not _IS_WINDOWS else None
    if raw_ctx:
        raw_ctx.__enter__()

    out = sys.stdout
    out.write(_ALT_SCREEN + _HIDE_CURSOR + _CLEAR_SCREEN + _HOME)
    out.flush()

    cols, rows = _get_terminal_size()
    engine = FlowEngine(
        cols=cols,
        rows=rows,
        n_particles=args.particles,
        speed=args.speed,
        decay=args.decay,
        noise_scale=args.scale,
        time_step=args.time_step,
    )
    renderer = Renderer(cols=cols, rows=rows, color_mode=args.color)

    out.write(_CLEAR_SCREEN + _HOME)
    out.flush()

    try:
        frame_count = 0
        while True:
            frame_start = time.perf_counter()

            if _RESIZE_PENDING:
                new_cols, new_rows = _get_terminal_size()
            elif frame_count % 30 == 0:
                new_cols, new_rows = _get_terminal_size()
            else:
                new_cols, new_rows = cols, rows

            if _RESIZE_PENDING or new_cols != cols or new_rows != rows:
                _RESIZE_PENDING = False
                time.sleep(0.05)
                new_cols, new_rows = _get_terminal_size()
                cols, rows = new_cols, new_rows
                engine.resize(cols, rows)
                renderer.resize(cols, rows)
                out.write(_CLEAR_SCREEN + _HOME)
                out.flush()
                frame_count = 0
                continue

            intensity = engine.step()
            frame_str = renderer.render_frame(intensity)

            if frame_str:
                out.write(frame_str)
                out.flush()

            elapsed = time.perf_counter() - frame_start
            output_dur = len(frame_str) / _TERMINAL_OUTPUT_BUDGET
            target_dur = max(frame_dur, output_dur)
            sleep_time = target_dur - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
            frame_count += 1
    except KeyboardInterrupt:
        pass
    finally:
        out.write(_SHOW_CURSOR + _RESET_ALL + _CLEAR_SCREEN + _NORM_SCREEN + _HOME)
        out.flush()
        if raw_ctx:
            raw_ctx.__exit__(None, None, None)
        print("\nhalo - goodbye\n")


if __name__ == "__main__":
    main()
