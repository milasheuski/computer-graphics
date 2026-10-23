"""Лабораторная 2. Запуск: python -m streamlit run app.py"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
import csv
import io
import os
import streamlit as st
from metadata import read_image


st.set_page_config(page_title="Лабораторная 2", layout="wide")
st.title("Информация об изображениях")
st.caption("JPEG, GIF, TIFF, BMP, PNG, PCX · ручное чтение заголовков")
folder_text = st.text_input("Путь к папке на этом компьютере", placeholder=r"C:\Users\Student\Pictures")
subfolders = st.checkbox("Включать вложенные папки", value=True)
threads = st.selectbox("Количество потоков", [1, 2, 4, 8], index=2)

if st.button("Прочитать папку", type="primary"):
    st.session_state.pop("rows", None)
    folder = Path(folder_text.strip().strip('"')).expanduser()
    if not folder_text.strip() or not folder.is_dir():
        st.error("Укажите существующую папку. Можно скопировать её путь из Проводника.")
    else:
        started, files, errors = perf_counter(), [], []
        with st.spinner("Составляем список файлов…"):
            for directory, _, names in os.walk(folder, onerror=lambda e: errors.append(str(e))):
                files.extend(Path(directory) / name for name in names)
                if len(files) > 100000 or not subfolders:
                    break
        if len(files) > 100000:
            st.error("В папке больше 100 000 файлов. Выберите меньшую папку.")
        elif not files:
            st.warning("В папке нет доступных файлов.")
        else:
            progress, rows = st.progress(0, text="Читаем заголовки…"), []
            with ThreadPoolExecutor(max_workers=threads) as pool:
                # Отправляем небольшие партии, а не 100 000 задач сразу.
                for start in range(0, len(files), 128):
                    rows.extend(pool.map(read_image, files[start:start + 128]))
                    progress.progress(len(rows) / len(files), text=f"Обработано: {len(rows)} из {len(files)}")
            st.session_state["rows"] = rows
            st.session_state["seconds"] = perf_counter() - started
        for error in errors:
            st.warning("Часть папок недоступна: " + error)

if "rows" in st.session_state:
    rows = st.session_state["rows"]
    st.success(f"Обработано файлов: {len(rows)}. Время: {st.session_state['seconds']:.2f} с")
    only_errors = st.checkbox("Показать только файлы с замечаниями")
    visible = [row for row in rows if row["Статус"] != "OK"] if only_errors else rows
    # На экран выводим одну страницу, чтобы большая таблица не тормозила.
    pages = max(1, (len(visible) + 199) // 200)
    page = st.number_input("Страница (по 200 строк)", min_value=1, max_value=pages, value=1)
    st.dataframe(visible[(page - 1) * 200:page * 200], hide_index=True, use_container_width=True)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    st.download_button("Скачать все результаты (CSV)", output.getvalue().encode("utf-8-sig"), "results.csv", "text/csv")

with st.expander("Что означают характеристики?"):
    st.markdown("""
    - **Размер, px** — ширина и высота в пикселях.
    - **DPI** — плотность пикселей по горизонтали и вертикали при печати. Если она не записана, принимается 96 DPI с пометкой «по умолчанию». Это условное значение, а не результат расчёта. У GIF абсолютный DPI не предусмотрен.
    - **Глубина** — число бит на пиксель в структуре изображения до сжатия, включая alpha. В палитровых изображениях — биты индекса цвета.
    - **Сжатие** — способ хранения пикселей в меньшем объёме. Не определяет размеры изображения.
    - **OK** — проверены заголовки и доступные структурные признаки. Полное декодирование пикселей не выполняется.
    """
    )
