import math

EPS = 1e-7


def eq(a, b, eps=EPS):
    return abs(a - b) <= eps


def lt(a, b, eps=EPS):
    return a < b - eps


def le(a, b, eps=EPS):
    return a <= b + eps


def gt(a, b, eps=EPS):
    return a > b + eps


def ge(a, b, eps=EPS):
    return a >= b - eps


class OpCounter:
    def __init__(self):
        self.cmp = 0
        self.add_sub = 0
        self.mul_div = 0

    def to_dict(self):
        return {
            "Сравнения": self.cmp,
            "Слож./Вычит.": self.add_sub,
            "Умнож./Дел.": self.mul_div,
            "Всего оп.": self.cmp + self.add_sub + self.mul_div,
        }


def point_in_rect(x, y, xmin, ymin, xmax, ymax, eps=EPS):
    return ge(x, xmin, eps) and le(x, xmax, eps) and ge(y, ymin, eps) and le(y, ymax, eps)


def point_on_rect_border(x, y, xmin, ymin, xmax, ymax, eps=EPS):
    if not point_in_rect(x, y, xmin, ymin, xmax, ymax, eps):
        return False
    return eq(x, xmin, eps) or eq(x, xmax, eps) or eq(y, ymin, eps) or eq(y, ymax, eps)


def liang_barsky(x1, y1, x2, y2, xmin, ymin, xmax, ymax, eps=EPS):
    ops = OpCounter()
    dx = x2 - x1
    dy = y2 - y1
    ops.add_sub += 2

    ops.cmp += 2
    if eq(dx, 0.0, eps) and eq(dy, 0.0, eps):
        inside = point_in_rect(x1, y1, xmin, ymin, xmax, ymax, eps)
        ops.cmp += 4
        if inside:
            on_border = point_on_rect_border(x1, y1, xmin, ymin, xmax, ymax, eps)
            tag = "Точка на границе/в вершине" if on_border else "Точка внутри окна"
            return tag, (x1, y1, x1, y1), (0.0, 0.0), ops
        return "Точка вне окна (невидима)", None, None, ops

    p = (-dx, dx, -dy, dy)
    q = (x1 - xmin, xmax - x1, y1 - ymin, ymax - y1)
    ops.add_sub += 6

    t0 = 0.0
    t1 = 1.0

    for pi, qi in zip(p, q):
        ops.cmp += 1
        if eq(pi, 0.0, eps):
            ops.cmp += 1
            if lt(qi, 0.0, eps):
                return "Невидим (параллелен границе)", None, None, ops
        else:
            t = qi / pi
            ops.mul_div += 1
            ops.cmp += 1
            if pi < 0.0:
                ops.cmp += 1
                if gt(t, t1, eps):
                    return "Невидим", None, None, ops
                ops.cmp += 1
                if gt(t, t0, eps):
                    t0 = t
            else:
                ops.cmp += 1
                if lt(t, t0, eps):
                    return "Невидим", None, None, ops
                ops.cmp += 1
                if lt(t, t1, eps):
                    t1 = t

    ops.cmp += 1
    if gt(t0, t1, eps):
        return "Невидим", None, None, ops

    cx1 = x1 + t0 * dx
    cy1 = y1 + t0 * dy
    cx2 = x1 + t1 * dx
    cy2 = y1 + t1 * dy
    ops.add_sub += 4
    ops.mul_div += 4

    on_edge = (
        (eq(cx1, xmin, eps) and eq(cx2, xmin, eps))
        or (eq(cx1, xmax, eps) and eq(cx2, xmax, eps))
        or (eq(cy1, ymin, eps) and eq(cy2, ymin, eps))
        or (eq(cy1, ymax, eps) and eq(cy2, ymax, eps))
    )

    if on_edge:
        status = "Видим (лежит точно на границе)"
    elif eq(t0, 0.0, eps) and eq(t1, 1.0, eps):
        status = "Видим полностью"
    else:
        status = "Частично видим"

    return status, (cx1, cy1, cx2, cy2), (t0, t1), ops


def _outcode(x, y, xmin, ymin, xmax, ymax, ops, eps=EPS):
    code = 0
    ops.cmp += 2
    if lt(x, xmin, eps):
        code |= 1
    elif gt(x, xmax, eps):
        code |= 2
    ops.cmp += 2
    if lt(y, ymin, eps):
        code |= 4
    elif gt(y, ymax, eps):
        code |= 8
    return code


def sutherland_cohen(x1, y1, x2, y2, xmin, ymin, xmax, ymax, eps=EPS):
    ops = OpCounter()
    c1 = _outcode(x1, y1, xmin, ymin, xmax, ymax, ops, eps)
    c2 = _outcode(x2, y2, xmin, ymin, xmax, ymax, ops, eps)
    init_codes = (c1, c2)
    iters = 0

    while True:
        iters += 1
        ops.cmp += 2
        if (c1 | c2) == 0:
            if eq(x1, x2, eps) and eq(y1, y2, eps):
                status = "Точка в окне"
            elif iters == 1:
                status = "Видим полностью"
            else:
                status = "Частично видим"
            return status, (x1, y1, x2, y2), init_codes, iters, ops
        if (c1 & c2) != 0:
            return "Невидим (тривиальное отбрасывание)", None, init_codes, iters, ops

        c_out = c1 if c1 != 0 else c2
        ops.cmp += 1
        dx = x2 - x1
        dy = y2 - y1
        ops.add_sub += 2

        if c_out & 8:
            x = x1 + dx * (ymax - y1) / dy if not eq(dy, 0.0, eps) else x1
            y = ymax
            ops.add_sub += 2
            ops.mul_div += 2
        elif c_out & 4:
            x = x1 + dx * (ymin - y1) / dy if not eq(dy, 0.0, eps) else x1
            y = ymin
            ops.add_sub += 2
            ops.mul_div += 2
        elif c_out & 2:
            y = y1 + dy * (xmax - x1) / dx if not eq(dx, 0.0, eps) else y1
            x = xmax
            ops.add_sub += 2
            ops.mul_div += 2
        else:
            y = y1 + dy * (xmin - x1) / dx if not eq(dx, 0.0, eps) else y1
            x = xmin
            ops.add_sub += 2
            ops.mul_div += 2

        if c_out == c1:
            x1, y1 = x, y
            c1 = _outcode(x1, y1, xmin, ymin, xmax, ymax, ops, eps)
        else:
            x2, y2 = x, y
            c2 = _outcode(x2, y2, xmin, ymin, xmax, ymax, ops, eps)


def polygon_signed_area(poly):
    n = len(poly)
    area = 0.0
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return 0.5 * area


def is_convex_polygon(poly, eps=EPS):
    n = len(poly)
    if n < 3:
        return False
    sign = 0
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        x2, y2 = poly[(i + 2) % n]
        cross = (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1)
        if abs(cross) > eps:
            cur = 1 if cross > 0 else -1
            if sign == 0:
                sign = cur
            elif sign != cur:
                return False
    return sign != 0


def ensure_ccw(poly):
    if polygon_signed_area(poly) < 0:
        return list(reversed(poly))
    return list(poly)


def point_in_convex_polygon(px, py, poly, eps=EPS):
    ccw = ensure_ccw(poly)
    n = len(ccw)
    for i in range(n):
        x1, y1 = ccw[i]
        x2, y2 = ccw[(i + 1) % n]
        cross = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
        if lt(cross, 0.0, eps):
            return False
    return True


def cyrus_beck(x1, y1, x2, y2, polygon, eps=EPS):
    ops = OpCounter()
    ccw = ensure_ccw(polygon)
    n = len(ccw)
    dx = x2 - x1
    dy = y2 - y1
    ops.add_sub += 2

    ops.cmp += 2
    if eq(dx, 0.0, eps) and eq(dy, 0.0, eps):
        if point_in_convex_polygon(x1, y1, ccw, eps):
            return "Точка внутри/на границе многоугольника", (x1, y1, x1, y1), (0.0, 0.0), ops
        return "Точка вне многоугольника", None, None, ops

    t_enter = 0.0
    t_leave = 1.0
    on_boundary_edge = False

    for i in range(n):
        vx1, vy1 = ccw[i]
        vx2, vy2 = ccw[(i + 1) % n]
        ex = vx2 - vx1
        ey = vy2 - vy1
        nx = -ey
        ny = ex
        ops.add_sub += 2

        denom = nx * dx + ny * dy
        wx = x1 - vx1
        wy = y1 - vy1
        numer = -(nx * wx + ny * wy)
        ops.add_sub += 4
        ops.mul_div += 4

        ops.cmp += 1
        if eq(denom, 0.0, eps):
            ops.cmp += 1
            if lt(numer, 0.0, eps):
                return "Невидим (вне ребра)", None, None, ops
            if eq(numer, 0.0, eps):
                on_boundary_edge = True
        else:
            t = numer / denom
            ops.mul_div += 1
            ops.cmp += 1
            if denom > 0.0:
                ops.cmp += 1
                if gt(t, t_enter, eps):
                    t_enter = t
            else:
                ops.cmp += 1
                if lt(t, t_leave, eps):
                    t_leave = t

            ops.cmp += 1
            if gt(t_enter, t_leave, eps):
                return "Невидим", None, None, ops

    cx1 = x1 + t_enter * dx
    cy1 = y1 + t_enter * dy
    cx2 = x1 + t_leave * dx
    cy2 = y1 + t_leave * dy
    ops.add_sub += 4
    ops.mul_div += 4

    if on_boundary_edge:
        status = "Видим (на ребре отсекателя)"
    elif eq(t_enter, 0.0, eps) and eq(t_leave, 1.0, eps):
        status = "Видим полностью"
    else:
        status = "Частично видим"

    return status, (cx1, cy1, cx2, cy2), (t_enter, t_leave), ops


def sutherland_hodgman_polygon(subject_poly, clip_poly, eps=EPS):
    ccw_clip = ensure_ccw(clip_poly)
    output = list(subject_poly)
    n_clip = len(ccw_clip)

    for i in range(n_clip):
        if not output:
            break
        ax, ay = ccw_clip[i]
        bx, by = ccw_clip[(i + 1) % n_clip]
        ex = bx - ax
        ey = by - ay

        def inside(px, py):
            return ge(ex * (py - ay) - ey * (px - ax), 0.0, eps)

        def intersect(sx, sy, px, py):
            dx = px - sx
            dy = py - sy
            denom = ex * dy - ey * dx
            if eq(denom, 0.0, eps):
                return (px, py)
            t = (ex * (ay - sy) - ey * (ax - sx)) / denom
            return (sx + t * dx, sy + t * dy)

        inp = output
        output = []
        s = inp[-1]
        for p in inp:
            p_in = inside(p[0], p[1])
            s_in = inside(s[0], s[1])
            if p_in:
                if not s_in:
                    output.append(intersect(s[0], s[1], p[0], p[1]))
                output.append(p)
            elif s_in:
                output.append(intersect(s[0], s[1], p[0], p[1]))
            s = p

    cleaned = []
    for pt in output:
        if not cleaned or not (eq(pt[0], cleaned[-1][0], eps) and eq(pt[1], cleaned[-1][1], eps)):
            cleaned.append(pt)
    if len(cleaned) > 1 and eq(cleaned[0][0], cleaned[-1][0], eps) and eq(cleaned[0][1], cleaned[-1][1], eps):
        cleaned.pop()
    return cleaned
