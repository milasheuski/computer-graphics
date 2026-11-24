STANDARD_INPUT_EXAMPLE = """8
-8 -4 12 9
-9 6 11 -5
2 -9 2 11
-10 3 13 3
-11 7 -6 11
-2 1 5 6
-5 -8 10 -8
7 7 7 7
-5 -5 8 7"""

CORNER_CASES_INPUT = """10
-6 -4 10 -4
8 -7 8 9
-6 6 2 6
-6 -4 -6 -4
8 6 8 6
-6 6 -6 6
-10 -8 12 10
-10 10 12 -8
-3 -4 8 6
1 2 4 4
-6 -4 8 6"""

POLYGON_PRESETS = {
    "Выпуклый шестиугольник": [
        (-5.0, -3.0),
        (2.0, -6.0),
        (8.0, -2.0),
        (7.0, 5.0),
        (-1.0, 7.0),
        (-7.0, 2.0),
    ],
    "Наклонный пятиугольник": [
        (-6.0, -4.0),
        (5.0, -5.0),
        (8.0, 2.0),
        (0.0, 7.0),
        (-7.0, 3.0),
    ],
    "Выпуклая трапеция": [
        (-7.0, -4.0),
        (7.0, -4.0),
        (4.0, 5.0),
        (-4.0, 5.0),
    ],
}

CYRUS_BECK_SEGMENTS = [
    (-9.0, -1.0, 10.0, 3.0),
    (-7.0, 2.0, 7.0, 5.0),
    (-5.0, -3.0, 2.0, -6.0),
    (-2.0, -2.0, 3.0, 2.0),
    (5.0, -7.0, 10.0, -4.0),
    (-1.0, 7.0, -1.0, 7.0),
    (-8.0, 7.0, 9.0, -5.0),
]

CONCAVE_SUBJECT_PRESETS = {
    "Невыпуклая «стрелка» (пересекает вершины окна)": [
        (-8.0, 0.0),
        (0.0, 8.0),
        (9.0, 2.0),
        (2.0, 1.0),
        (8.0, -6.0),
        (-2.0, -7.0),
        (-2.0, -1.0),
    ],
    "Невыпуклая буква «П»": [
        (-7.0, -6.0),
        (-7.0, 7.0),
        (7.0, 7.0),
        (7.0, -6.0),
        (3.0, -6.0),
        (3.0, 2.0),
        (-3.0, 2.0),
        (-3.0, -6.0),
    ],
}


def parse_lab5_text(raw_text):
    lines = [ln.strip() for ln in raw_text.strip().splitlines() if ln.strip()]
    if len(lines) < 3:
        raise ValueError("Недостаточно строк: ожидается число отрезков n, n строк координат и строка окна.")
    n = int(lines[0].split()[0])
    if len(lines) < n + 2:
        raise ValueError(f"Указано n = {n}, но строк с координатами меньше.")
    segments = []
    for i in range(1, n + 1):
        parts = [float(v) for v in lines[i].split()[:4]]
        if len(parts) < 4:
            raise ValueError(f"Ошибка в строке {i + 1}: нужно 4 числа (X1 Y1 X2 Y2).")
        segments.append(tuple(parts))
    win_parts = [float(v) for v in lines[n + 1].split()[:4]]
    if len(win_parts) < 4:
        raise ValueError("Ошибка в строке окна: нужно 4 числа (Xmin Ymin Xmax Ymax).")
    xmin, ymin, xmax, ymax = win_parts
    if xmin > xmax:
        xmin, xmax = xmax, xmin
    if ymin > ymax:
        ymin, ymax = ymax, ymin
    return segments, (xmin, ymin, xmax, ymax)
