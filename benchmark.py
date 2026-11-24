from time import perf_counter
import numpy as np
import pandas as pd
from raster_engine import RasterEngine
from virtual_grid import VirtualGrid


def run_benchmark(total_lines=100000, total_circles=50000):
    rng = np.random.default_rng(42)
    grid = VirtualGrid(-250, 250, -250, 250, record_steps=False)

    angles = rng.uniform(0.0, 2.0 * np.pi, size=total_lines)
    lengths = rng.uniform(20.0, 220.0, size=total_lines)
    x0 = rng.integers(-20, 21, size=total_lines)
    y0 = rng.integers(-20, 21, size=total_lines)
    x1 = np.rint(x0 + lengths * np.cos(angles)).astype(int)
    y1 = np.rint(y0 + lengths * np.sin(angles)).astype(int)
    segments = list(zip(x0.tolist(), y0.tolist(), x1.tolist(), y1.tolist()))

    line_algos = [
        ("Пошаговый", RasterEngine.step_by_step_line),
        ("ЦДА (DDA)", RasterEngine.dda_line),
        ("Брезенхем (отрезок)", RasterEngine.bresenham_line),
        ("Алгоритм Ву", RasterEngine.wu_line),
        ("Кастл-Питвей", RasterEngine.castle_pitteway_line),
    ]

    summary_rows = []
    for name, fn in line_algos:
        grid.clear()
        t0 = perf_counter()
        for sx0, sy0, sx1, sy1 in segments:
            fn(grid, sx0, sy0, sx1, sy1)
        dt = perf_counter() - t0
        summary_rows.append({
            "Алгоритм": name,
            "Примитив": "Отрезки (8 октантов)",
            "Количество": total_lines,
            "Время, с": round(dt, 4),
            "Примитивов/сек": int(total_lines / max(dt, 1e-9)),
        })

    cx = rng.integers(-40, 41, size=total_circles).tolist()
    cy = rng.integers(-40, 41, size=total_circles).tolist()
    radii = rng.integers(5, 180, size=total_circles).tolist()
    circles = list(zip(cx, cy, radii))

    grid.clear()
    t0 = perf_counter()
    for x, y, r in circles:
        RasterEngine.bresenham_circle(grid, x, y, r)
    dt_circle = perf_counter() - t0
    summary_rows.append({
        "Алгоритм": "Брезенхем (окружность)",
        "Примитив": "Окружности",
        "Количество": total_circles,
        "Время, с": round(dt_circle, 4),
        "Примитивов/сек": int(total_circles / max(dt_circle, 1e-9)),
    })

    counts = [10000, 25000, 50000, 75000, total_lines]
    scaling_rows = []
    for n in counts:
        sub = segments[:n]
        for name, fn in line_algos:
            grid.clear()
            t0 = perf_counter()
            for sx0, sy0, sx1, sy1 in sub:
                fn(grid, sx0, sy0, sx1, sy1)
            dt = perf_counter() - t0
            scaling_rows.append({
                "Количество отрезков": n,
                "Алгоритм": name,
                "Время, с": dt,
            })

    length_rows = []
    test_lengths = [10, 30, 60, 100, 150, 200]
    batch_len = 15000
    for L in test_lengths:
        ang = rng.uniform(0.0, 2.0 * np.pi, size=batch_len)
        lx1 = np.rint(L * np.cos(ang)).astype(int).tolist()
        ly1 = np.rint(L * np.sin(ang)).astype(int).tolist()
        fixed_segs = list(zip([0] * batch_len, [0] * batch_len, lx1, ly1))
        for name, fn in line_algos:
            grid.clear()
            t0 = perf_counter()
            for sx0, sy0, sx1, sy1 in fixed_segs:
                fn(grid, sx0, sy0, sx1, sy1)
            dt = perf_counter() - t0
            length_rows.append({
                "Длина отрезка, px": L,
                "Алгоритм": name,
                "Время (15 000 шт.), с": dt,
            })

    return pd.DataFrame(summary_rows), pd.DataFrame(scaling_rows), pd.DataFrame(length_rows)
