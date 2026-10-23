from io import BytesIO

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
    equalize_hsv
)


st.set_page_config(
    page_title="Обработка изображений",
    layout="wide"
)

st.title("Обработка изображений")
st.write("Сглаживание, гистограммы и повышение контраста")

uploaded = st.file_uploader(
    "Загрузите изображение",
    type=["png", "jpg", "jpeg", "bmp"]
)

if uploaded is None:
    st.info("Прикрепите изображение, чтобы начать обработку.")
    st.stop()

try:
    image = ImageOps.exif_transpose(
        Image.open(uploaded)
    ).convert("RGB")
except (
    UnidentifiedImageError,
    OSError,
    Image.DecompressionBombError
):
    st.error("Не удалось прочитать изображение. Выберите другой файл.")
    st.stop()

if max(image.size) > 1200:
    image.thumbnail((1200, 1200))

    st.caption(
        "Для быстрой обработки изображение уменьшено "
        "до 1200 пикселей по большей стороне. "
        "Результат будет сохранён в уменьшенном размере."
    )

section = st.sidebar.selectbox(
    "Раздел",
    [
        "Сглаживание",
        "Контраст серого изображения",
        "Эквализация цветного изображения"
    ]
)

if section == "Сглаживание":
    size = st.sidebar.select_slider(
        "Размер фильтра",
        options=[3, 5, 7, 9, 11],
        value=3
    )

    sigma = st.sidebar.slider(
        "Сигма Гаусса",
        min_value=0.5,
        max_value=5.0,
        value=1.0,
        step=0.1
    )

    results = [
        ("Исходное", image, "original"),
        ("Усреднение", mean_filter(image, size), "mean"),
        ("Гаусс", gaussian_filter(image, size, sigma), "gaussian")
    ]

    explanation = (
        "Усредняющий фильтр даёт одинаковый вес всем соседям. "
        "Фильтр Гаусса сильнее учитывает близкие пиксели. "
        "Оба фильтра подавляют шум, но размывают границы. "
        "Размер задаёт область соседей, "
        "сигма — распределение весов Гаусса."
    )

elif section == "Контраст серого изображения":
    gray = image.convert("L")

    results = [
        ("Исходное серое", gray, "gray"),
        (
            "Линейное контрастирование",
            linear_contrast(gray),
            "linear"
        ),
        ("Эквализация", equalize_gray(gray), "equalized")
    ]

    explanation = (
        "Линейное контрастирование растягивает диапазон "
        "от минимальной до максимальной яркости на 0–255. "
        "Эквализация перераспределяет яркости "
        "по накопленной гистограмме. "
        "Если изображение уже содержит значения 0 и 255, "
        "линейное растяжение не изменит его. "
        "Однотонное изображение сохраняется без изменений."
    )

else:
    results = [
        ("Исходное RGB", image, "color"),
        ("Эквализация RGB", equalize_rgb(image), "rgb"),
        ("Эквализация V в HSV", equalize_hsv(image), "hsv")
    ]

    explanation = (
        "В RGB каждый цветовой канал выравнивается отдельно, "
        "поэтому оттенки могут измениться. "
        "В HSV изменяется только V, а H и S сохраняются "
        "до обратного преобразования. "
        "Это обычно лучше сохраняет цветовую гамму. "
        "V — максимум компонент RGB. "
        "При преобразовании возможны округления."
    )

st.info(explanation)

show_rgb = st.checkbox(
    "Показывать гистограммы R, G, B",
    value=False
)

charts = []

for title, result, key in results:
    if show_rgb and result.mode == "RGB":
        pixels = np.asarray(result)

        data = pd.DataFrame({
            channel: np.bincount(
                pixels[:, :, i].ravel(),
                minlength=256
            )
            for i, channel in enumerate(["R", "G", "B"])
        })

    else:
        data = pd.DataFrame({
            "Яркость": histogram(result)
        })

    charts.append(data)

maximum_count = max(
    int(data.to_numpy().max())
    for data in charts
)

columns = st.columns(3)

for column, item, data in zip(columns, results, charts):
    title, result, key = item

    with column:
        st.subheader(title)
        st.image(result, width="stretch")

        plot_data = (
            data
            .rename_axis("Значение")
            .reset_index()
            .melt(
                id_vars="Значение",
                var_name="Канал",
                value_name="Количество"
            )
        )

        chart = alt.Chart(plot_data).mark_line().encode(
            x=alt.X(
                "Значение:Q",
                scale=alt.Scale(domain=[0, 255])
            ),
            y=alt.Y(
                "Количество:Q",
                scale=alt.Scale(domain=[0, maximum_count])
            ),
            color=alt.Color(
                "Канал:N",
                scale=alt.Scale(
                    domain=["R", "G", "B", "Яркость"],
                    range=["red", "green", "blue", "gray"]
                )
            )
        )

        st.altair_chart(chart, width="stretch")

        buffer = BytesIO()
        result.save(buffer, format="PNG")

        st.download_button(
            "Скачать PNG",
            data=buffer.getvalue(),
            file_name=f"{key}.png",
            mime="image/png",
            key=key
        )

st.caption(
    "Гистограмма: по горизонтали — значение от 0 до 255, "
    "по вертикали — количество пикселей. "
    "Масштаб одинаков для трёх графиков. "
    "Без флажка RGB показана гистограмма изображения "
    "в оттенках серого. "
    "Все методы применяются к исходному изображению."
)