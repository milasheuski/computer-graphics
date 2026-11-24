import matplotlib.pyplot as plt
import streamlit as st
from benchmark import run_benchmark
from grid_painter import GridPainter
from raster_engine import RasterEngine
from virtual_grid import VirtualGrid


st.set_page_config(page_title="Лабораторная работа №4", layout="wide")
st.title("Базовые растровые алгоритмы (ЛР №4)")
st.caption("Пошаговый, ЦДА, Брезенхем (отрезок и окружность), сглаживание Ву, Кастл-Питвей и бенчмарк")

mode = st.sidebar.radio(
    "Режим работы",
    [
        "Интерактивная растеризация и расчёты",
        "Сравнение всех 8 октантов («Веер»)",
        "Стресс-тест / Бенчмарк (100 000 отрезков + 50 000 окружностей)",
    ],
)

if mode == "Интерактивная растеризация и расчёты":
    algo = st.sidebar.selectbox(
        "Алгоритм",
        [
            "Пошаговый алгоритм (отрезок)",
            "Алгоритм ЦДА / DDA (отрезок)",
            "Алгоритм Брезенхема (отрезок)",
            "Алгоритм Ву / Anti-aliasing (отрезок)",
            "Алгоритм Кастла-Питвея (отрезок)",
            "Алгоритм Брезенхема (окружность)",
        ],
    )

    grid_radius = st.sidebar.slider("Размер сетки (от -N до +N)", min_value=8, max_value=40, value=15)
    show_overlay = st.sidebar.checkbox("Показывать идеальную геометрическую линию", value=True)

    grid = VirtualGrid(-grid_radius, grid_radius, -grid_radius, grid_radius, record_steps=True)

    if algo == "Алгоритм Брезенхема (окружность)":
        c1, c2, c3 = st.sidebar.columns(3)
        xc = c1.number_input("Xc", min_value=-grid_radius, max_value=grid_radius, value=0, step=1)
        yc = c2.number_input("Yc", min_value=-grid_radius, max_value=grid_radius, value=0, step=1)
        r = c3.number_input("R", min_value=1, max_value=grid_radius, value=min(9, grid_radius - 1), step=1)

        RasterEngine.bresenham_circle(grid, xc, yc, r)
        overlay = {"type": "circle", "xc": xc, "yc": yc, "r": r} if show_overlay else None
    else:
        c1, c2 = st.sidebar.columns(2)
        x0 = c1.number_input("X0", min_value=-grid_radius, max_value=grid_radius, value=-10, step=1)
        y0 = c2.number_input("Y0", min_value=-grid_radius, max_value=grid_radius, value=-4, step=1)
        x1 = c1.number_input("X1", min_value=-grid_radius, max_value=grid_radius, value=11, step=1)
        y1 = c2.number_input("Y1", min_value=-grid_radius, max_value=grid_radius, value=5, step=1)

        if algo == "Пошаговый алгоритм (отрезок)":
            RasterEngine.step_by_step_line(grid, x0, y0, x1, y1)
        elif algo == "Алгоритм ЦДА / DDA (отрезок)":
            RasterEngine.dda_line(grid, x0, y0, x1, y1)
        elif algo == "Алгоритм Брезенхема (отрезок)":
            RasterEngine.bresenham_line(grid, x0, y0, x1, y1)
        elif algo == "Алгоритм Ву / Anti-aliasing (отрезок)":
            RasterEngine.wu_line(grid, x0, y0, x1, y1)
        else:
            RasterEngine.castle_pitteway_line(grid, x0, y0, x1, y1)

        overlay = {"type": "line", "x0": x0, "y0": y0, "x1": x1, "y1": y1} if show_overlay else None

    col_plot, col_table = st.columns([1.25, 1.0])
    with col_plot:
        fig = GridPainter.render(grid, overlay=overlay, title=algo)
        st.pyplot(fig, use_container_width=True)
        plt.close(fig)

    with col_table:
        st.subheader("Сопроводительные вычисления по шагам")
        st.caption(f"Всего сгенерировано пикселей: {len(grid.steps)}")
        if grid.steps:
            st.dataframe(grid.steps, hide_index=True, use_container_width=True, height=520)

elif mode == "Сравнение всех 8 октантов («Веер»)":
    algo_fan = st.sidebar.selectbox(
        "Алгоритм для проверки 8 октантов",
        [
            "Алгоритм Брезенхема (отрезок)",
            "Алгоритм ЦДА / DDA (отрезок)",
            "Пошаговый алгоритм (отрезок)",
            "Алгоритм Ву / Anti-aliasing (отрезок)",
            "Алгоритм Кастла-Питвея (отрезок)",
        ],
    )
    radius = st.sidebar.slider("Радиус веера", min_value=10, max_value=25, value=16)
    grid = VirtualGrid(-radius - 2, radius + 2, -radius - 2, radius + 2, record_steps=False)

    endpoints = [
        (radius, 4),
        (6, radius),
        (-6, radius),
        (-radius, 4),
        (-radius, -4),
        (-6, -radius),
        (6, -radius),
        (radius, -4),
    ]

    for ex, ey in endpoints:
        if algo_fan == "Алгоритм Брезенхема (отрезок)":
            RasterEngine.bresenham_line(grid, 0, 0, ex, ey)
        elif algo_fan == "Алгоритм ЦДА / DDA (отрезок)":
            RasterEngine.dda_line(grid, 0, 0, ex, ey)
        elif algo_fan == "Пошаговый алгоритм (отрезок)":
            RasterEngine.step_by_step_line(grid, 0, 0, ex, ey)
        elif algo_fan == "Алгоритм Ву / Anti-aliasing (отрезок)":
            RasterEngine.wu_line(grid, 0, 0, ex, ey)
        else:
            RasterEngine.castle_pitteway_line(grid, 0, 0, ex, ey)

    fig = GridPainter.render(grid, title=f"Проверка всех 8 октантов: {algo_fan}")
    st.pyplot(fig, use_container_width=False)
    plt.close(fig)

else:
    c1, c2 = st.columns(2)
    n_lines = c1.number_input("Количество случайных отрезков", min_value=10000, max_value=200000, value=100000, step=10000)
    n_circles = c2.number_input("Количество случайных окружностей", min_value=5000, max_value=100000, value=50000, step=5000)

    if st.button("Запустить бенчмарк", type="primary"):
        with st.spinner("Генерация виртуального растра и замер времени…"):
            df_summary, df_scaling, df_length = run_benchmark(int(n_lines), int(n_circles))
        st.session_state["bench_lab4"] = (df_summary, df_scaling, df_length)

    if "bench_lab4" in st.session_state:
        df_summary, df_scaling, df_length = st.session_state["bench_lab4"]
        st.subheader("Сводная таблица производительности (чистый виртуальный растр)")
        st.dataframe(df_summary, hide_index=True, use_container_width=True)

        g1, g2 = st.columns(2)
        with g1:
            st.subheader("Зависимость времени от количества отрезков")
            piv_scale = df_scaling.pivot(index="Количество отрезков", columns="Алгоритм", values="Время, с")
            st.line_chart(piv_scale)
        with g2:
            st.subheader("Зависимость времени от длины отрезка")
            piv_len = df_length.pivot(index="Длина отрезка, px", columns="Алгоритм", values="Время (15 000 шт.), с")
            st.line_chart(piv_len)
