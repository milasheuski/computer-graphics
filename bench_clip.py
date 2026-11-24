from time import perf_counter
import numpy as np
import pandas as pd
from clipping_engine import liang_barsky, sutherland_cohen


class QuadtreeNode:
    def __init__(self, xmin, ymin, xmax, ymax, depth=0, max_depth=4):
        self.xmin = xmin
        self.ymin = ymin
        self.xmax = xmax
        self.ymax = ymax
        self.depth = depth
        self.max_depth = max_depth
        self.items = []
        self.children = []

    def subdivide(self):
        mx = 0.5 * (self.xmin + self.xmax)
        my = 0.5 * (self.ymin + self.ymax)
        d = self.depth + 1
        self.children = [
            QuadtreeNode(self.xmin, self.ymin, mx, my, d, self.max_depth),
            QuadtreeNode(mx, self.ymin, self.xmax, my, d, self.max_depth),
            QuadtreeNode(self.xmin, my, mx, self.ymax, d, self.max_depth),
            QuadtreeNode(mx, my, self.xmax, self.ymax, d, self.max_depth),
        ]

    def insert(self, seg, sxmin, symin, sxmax, symax):
        if sxmax < self.xmin or sxmin > self.xmax or symax < self.ymin or symin > self.ymax:
            return
        if self.depth >= self.max_depth:
            self.items.append(seg)
            return
        if not self.children:
            self.subdivide()
        for ch in self.children:
            if sxmin >= ch.xmin and sxmax <= ch.xmax and symin >= ch.ymin and symax <= ch.ymax:
                ch.insert(seg, sxmin, symin, sxmax, symax)
                return
        self.items.append(seg)

    def query(self, wxmin, wymin, wxmax, wymax, out):
        if wxmax < self.xmin or wxmin > self.xmax or wymax < self.ymin or wymin > self.ymax:
            return
        out.extend(self.items)
        for ch in self.children:
            ch.query(wxmin, wymin, wxmax, wymax, out)


def run_clipping_benchmark(total_segments=500000):
    rng = np.random.default_rng(42)
    x1 = rng.uniform(-100.0, 100.0, size=total_segments)
    y1 = rng.uniform(-100.0, 100.0, size=total_segments)
    angles = rng.uniform(0.0, 2.0 * np.pi, size=total_segments)
    lengths = rng.uniform(5.0, 45.0, size=total_segments)
    x2 = x1 + lengths * np.cos(angles)
    y2 = y1 + lengths * np.sin(angles)

    segments = list(zip(x1.tolist(), y1.tolist(), x2.tolist(), y2.tolist()))
    wxmin, wymin, wxmax, wymax = -25.0, -25.0, 25.0, 25.0

    t0 = perf_counter()
    vis_lb = 0
    for sx1, sy1, sx2, sy2 in segments:
        _, clipped, _, _ = liang_barsky(sx1, sy1, sx2, sy2, wxmin, wymin, wxmax, wymax)
        if clipped is not None:
            vis_lb += 1
    dt_lb = perf_counter() - t0

    t0 = perf_counter()
    vis_sc = 0
    for sx1, sy1, sx2, sy2 in segments:
        _, clipped, _, _, _ = sutherland_cohen(sx1, sy1, sx2, sy2, wxmin, wymin, wxmax, wymax)
        if clipped is not None:
            vis_sc += 1
    dt_sc = perf_counter() - t0

    t0 = perf_counter()
    vis_aabb = 0
    for sx1, sy1, sx2, sy2 in segments:
        if (sx1 < wxmin and sx2 < wxmin) or (sx1 > wxmax and sx2 > wxmax):
            continue
        if (sy1 < wymin and sy2 < wymin) or (sy1 > wymax and sy2 > wymax):
            continue
        _, clipped, _, _ = liang_barsky(sx1, sy1, sx2, sy2, wxmin, wymin, wxmax, wymax)
        if clipped is not None:
            vis_aabb += 1
    dt_aabb = perf_counter() - t0

    t_build0 = perf_counter()
    qt = QuadtreeNode(-150.0, -150.0, 150.0, 150.0, depth=0, max_depth=4)
    for seg in segments:
        sx1, sy1, sx2, sy2 = seg
        qt.insert(seg, min(sx1, sx2), min(sy1, sy2), max(sx1, sx2), max(sy1, sy2))
    dt_qt_build = perf_counter() - t_build0

    t0 = perf_counter()
    candidates = []
    qt.query(wxmin, wymin, wxmax, wymax, candidates)
    vis_qt = 0
    for sx1, sy1, sx2, sy2 in candidates:
        _, clipped, _, _ = liang_barsky(sx1, sy1, sx2, sy2, wxmin, wymin, wxmax, wymax)
        if clipped is not None:
            vis_qt += 1
    dt_qt_query = perf_counter() - t0

    summary = pd.DataFrame([
        {
            "Метод": "Лианг-Барски (прямой перебор)",
            "Отрезков": total_segments,
            "Видимых": vis_lb,
            "Время отсечения, с": round(dt_lb, 4),
            "Отрезков/сек": int(total_segments / max(dt_lb, 1e-9)),
        },
        {
            "Метод": "Сазерленд-Коэн (прямой перебор)",
            "Отрезков": total_segments,
            "Видимых": vis_sc,
            "Время отсечения, с": round(dt_sc, 4),
            "Отрезков/сек": int(total_segments / max(dt_sc, 1e-9)),
        },
        {
            "Метод": "AABB-отбраковка + Лианг-Барски",
            "Отрезков": total_segments,
            "Видимых": vis_aabb,
            "Время отсечения, с": round(dt_aabb, 4),
            "Отрезков/сек": int(total_segments / max(dt_aabb, 1e-9)),
        },
        {
            "Метод": f"Quadtree (выборка {len(candidates)} шт.) + Лианг-Барски",
            "Отрезков": total_segments,
            "Видимых": vis_qt,
            "Время отсечения, с": round(dt_qt_query, 4),
            "Отрезков/сек": int(total_segments / max(dt_qt_query, 1e-9)),
        },
    ])

    steps = [50000, 100000, 250000, total_segments]
    scaling_rows = []
    for n in steps:
        sub = segments[:n]
        t0 = perf_counter()
        for sx1, sy1, sx2, sy2 in sub:
            liang_barsky(sx1, sy1, sx2, sy2, wxmin, wymin, wxmax, wymax)
        scaling_rows.append({"Отрезков": n, "Метод": "Лианг-Барски", "Время, с": perf_counter() - t0})

        t0 = perf_counter()
        for sx1, sy1, sx2, sy2 in sub:
            sutherland_cohen(sx1, sy1, sx2, sy2, wxmin, wymin, wxmax, wymax)
        scaling_rows.append({"Отрезков": n, "Метод": "Сазерленд-Коэн", "Время, с": perf_counter() - t0})

        t0 = perf_counter()
        for sx1, sy1, sx2, sy2 in sub:
            if (sx1 < wxmin and sx2 < wxmin) or (sx1 > wxmax and sx2 > wxmax):
                continue
            if (sy1 < wymin and sy2 < wymin) or (sy1 > wymax and sy2 > wymax):
                continue
            liang_barsky(sx1, sy1, sx2, sy2, wxmin, wymin, wxmax, wymax)
        scaling_rows.append({"Отрезков": n, "Метод": "AABB + Лианг-Барски", "Время, с": perf_counter() - t0})

    return summary, pd.DataFrame(scaling_rows), round(dt_qt_build, 4)
