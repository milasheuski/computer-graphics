import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from bench_clip import run_clipping_benchmark
from clipping_engine import (
    EPS,
    cyrus_beck,
    ensure_ccw,
    is_convex_polygon,
    liang_barsky,
    sutherland_cohen,
    sutherland_hodgman_polygon,
)
from presets import (
    CONCAVE_SUBJECT_PRESETS,
    CORNER_CASES_INPUT,
    CYRUS_BECK_SEGMENTS,
    POLYGON_PRESETS,
    STANDARD_INPUT_EXAMPLE,
    parse_lab5_text,
)


st.set_page_config(page_title="Лабораторная работа №5", layout="wide")
st.title("Алгоритмы отсечения отрезков и многоугольников (ЛР №5, вариант 2)")
st.caption("Лианг-Барски (вариант 2), сравнение с Сазерлендом-Коэном, Сайрус-Бек, ε = 10⁻⁷ и бенчмарк")


def setup_axes(ax, title, bounds):
    xmin, ymin, xmax, ymax = bounds
    span = max(xmax - xmin, ymax - ymin, 4.0)
    pad = span * 0.14
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.axhline(0, color="#1F6FEB", linewidth=1.0, alpha=0.65)
    ax.axvline(0, color="#1F6FEB", linewidth=1.0, alpha=0.65)
    ax.grid(True, linestyle=":", color="#CBD5E1", linewidth=0.8)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title(title, fontsize=11)


mode = st.sidebar.radio(
    "Раздел лабораторной работы",
    [
        "Часть 1: Отсечение окном (Лианг-Барски vs Сазерленд-Коэн)",
        "Часть 2: Отсечение выпуклым многоугольником (Сайрус-Бек)",
        "Дополнительно: Отсечение многоугольника (Сазерленд-Ходжман)",
        "Стресс-тест / Бенчмарк (500 000 отрезков + AABB / Quadtree)",
    ],
)

if mode == "Часть 1: Отсечение окном (Лианг-Барски vs Сазерленд-Коэн)":
    src_type = st.sidebar.selectbox(
        "Набор входных данных",
        [
            "Стандартный пример (формат входного файла ЛР №5)",
            "Вырожденные случаи (Corner Cases, ε = 10⁻⁷)",
            "Загрузить .txt файл из условия",
        ],
    )

    if src_type == "Загрузить .txt файл из условия":
        up = st.sidebar.file_uploader("Файл формата n / отрезки / окно", type=["txt"])
        raw_text = up.getvalue().decode("utf-8", errors="replace") if up else STANDARD_INPUT_EXAMPLE
    elif src_type == "Вырожденные случаи (Corner Cases, ε = 10⁻⁷)":
        raw_text = st.sidebar.text_area("Входные данные (редактируемые)", value=CORNER_CASES_INPUT, height=250)
    else:
        raw_text = st.sidebar.text_area("Входные данные (редактируемые)", value=STANDARD_INPUT_EXAMPLE, height=250)

    try:
        segments, (wxmin, wymin, wxmax, wymax) = parse_lab5_text(raw_text)
    except ValueError as err:
        st.error(str(err))
        st.stop()

    all_x = [wxmin, wxmax] + [s[0] for s in segments] + [s[2] for s in segments]
    all_y = [wymin, wymax] + [s[1] for s in segments] + [s[3] for s in segments]
    bounds = (min(all_x), min(all_y), max(all_x), max(all_y))

    fig, ax = plt.subplots(figsize=(7.6, 6.2), dpi=130)
    setup_axes(ax, f"Отсечение отрезков окном [{wxmin:g}, {wymin:g}] × [{wxmax:g}, {wymax:g}] (ε = {EPS:g})", bounds)

    rect = patches.Rectangle(
        (wxmin, wymin),
        wxmax - wxmin,
        wymax - wymin,
        linewidth=2.0,
        edgecolor="#1F6FEB",
        facecolor="#DBEAFE",
        alpha=0.28,
        label="Отсекающее окно",
        zorder=2,
    )
    ax.add_patch(rect)

    table_rows = []
    tot_lb = {"Сравнения": 0, "Слож./Вычит.": 0, "Умнож./Дел.": 0, "Всего оп.": 0}
    tot_sc = {"Сравнения": 0, "Слож./Вычит.": 0, "Умнож./Дел.": 0, "Всего оп.": 0}

    for idx, (x1, y1, x2, y2) in enumerate(segments, start=1):
        st_lb, clip_lb, t_pair, ops_lb = liang_barsky(x1, y1, x2, y2, wxmin, wymin, wxmax, wymax)
        st_sc, clip_sc, codes, iters, ops_sc = sutherland_cohen(x1, y1, x2, y2, wxmin, wymin, wxmax, wymax)

        for k in tot_lb:
            tot_lb[k] += ops_lb.to_dict()[k]
            tot_sc[k] += ops_sc.to_dict()[k]

        lbl_orig = "Исходные отрезки" if idx == 1 else None
        if abs(x1 - x2) <= EPS and abs(y1 - y2) <= EPS:
            ax.scatter([x1], [y1], color="#64748B", s=42, zorder=3, label=lbl_orig)
        else:
            ax.plot([x1, x2], [y1, y2], color="#94A3B8", linestyle="--", linewidth=1.3, zorder=3, label=lbl_orig)

        if clip_lb is not None:
            cx1, cy1, cx2, cy2 = clip_lb
            lbl_vis = "Видимые части (Лианг-Барски)" if idx == 1 or "Видимые части (Лианг-Барски)" not in ax.get_legend_handles_labels()[1] else None
            if abs(cx1 - cx2) <= EPS and abs(cy1 - cy2) <= EPS:
                ax.scatter([cx1], [cy1], color="#16A34A", s=70, zorder=5, label=lbl_vis)
            else:
                ax.plot([cx1, cx2], [cy1, cy2], color="#16A34A", linewidth=2.8, zorder=5, label=lbl_vis)
                ax.scatter([cx1, cx2], [cy1, cy2], color="#15803D", s=26, zorder=6)

        ax.text(x1, y1, f" {idx}", fontsize=8.5, color="#334155")

        vis_str = (
            f"({clip_lb[0]:.3g}; {clip_lb[1]:.3g}) → ({clip_lb[2]:.3g}; {clip_lb[3]:.3g})"
            if clip_lb is not None
            else "—"
        )
        t_str = f"[{t_pair[0]:.3f}; {t_pair[1]:.3f}]" if t_pair is not None else "—"
        table_rows.append({
            "№": idx,
            "Исходный отрезок": f"({x1:g}; {y1:g}) → ({x2:g}; {y2:g})",
            "Статус (Лианг-Барски)": st_lb,
            "Видимая часть": vis_str,
            "t0..t1": t_str,
            "Коды Коэна": f"{codes[0]:04b} / {codes[1]:04b}",
            "Оп. ЛБ": ops_lb.to_dict()["Всего оп."],
            "Оп. СК": ops_sc.to_dict()["Всего оп."],
        })

    ax.legend(loc="upper right", fontsize=8.5)
    fig.tight_layout()

    col_plot, col_info = st.columns([1.25, 1.0])
    with col_plot:
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    with col_info:
        st.subheader("Счётчик операций (Лианг-Барски vs Сазерленд-Коэн)")
        df_ops = pd.DataFrame([
            {"Алгоритм": "Лианг-Барски (вариант 2)", **tot_lb},
            {"Алгоритм": "Сазерленд-Коэн", **tot_sc},
        ])
        st.dataframe(df_ops, hide_index=True, use_container_width=True)

        st.subheader("Таблица отсечения и вырожденных случаев")
        st.dataframe(pd.DataFrame(table_rows), hide_index=True, use_container_width=True, height=390)

elif mode == "Часть 2: Отсечение выпуклым многоугольником (Сайрус-Бек)":
    poly_name = st.sidebar.selectbox("Отсекающий выпуклый многоугольник", list(POLYGON_PRESETS.keys()))
    poly_default = "\n".join(f"{x:g} {y:g}" for x, y in POLYGON_PRESETS[poly_name])
    poly_text = st.sidebar.text_area("Вершины многоугольника (X Y)", value=poly_default, height=160)

    seg_default = "\n".join(f"{a:g} {b:g} {c:g} {d:g}" for a, b, c, d in CYRUS_BECK_SEGMENTS)
    seg_text = st.sidebar.text_area("Отрезки (X1 Y1 X2 Y2)", value=seg_default, height=180)
    show_normals = st.sidebar.checkbox("Показывать внутренние нормали рёбер", value=True)

    try:
        polygon = []
        for line in poly_text.strip().splitlines():
            if line.strip():
                px, py = [float(v) for v in line.split()[:2]]
                polygon.append((px, py))
        segments = []
        for line in seg_text.strip().splitlines():
            if line.strip():
                a, b, c, d = [float(v) for v in line.split()[:4]]
                segments.append((a, b, c, d))
    except Exception:
        st.error("Проверьте формат координат: по 2 числа на строку для вершин и по 4 для отрезков.")
        st.stop()

    if not is_convex_polygon(polygon):
        st.error("Заданный многоугольник не является выпуклым (алгоритм Сайруса-Бека требует выпуклый отсекатель).")
        st.stop()

    ccw_poly = ensure_ccw(polygon)
    all_x = [p[0] for p in ccw_poly] + [s[0] for s in segments] + [s[2] for s in segments]
    all_y = [p[1] for p in ccw_poly] + [s[1] for s in segments] + [s[3] for s in segments]
    bounds = (min(all_x), min(all_y), max(all_x), max(all_y))

    fig, ax = plt.subplots(figsize=(7.6, 6.2), dpi=130)
    setup_axes(ax, "Отсечение отрезков выпуклым многоугольником (алгоритм Сайруса-Бека)", bounds)

    poly_patch = patches.Polygon(
        ccw_poly,
        closed=True,
        linewidth=2.0,
        edgecolor="#1F6FEB",
        facecolor="#DBEAFE",
        alpha=0.28,
        label="Выпуклый отсекатель",
        zorder=2,
    )
    ax.add_patch(poly_patch)

    if show_normals:
        n_p = len(ccw_poly)
        for i in range(n_p):
            vx1, vy1 = ccw_poly[i]
            vx2, vy2 = ccw_poly[(i + 1) % n_p]
            mx, my = 0.5 * (vx1 + vx2), 0.5 * (vy1 + vy2)
            ex, ey = vx2 - vx1, vy2 - vy1
            length = max(np.hypot(ex, ey), 1e-9)
            nx, ny = -ey / length, ex / length
            ax.arrow(mx, my, nx * 0.9, ny * 0.9, head_width=0.28, color="#2563EB", alpha=0.75, zorder=4)

    rows = []
    for idx, (x1, y1, x2, y2) in enumerate(segments, start=1):
        status, clipped, t_pair, ops = cyrus_beck(x1, y1, x2, y2, ccw_poly)
        lbl_orig = "Исходные отрезки" if idx == 1 else None
        if abs(x1 - x2) <= EPS and abs(y1 - y2) <= EPS:
            ax.scatter([x1], [y1], color="#64748B", s=42, zorder=3, label=lbl_orig)
        else:
            ax.plot([x1, x2], [y1, y2], color="#94A3B8", linestyle="--", linewidth=1.3, zorder=3, label=lbl_orig)

        if clipped is not None:
            cx1, cy1, cx2, cy2 = clipped
            lbl_vis = "Видимые части (Сайрус-Бек)" if "Видимые части (Сайрус-Бек)" not in ax.get_legend_handles_labels()[1] else None
            if abs(cx1 - cx2) <= EPS and abs(cy1 - cy2) <= EPS:
                ax.scatter([cx1], [cy1], color="#DC2626", s=70, zorder=5, label=lbl_vis)
            else:
                ax.plot([cx1, cx2], [cy1, cy2], color="#DC2626", linewidth=2.8, zorder=5, label=lbl_vis)
                ax.scatter([cx1, cx2], [cy1, cy2], color="#991B1B", s=26, zorder=6)

        ax.text(x1, y1, f" {idx}", fontsize=8.5, color="#334155")
        vis_str = (
            f"({clipped[0]:.3g}; {clipped[1]:.3g}) → ({clipped[2]:.3g}; {clipped[3]:.3g})"
            if clipped is not None
            else "—"
        )
        t_str = f"[{t_pair[0]:.3f}; {t_pair[1]:.3f}]" if t_pair is not None else "—"
        rows.append({
            "№": idx,
            "Отрезок": f"({x1:g}; {y1:g}) → ({x2:g}; {y2:g})",
            "Статус": status,
            "Видимая часть": vis_str,
            "t_вх..t_вых": t_str,
            "Всего оп.": ops.to_dict()["Всего оп."],
        })

    ax.legend(loc="upper right", fontsize=8.5)
    fig.tight_layout()

    col_plot, col_tbl = st.columns([1.25, 1.0])
    with col_plot:
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
    with col_tbl:
        st.subheader("Результаты отсечения (Сайрус-Бек)")
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True, height=480)

elif mode == "Дополнительно: Отсечение многоугольника (Сазерленд-Ходжман)":
    subj_name = st.sidebar.selectbox("Отсекаемый многоугольник", list(CONCAVE_SUBJECT_PRESETS.keys()))
    clip_name = st.sidebar.selectbox("Выпуклый отсекатель", list(POLYGON_PRESETS.keys()))

    subj_poly = CONCAVE_SUBJECT_PRESETS[subj_name]
    clip_poly = ensure_ccw(POLYGON_PRESETS[clip_name])
    result_poly = sutherland_hodgman_polygon(subj_poly, clip_poly)

    all_x = [p[0] for p in subj_poly] + [p[0] for p in clip_poly]
    all_y = [p[1] for p in subj_poly] + [p[1] for p in clip_poly]
    bounds = (min(all_x), min(all_y), max(all_x), max(all_y))

    fig, ax = plt.subplots(figsize=(7.6, 6.2), dpi=130)
    setup_axes(ax, "Отсечение многоугольника (алгоритм Сазерленда-Ходжмана)", bounds)

    ax.add_patch(
        patches.Polygon(
            clip_poly,
            closed=True,
            linewidth=2.0,
            edgecolor="#1F6FEB",
            facecolor="#DBEAFE",
            alpha=0.25,
            label="Отсекающий многоугольник",
        )
    )
    ax.add_patch(
        patches.Polygon(
            subj_poly,
            closed=True,
            linewidth=1.5,
            linestyle="--",
            edgecolor="#64748B",
            facecolor="none",
            label="Исходный многоугольник",
        )
    )
    if len(result_poly) >= 3:
        ax.add_patch(
            patches.Polygon(
                result_poly,
                closed=True,
                linewidth=2.5,
                edgecolor="#16A34A",
                facecolor="#86EFAC",
                alpha=0.55,
                label="Отсечённый многоугольник",
            )
        )
        rx = [p[0] for p in result_poly]
        ry = [p[1] for p in result_poly]
        ax.scatter(rx, ry, color="#15803D", s=34, zorder=5)

    ax.legend(loc="upper right", fontsize=8.5)
    fig.tight_layout()

    c1, c2 = st.columns([1.25, 1.0])
    with c1:
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)
    with c2:
        st.subheader("Вершины результирующего контура")
        st.caption(f"Исходных вершин: {len(subj_poly)} → после отсечения: {len(result_poly)}")
        df_v = pd.DataFrame(
            [{"№": i + 1, "X": round(x, 4), "Y": round(y, 4)} for i, (x, y) in enumerate(result_poly)]
        )
        st.dataframe(df_v, hide_index=True, use_container_width=True)

else:
    n_bench = st.number_input("Количество случайных отрезков", min_value=50000, max_value=1000000, value=500000, step=50000)
    if st.button("Запустить бенчмарк", type="primary"):
        with st.spinner("Генерация 500 000 отрезков, построение Quadtree и замер времени…"):
            df_sum, df_scale, build_t = run_clipping_benchmark(int(n_bench))
        st.session_state["bench_lab5"] = (df_sum, df_scale, build_t)

    if "bench_lab5" in st.session_state:
        df_sum, df_scale, build_t = st.session_state["bench_lab5"]
        st.caption(f"Время однократного построения индекса Quadtree: {build_t} с")
        st.subheader("Сравнение производительности отсечения")
        st.dataframe(df_sum, hide_index=True, use_container_width=True)

        st.subheader("Зависимость времени от количества отрезков")
        piv = df_scale.pivot(index="Отрезков", columns="Метод", values="Время, с")
        st.line_chart(piv)
