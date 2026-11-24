import math


class RasterEngine:
    @staticmethod
    def step_by_step_line(target, x0, y0, x1, y1):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx = x1 - x0
        dy = y1 - y0
        if dx == 0 and dy == 0:
            target.set_pixel(x0, y0, 1.0, {"Параметр": "Вырожденный отрезок"})
            return
        if abs(dx) >= abs(dy):
            step = 1 if x1 >= x0 else -1
            k = dy / dx
            b = y0 - k * x0
            x = x0
            while True:
                y_exact = k * x + b
                y = int(math.floor(y_exact + 0.5))
                target.set_pixel(x, y, 1.0, {"k": round(k, 3), "y_точн": round(y_exact, 3)})
                if x == x1:
                    break
                x += step
        else:
            step = 1 if y1 >= y0 else -1
            inv_k = dx / dy
            y = y0
            while True:
                x_exact = x0 + inv_k * (y - y0)
                x = int(math.floor(x_exact + 0.5))
                target.set_pixel(x, y, 1.0, {"1/k": round(inv_k, 3), "x_точн": round(x_exact, 3)})
                if y == y1:
                    break
                y += step

    @staticmethod
    def dda_line(target, x0, y0, x1, y1):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx = x1 - x0
        dy = y1 - y0
        steps = max(abs(dx), abs(dy))
        if steps == 0:
            target.set_pixel(x0, y0, 1.0, {"L": 0})
            return
        x_inc = dx / steps
        y_inc = dy / steps
        x = float(x0)
        y = float(y0)
        for _ in range(steps + 1):
            ix = int(math.floor(x + 0.5))
            iy = int(math.floor(y + 0.5))
            target.set_pixel(ix, iy, 1.0, {"x_float": round(x, 3), "y_float": round(y, 3)})
            x += x_inc
            y += y_inc

    @staticmethod
    def bresenham_line(target, x0, y0, x1, y1):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            target.set_pixel(x0, y0, 1.0, {"Ошибка e": err})
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    @staticmethod
    def bresenham_circle(target, xc, yc, r):
        xc, yc, r = int(xc), int(yc), abs(int(r))
        if r == 0:
            target.set_pixel(xc, yc, 1.0, {"d": 0})
            return
        x = 0
        y = r
        d = 3 - 2 * r
        while x <= y:
            pts = (
                (xc + x, yc + y),
                (xc - x, yc + y),
                (xc + x, yc - y),
                (xc - x, yc - y),
                (xc + y, yc + x),
                (xc - y, yc + x),
                (xc + y, yc - x),
                (xc - y, yc - x),
            )
            for px, py in pts:
                target.set_pixel(px, py, 1.0, {"d": d, "Октант_x": x, "Октант_y": y})
            if d < 0:
                d = d + 4 * x + 6
            else:
                d = d + 4 * (x - y) + 10
                y -= 1
            x += 1

    @staticmethod
    def wu_line(target, x0, y0, x1, y1):
        x0, y0, x1, y1 = float(x0), float(y0), float(x1), float(y1)
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1
        if x0 > x1:
            x0, x1 = x1, x0
            y0, y1 = y1, y0
        dx = x1 - x0
        dy = y1 - y0
        gradient = 1.0 if dx == 0.0 else dy / dx

        def plot(px, py, c):
            if c <= 0.0:
                return
            if steep:
                target.set_pixel(py, px, c, {"y_точн": round(px, 3)})
            else:
                target.set_pixel(px, py, c, {"y_точн": round(py, 3)})

        xend = round(x0)
        yend = y0 + gradient * (xend - x0)
        xgap = 1.0 - ((x0 + 0.5) - math.floor(x0 + 0.5))
        xpxl1 = int(xend)
        ypxl1 = int(math.floor(yend))
        f1 = yend - math.floor(yend)
        plot(xpxl1, ypxl1, (1.0 - f1) * xgap)
        plot(xpxl1, ypxl1 + 1, f1 * xgap)
        intery = yend + gradient

        xend = round(x1)
        yend = y1 + gradient * (xend - x1)
        xgap = (x1 + 0.5) - math.floor(x1 + 0.5)
        xpxl2 = int(xend)
        ypxl2 = int(math.floor(yend))
        f2 = yend - math.floor(yend)
        plot(xpxl2, ypxl2, (1.0 - f2) * xgap)
        plot(xpxl2, ypxl2 + 1, f2 * xgap)

        for x in range(xpxl1 + 1, xpxl2):
            iy = int(math.floor(intery))
            frac = intery - iy
            plot(x, iy, 1.0 - frac)
            plot(x, iy + 1, frac)
            intery += gradient

    @staticmethod
    def castle_pitteway_line(target, x0, y0, x1, y1):
        x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
        dx = x1 - x0
        dy = y1 - y0
        sx = 1 if dx >= 0 else -1
        sy = 1 if dy >= 0 else -1
        adx = abs(dx)
        ady = abs(dy)
        if adx == 0 and ady == 0:
            target.set_pixel(x0, y0, 1.0, {"Сдвиг": "нет"})
            return
        if adx >= ady:
            a = adx - ady
            b = ady
            s1 = (sx, 0)
            s2 = (sx, sy)
        else:
            a = ady - adx
            b = adx
            s1 = (0, sy)
            s2 = (sx, sy)
        if b == 0:
            cx, cy = x0, y0
            for _ in range(a + 1):
                target.set_pixel(cx, cy, 1.0, {"Вектор": str(s1)})
                cx += s1[0]
                cy += s1[1]
            return
        m1 = [s1]
        m2 = [s2]
        while a != b:
            if a > b:
                a -= b
                m2 = m1 + m2
            else:
                b -= a
                m1 = m1 + m2
        pattern = (m1 + m2) * a
        cx, cy = x0, y0
        target.set_pixel(cx, cy, 1.0, {"Вектор": "старт", "НОД(dx,dy)": a})
        for step_x, step_y in pattern:
            cx += step_x
            cy += step_y
            target.set_pixel(cx, cy, 1.0, {"Вектор": f"({step_x}, {step_y})", "НОД(dx,dy)": a})
