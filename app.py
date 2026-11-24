from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
import csv
import io
import os
import streamlit as st
from metadata import read_image, read_uploaded_batch


st.set_page_config(page_title="Лабораторная 2 — Метаданные изображений", layout="wide")
st.title("Информация об изображениях (ЛР №2)")
st.caption("JPEG, GIF, TIFF, BMP, PNG, PCX · ручной побайтовый парсинг заголовков и тегов")

PUBLIC_COLUMNS = [
    "Файл",
    "Формат",
    "Размер, px",
    "DPI, X × Y",
    "Глубина, бит/пиксель",
    "Сжатие",
    "Статус",
    "Примечание",
]

mode = st.radio(
    "Источник изображений:",
    [
        "Загрузка файлов или ZIP-архива (для веб-версии / проверки в облаке)",
        "Сканирование папки на диске (для локального теста до 100 000 файлов / 2 ГБ)",
    ],
    horizontal=True,
)

if mode.startswith("Загрузка"):
    uploaded = st.file_uploader(
        "Выберите изображения (JPG, PNG, GIF, BMP, TIF, PCX) или целый ZIP-архив",
        accept_multiple_files=True,
    )
    if st.button("Обработать загруженные файлы", type="primary"):
        if not uploaded:
            st.warning("Сначала перетащите файлы или ZIP-архив в область выше.")
        else:
            started = perf_counter()
            with st.spinner("Побайтовый разбор заголовков…"):
                rows = read_uploaded_batch(uploaded)
            st.session_state["rows"] = rows
            st.session_state["seconds"] = perf_counter() - started
else:
    col_path, col_threads = st.columns([3, 1])
    with col_path:
        folder_text = st.text_input("Путь к папке на сервере/ПК", placeholder=r"C:\Users\Student\Pictures")
    with col_threads:
        threads = st.selectbox("Потоки (ThreadPool)", [1, 2, 4, 8, 16], index=2)
    subfolders = st.checkbox("Включать вложенные папки", value=True)

    if st.button("Прочитать папку", type="primary"):
        st.session_state.pop("rows", None)
        folder = Path(folder_text.strip().strip('"')).expanduser()
        if not folder_text.strip() or not folder.is_dir():
            st.error("Укажите существующую папку. При запуске в облаке используйте вкладку «Загрузка файлов или ZIP-архива».")
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
                progress = st.progress(0, text="Читаем заголовки…")
                rows = []
                batch_size = max(128, len(files) // 60)
                with ThreadPoolExecutor(max_workers=threads) as pool:
                    for start in range(0, len(files), batch_size):
                        rows.extend(pool.map(read_image, files[start:start + batch_size]))
                        progress.progress(
                            min(1.0, len(rows) / len(files)),
                            text=f"Обработано: {len(rows)} из {len(files)}",
                        )
                st.session_state["rows"] = rows
                st.session_state["seconds"] = perf_counter() - started
            for error in errors:
                st.warning("Часть папок недоступна: " + error)

if "rows" in st.session_state and st.session_state["rows"]:
    rows = st.session_state["rows"]
    elapsed = st.session_state["seconds"]
    ok_count = sum(1 for r in rows if r["Статус"] == "OK")
    warn_count = len(rows) - ok_count

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Всего файлов", len(rows))
    m2.metric("Валидных (OK)", ok_count)
    m3.metric("С замечаниями / битых", warn_count)
    m4.metric("Время обработки", f"{elapsed:.3f} с")

    fmt_counts = Counter(r["Формат"] for r in rows)
    st.caption("Распределение по форматам: " + " · ".join(f"**{k}**: {v}" for k, v in fmt_counts.items()))

    f1, f2 = st.columns([1, 2])
    with f1:
        only_errors = st.checkbox("Показать только файлы с замечаниями / битые")
    with f2:
        search_q = st.text_input("Фильтр по имени файла или формату", placeholder="Например: .jpg или поврежден")

    visible = rows
    if only_errors:
        visible = [r for r in visible if r["Статус"] != "OK"]
    if search_q.strip():
        q = search_q.strip().lower()
        visible = [r for r in visible if q in r["Файл"].lower() or q in r["Формат"].lower() or q in r["Статус"].lower()]

    pages = max(1, (len(visible) + 199) // 200)
    page = st.number_input("Страница (по 200 строк)", min_value=1, max_value=pages, value=1)
    page_slice = visible[(page - 1) * 200:page * 200]
    table_data = [{col: r[col] for col in PUBLIC_COLUMNS} for r in page_slice]
    st.dataframe(table_data, hide_index=True, use_container_width=True)

    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=PUBLIC_COLUMNS, delimiter=";")
    writer.writeheader()
    for r in rows:
        writer.writerow({col: r[col] for col in PUBLIC_COLUMNS})
    st.download_button(
        "Скачать полную таблицу (CSV для Excel)",
        output.getvalue().encode("utf-8-sig"),
        "lab2_metadata.csv",
        "text/csv",
    )

    st.divider()
    st.subheader("Детальный инспектор файла (доп. характеристики и матрицы квантования)")
    selected_name = st.selectbox("Выберите файл из обработанных:", [r["Файл"] for r in rows[:2000]])
    selected_row = next(r for r in rows if r["Файл"] == selected_name)

    col_info, col_preview = st.columns([2, 1])
    with col_info:
        st.write(f"**Статус:** {selected_row['Статус']} — {selected_row['Примечание']}")
        if selected_row.get("_extra"):
            st.table([{"Параметр": k, "Значение": str(v)} for k, v in selected_row["_extra"].items()])
        if selected_row.get("_quant"):
            st.markdown("**Матрицы квантования JPEG 8×8 (из маркера `FF DB` / DQT после обратного зигзаг-сканирования):**")
            for tid, matrix in sorted(selected_row["_quant"].items()):
                label = "Яркостная (Y, ID=0)" if tid == 0 else ("Цветностная (Cb/Cr, ID=1)" if tid == 1 else f"Таблица ID={tid}")
                st.caption(label)
                st.dataframe(matrix, hide_index=True)
    with col_preview:
        if selected_row["Статус"] in ("OK", "Расширение не совпадает с форматом"):
            try:
                if "_preview_bytes" in selected_row:
                    st.image(selected_row["_preview_bytes"], caption="Предпросмотр", use_container_width=True)
                elif Path(selected_row["Файл"]).is_file():
                    st.image(selected_row["Файл"], caption="Предпросмотр", use_container_width=True)
            except Exception:
                st.info("Предпросмотр недоступен для данного формата в браузере.")

with st.expander("Справка к защите: откуда берутся характеристики?"):
    st.markdown("""
    - **Сигнатура (Magic Numbers):** первые байты файла определяют реальный формат независимо от расширения (`89 50 4E 47` — PNG, `FF D8` — JPEG, `BM` — BMP, `GIF87a/89a` — GIF, `II/MM` + `42` — TIFF, `0A` — PCX).
    - **Размер, px:** ширина и высота из заголовка (`IHDR` в PNG, маркер `SOF0..SOF15` в JPEG, `BITMAPINFOHEADER` в BMP, теги `256/257` в TIFF).
    - **DPI (разрешение):** плотность пикселей при печати. Извлекается из чанка `pHYs` (PNG, пересчёт из пикселей/метр × `0.0254`), `APP1 EXIF` / `APP0 JFIF` (JPEG), полей `biXPelsPerMeter/biYPelsPerMeter` (BMP), тегов `282/283/296` (TIFF). Если не указано — подставляется стандартное экранное `96 DPI`. У GIF абсолютный DPI не предусмотрен.
    - **Глубина цвета:** число бит на пиксель до сжатия (`BitDepth × Channels` в PNG и JPEG, `biBitCount` в BMP, сумма тега `258 BitsPerSample` в TIFF, биты индекса палитры в GIF).
    - **Сжатие:** алгоритм упаковки растра (`Deflate` в PNG, `DCT + Хаффман` в JPEG, `LZW` в GIF, `BI_RGB / RLE8 / RLE4` в BMP, `RLE` в PCX).
    - **Матрицы квантования JPEG (`FF DB`):** таблицы 8×8, на коэффициенты которых делятся значения дискретного косинусного преобразования (DCT). Чем больше числа в матрице, тем сильнее сжимаются высокие частоты и тем выше степень сжатия с потерями.
    """)