from io import BytesIO
from time import perf_counter

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

from processing import (
    mean_filter,
    gaussian_filter,
    histogram,
    linear_contrast,
    equalize_gray,
    equalize_rgb,
    equalize_hsv,
    clahe_gray,
    clahe_rgb,
    clahe_hsv,
)
from samples import get_sample_images


st.set_page_config(page_title="Лабораторная работа №3", layout="wide")
st.title("Основы обработки цифровых изображений (ЛР №3, вариант 2)")
st.caption("Разделяемые низкочастотные фильтры, гистограммы, линейное контрастирование, эквализация и CLAHE")

samples = get_sample_images()

source_mode = st.sidebar.radio(
    "Источник изображения",
    ["Тестовая база (встроенные)", "Загрузить свой файл"]
)

if source_mode == "Тестовая база (встроенные)":
    sample_name = st.sidebar.selectbox("Выберите тестовый пример", list(samples.keys()))
    image = samples[sample_name]
else:
    uploaded = st.sidebar.file_uploader("Файл изображения", type=["png", "jpg", "jpeg", "bmp"])
    if uploaded is None:
        st.info("Загрузите изображение или переключитесь на встроенную тестовую базу в панели слева.")
        st.stop()
    try:
        image = ImageOps.exif_transpose(Image.open(uploaded)).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        st.error("Не удалось прочитать изображение.")
        st.stop()

if max(image.size) > 1200:
    image = image.copy()
    image.thumbnail((1200, 1200))

section = st.sidebar.selectbox(
    "Режим обработки",
    [
        "Низкочастотная фильтрация (сглаживание)",
        "Контраст полутонового изображения",
        "Эквализация и CLAHE цветного (RGB vs HSV)",
        "Сравнение обработки краёв (Reflect vs Clamp)",
    ]
)

workers = st.sidebar.selectbox("Потоки (ThreadPool)", [1, 2, 4, 8], index=2)

started = perf_counter()

if section == "Низкочастотная фильтрация (сглаживание)":
    size = st.sidebar.select_slider("Размер ядра (K)", options=[3, 5, 7, 9, 11], value=5)
    sigma = st.sidebar.slider("Сигма Гаусса (σ)", min_value=0.5, max_value=5.0, value=1.4, step=0.1)
    pad_strategy = st.sidebar.radio("Обработка краёв", ["Reflect", "Clamp"], horizontal=True)

    results = [
        ("Исходное", image, "original"),
        (f"Бокс-фильтр ({size}×{size})", mean_filter(image, size, pad_strategy, workers), "box"),
        (f"Гаусс ({size}×{size}, σ={sigma})", gaussian_filter(image, size, sigma, pad_strategy, workers), "gauss"),
    ]

elif section == "Контраст полутонового изображения":
    gray = image.convert("L")
    grid_size = st.sidebar.slider("Сетка блоков CLAHE", min_value=2, max_value=16, value=8)
    clip_limit = st.sidebar.slider("Ограничение контраста (Clip Limit)", min_value=1.0, max_value=8.0, value=2.5, step=0.5)

    results = [
        ("Исходное (Gray)", gray, "gray"),
        ("Линейное контрастирование", linear_contrast(gray), "linear"),
        ("Глобальная эквализация", equalize_gray(gray), "eq_gray"),
        ("CLAHE (адаптивная)", clahe_gray(gray, grid_size, clip_limit), "clahe_gray"),
    ]

elif section == "Эквализация и CLAHE цветного (RGB vs HSV)":
    grid_size = st.sidebar.slider("Сетка блоков CLAHE", min_value=2, max_value=16, value=8)
    clip_limit = st.sidebar.slider("Ограничение контраста (Clip Limit)", min_value=1.0, max_value=8.0, value=2.5, step=0.5)

    results = [
        ("Исходное RGB", image, "orig_rgb"),
        ("Эквализация RGB (поканально)", equalize_rgb(image), "eq_rgb"),
        ("Эквализация HSV (только V)", equalize_hsv(image), "eq_hsv"),
        ("CLAHE HSV (только V)", clahe_hsv(image, grid_size, clip_limit), "clahe_hsv"),
    ]

else:
    size = st.sidebar.select_slider("Размер ядра (K)", options=[5, 7, 9, 11], value=9)
    sigma = st.sidebar.slider("Сигма Гаусса (σ)", min_value=1.0, max_value=5.0, value=2.5, step=0.1)

    results = [
        ("Исходное", image, "orig_edge"),
        ("Гаусс + Reflect (отражение)", gaussian_filter(image, size, sigma, "reflect", workers), "reflect"),
        ("Гаусс + Clamp (повтор края)", gaussian_filter(image, size, sigma, "clamp", workers), "clamp"),
    ]

elapsed = perf_counter() - started

m1, m2, m3 = st.columns(3)
m1.metric("Разрешение", f"{image.size[0]} × {image.size[1]} px")
m2.metric("Время обработки", f"{elapsed * 1000:.1f} мс")
m3.metric("Потоков", str(workers))

show_rgb = st.checkbox("Показывать гистограммы по каналам R, G, B", value=False)

charts = []
for _, result, _ in results:
    if show_rgb and result.mode == "RGB":
        pixels = np.asarray(result)
        data = pd.DataFrame({
            ch: np.bincount(pixels[:, :, i].ravel(), minlength=256)
            for i, ch in enumerate(["R", "G", "B"])
        })
    else:
        data = pd.DataFrame({"Яркость": histogram(result)})
    charts.append(data)

maximum_count = max(1, max(int(df.to_numpy().max()) for df in charts))

columns = st.columns(len(results))
for column, (title, result, key), data in zip(columns, results, charts):
    with column:
        st.subheader(title)
        st.image(result, use_container_width=True)

        plot_data = (
            data.rename_axis("Значение")
            .reset_index()
            .melt(id_vars="Значение", var_name="Канал", value_name="Количество")
        )

        chart = alt.Chart(plot_data).mark_line().encode(
            x=alt.X("Значение:Q", scale=alt.Scale(domain=[0, 255])),
            y=alt.Y("Количество:Q", scale=alt.Scale(domain=[0, maximum_count])),
            color=alt.Color(
                "Канал:N",
                scale=alt.Scale(
                    domain=["R", "G", "B", "Яркость"],
                    range=["red", "green", "blue", "gray"]
                )
            )
        )
        st.altair_chart(chart, use_container_width=True)

        buf = BytesIO()
        result.save(buf, format="PNG")
        st.download_button(
            "Скачать PNG",
            data=buf.getvalue(),
            file_name=f"{key}.png",
            mime="image/png",
            key=key
        )
