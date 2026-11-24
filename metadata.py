import io
import os
import struct
import zipfile
from pathlib import Path


def stream_size(file):
    current = file.tell()
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(current)
    return size


def read_at(file, offset, length, size=None):
    if size is None:
        size = stream_size(file)
    if offset < 0 or length < 0 or offset + length > size:
        raise ValueError("Данные обрезаны: чтение за границами файла")
    file.seek(offset)
    data = file.read(length)
    if len(data) != length:
        raise ValueError("Файл изменился или не удалось прочитать данные")
    return data


def number(data, offset, length, endian="little", signed=False):
    return int.from_bytes(data[offset:offset + length], endian, signed=signed)


def resolution(x, y, factor=1):
    return f"{x * factor:.2f} × {y * factor:.2f}" if x > 0 and y > 0 else "Не указано"


def png(file, size):
    position, result, has_pixels, has_end = 8, {}, False, False
    color_names = {0: "Grayscale", 2: "RGB", 3: "Indexed (палитра)", 4: "Grayscale + Alpha", 6: "RGBA"}
    palette_colors = None
    while position < size:
        header = read_at(file, position, 8, size)
        length = number(header, 0, 4, "big")
        kind = header[4:8]
        if position + length + 12 > size:
            raise ValueError("PNG: чанк обрезан")
        if not result and (kind != b"IHDR" or length != 13):
            raise ValueError("PNG: нет правильного IHDR")
        if kind == b"IHDR":
            if result or length != 13:
                raise ValueError("PNG: неправильный или повторный IHDR")
            data = read_at(file, position + 8, 13, size)
            width, height = struct.unpack(">II", data[:8])
            depth, color = data[8], data[9]
            allowed = {0: (1, 2, 4, 8, 16), 2: (8, 16), 3: (1, 2, 4, 8), 4: (8, 16), 6: (8, 16)}
            if depth not in allowed.get(color, ()) or data[10:12] != b"\x00\x00" or data[12] > 1:
                raise ValueError("PNG: неверные параметры IHDR")
            channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
            interlace = "Adam7" if data[12] == 1 else "Нет"
            result = dict(
                width=width,
                height=height,
                bits=depth * channels,
                dpi="Не указано",
                compression="Deflate",
                note=f"Тип: {color_names[color]}; фильтрация: метод 0; чересстрочность: {interlace}",
                extra={"Тип цвета PNG": color_names[color], "Метод фильтрации": "0 (адаптивная построчная)", "Чересстрочность": interlace},
            )
        elif kind == b"PLTE":
            if length % 3 != 0 or length == 0:
                raise ValueError("PNG: неверный чанк палитры PLTE")
            palette_colors = length // 3
        elif kind == b"pHYs":
            if length != 9:
                raise ValueError("PNG: неверный pHYs")
            data = read_at(file, position + 8, 9, size)
            if data[8] == 1:
                result["dpi"] = resolution(*struct.unpack(">II", data[:8]), 0.0254)
        elif kind == b"IDAT":
            has_pixels = True
        elif kind == b"IEND":
            if length != 0:
                raise ValueError("PNG: неверный IEND")
            has_end = True
            break
        position += length + 12
    if not has_end or not has_pixels:
        raise ValueError("PNG: отсутствует IEND или IDAT")
    if palette_colors is not None:
        result["note"] += f"; палитра: {palette_colors} цв."
        result["extra"]["Цветов в палитре PLTE"] = palette_colors
    return result


def bmp(file, size):
    header = read_at(file, 0, 18, size)
    declared, pixels, dib = (number(header, p, 4) for p in (2, 10, 14))
    if declared > size or pixels > size or pixels < 14 + dib:
        raise ValueError("BMP: неправильный размер или смещение")
    data = read_at(file, 14, dib if dib in (12, 40, 52, 56, 108, 124) else 4, size)
    if dib == 12:
        width, height, planes, bits = struct.unpack("<HHHH", data[4:12])
        compression, dpi, colors = 0, "Не указано", 0
    elif dib in (40, 52, 56, 108, 124):
        width, height, planes, bits, compression = struct.unpack("<iiHHI", data[4:20])
        height = abs(height)
        dpi = resolution(*struct.unpack("<ii", data[24:32]), 0.0254)
        colors = number(data, 32, 4)
        if pixels + number(data, 20, 4) > size:
            raise ValueError("BMP: массив пикселей обрезан")
    else:
        raise NotImplementedError(f"BMP: DIB-заголовок {dib} не поддерживается")
    if planes != 1 or bits not in (1, 2, 4, 8, 16, 24, 32):
        raise ValueError("BMP: неверные плоскости или глубина")
    if compression in (0, 3, 6) and pixels + ((width * bits + 31) // 32) * 4 * height > size:
        raise ValueError("BMP: массив пикселей обрезан")
    note = f"DIB-заголовок: {dib} байт"
    extra = {"Размер DIB-заголовка": f"{dib} байт", "Смещение пикселей (bfOffBits)": f"{pixels} байт"}
    if bits <= 8:
        colors = colors or 2 ** bits
        if colors > 2 ** bits or 14 + dib + colors * (3 if dib == 12 else 4) > pixels:
            raise ValueError("BMP: палитра обрезана")
        note += f"; цветов в палитре: {colors}"
        extra["Цветов в палитре"] = colors
    names = {
        0: "BI_RGB (без сжатия)",
        1: "BI_RLE8",
        2: "BI_RLE4",
        3: "BI_BITFIELDS",
        4: "BI_JPEG",
        5: "BI_PNG",
        6: "BI_ALPHABITFIELDS",
    }
    return dict(
        width=width,
        height=height,
        bits=bits,
        dpi=dpi,
        compression=names.get(compression, f"Код {compression}"),
        note=note,
        extra=extra,
    )


def gif(file, size):
    data = read_at(file, 0, 13, size)
    version = data[:6].decode("ascii")
    width, height = struct.unpack("<HH", data[6:10])
    global_bits = (data[10] & 7) + 1 if data[10] & 128 else 0
    position = 13 + (3 * 2 ** global_bits if global_bits else 0)
    frames, bits, ended = 0, 0, False
    while position < size:
        kind = read_at(file, position, 1, size)[0]
        position += 1
        if kind == 0x3B:
            ended = True
            break
        if kind == 0x2C:
            frame = read_at(file, position, 9, size)
            position += 9
            local_bits = (frame[8] & 7) + 1 if frame[8] & 128 else 0
            bits = max(bits, local_bits or global_bits)
            if not (local_bits or global_bits):
                raise ValueError("GIF: отсутствует палитра")
            position += 3 * 2 ** local_bits if local_bits else 0
            code_size = read_at(file, position, 1, size)[0]
            if not 2 <= code_size <= 8:
                raise ValueError("GIF: неверный размер LZW-кода")
            position += 1
            frames += 1
        elif kind == 0x21:
            read_at(file, position, 1, size)
            position += 1
        else:
            raise ValueError("GIF: неизвестный блок")
        while True:
            length = read_at(file, position, 1, size)[0]
            position += 1
            if not length:
                break
            if position + length > size:
                raise ValueError("GIF: подблок обрезан")
            position += length
    if not ended or not frames:
        raise ValueError("GIF: нет завершающего блока или кадров")
    max_colors = 2 ** bits
    return dict(
        width=width,
        height=height,
        bits=bits,
        dpi="Не предусмотрено форматом",
        compression="LZW",
        note=f"Версия: {version}; кадров: {frames}; макс. палитра: {max_colors} цв.",
        extra={"Версия стандарта": version, "Количество кадров": frames, "Макс. цветов в палитре": max_colors},
    )


def pcx(file, size):
    data = read_at(file, 0, 128, size)
    if data[1] not in (0, 2, 3, 4, 5) or data[2] not in (0, 1) or data[3] not in (1, 2, 4, 8):
        raise ValueError("PCX: неверный заголовок")
    xmin, ymin, xmax, ymax = struct.unpack("<HHHH", data[4:12])
    width, height = xmax - xmin + 1, ymax - ymin + 1
    planes, line = data[65], number(data, 66, 2)
    if not 1 <= planes <= 4 or line < (width * data[3] + 7) // 8:
        raise ValueError("PCX: неверные плоскости или длина строки")
    end = size
    has_vga_palette = False
    if data[3] == 8 and planes == 1:
        end -= 769
        if read_at(file, end, 1, size) != b"\x0c":
            raise ValueError("PCX: нет 256-цветной палитры")
        has_vga_palette = True
    if end <= 128 or (data[2] == 0 and 128 + line * planes * height > end):
        raise ValueError("PCX: данные пикселей обрезаны")
    if data[2] == 1:
        def encoded_bytes():
            position = 128
            while position < end:
                block = read_at(file, position, min(32768, end - position), size)
                position += len(block)
                yield from block

        stream = encoded_bytes()
        expected, decoded = line * planes * height, 0
        while decoded < expected:
            value = next(stream, None)
            if value is None:
                raise ValueError("PCX: RLE-данные обрезаны")
            count = 1
            if value & 0xC0 == 0xC0:
                count = value & 0x3F
                if count == 0 or next(stream, None) is None:
                    raise ValueError("PCX: неверная или обрезанная RLE-серия")
            decoded += count
        if decoded != expected:
            raise ValueError("PCX: RLE-серия превышает размер изображения")
    return dict(
        width=width,
        height=height,
        bits=data[3] * planes,
        dpi=resolution(*struct.unpack("<HH", data[12:16])),
        compression="RLE" if data[2] else "Без сжатия",
        note=f"Плоскостей: {planes}; байт на строку: {line}",
        extra={
            "Версия PCX": data[1],
            "Цветовых плоскостей": planes,
            "Байт на строку (BytesPerLine)": line,
            "VGA-палитра (256 цветов)": "Да" if has_vga_palette else "Нет",
        },
    )


def tiff_tags(file, base=0, end=None):
    end = stream_size(file) if end is None else end

    def read(offset, length):
        if offset < 0 or base + offset + length > end:
            raise ValueError("TIFF: смещение за границами данных")
        return read_at(file, base + offset, length, end)

    header = read(0, 8)
    if header[:2] not in (b"II", b"MM"):
        raise ValueError("TIFF: неверный порядок байтов")
    endian = "little" if header[:2] == b"II" else "big"
    magic = number(header, 2, 2, endian)
    if magic == 43:
        raise NotImplementedError("BigTIFF не поддерживается")
    if magic != 42:
        raise ValueError("TIFF: неверная сигнатура")
    offset = number(header, 4, 4, endian)
    count = number(read(offset, 2), 0, 2, endian)
    if not offset or count > 4096:
        raise ValueError("TIFF: неверная таблица IFD")
    entries, tags = read(offset + 2, count * 12 + 4), {}
    wanted = (256, 257, 258, 259, 262, 273, 277, 279, 282, 283, 296, 324, 325)
    for i in range(count):
        entry = entries[i * 12:(i + 1) * 12]
        tag, kind, amount = (number(entry, p, n, endian) for p, n in ((0, 2), (2, 2), (4, 4)))
        if tag not in wanted:
            continue
        length = {1: 1, 3: 2, 4: 4, 5: 8}.get(kind)
        if not length:
            raise ValueError(f"TIFF: неподходящий тип нужного тега {tag}")
        total = length * amount
        if total > 16 * 1024 * 1024:
            raise ValueError("TIFF: слишком большой тег")
        data = entry[8:8 + total] if total <= 4 else read(number(entry, 8, 4, endian), total)
        values = []
        for p in range(0, total, length):
            value = number(data, p, 4 if kind == 5 else length, endian)
            if kind == 5:
                denominator = number(data, p + 4, 4, endian)
                if not denominator:
                    raise ValueError("TIFF: нулевой знаменатель")
                value /= denominator
            values.append(value)
        tags[tag] = values
    tags["_endian"] = endian
    return tags


def tiff(file, size):
    tags = tiff_tags(file, 0, size)
    width, height = tags.get(256, [0])[0], tags.get(257, [0])[0]
    samples, depths = tags.get(277, [1])[0], tags.get(258, [1])
    if not depths or not 1 <= samples <= 64 or len(depths) not in (1, samples):
        raise ValueError("TIFF: неверная глубина")
    bits = sum(depths) if len(depths) > 1 else depths[0] * samples
    offsets, lengths = tags.get(273, tags.get(324)), tags.get(279, tags.get(325))
    if not offsets or not lengths or len(offsets) != len(lengths):
        raise ValueError("TIFF: нет корректных полос/тайлов")
    if any(p < 0 or n <= 0 or p + n > size for p, n in zip(offsets, lengths)):
        raise ValueError("TIFF: полоса или тайл обрезаны")
    unit = tags.get(296, [2])[0]
    dpi = resolution(tags.get(282, [0])[0], tags.get(283, [0])[0], 2.54 if unit == 3 else 1) if unit in (2, 3) else "Не указано"
    names = {
        1: "Без сжатия",
        2: "CCITT RLE",
        3: "CCITT Group 3",
        4: "CCITT Group 4",
        5: "LZW",
        6: "JPEG (старый TIFF)",
        7: "JPEG",
        8: "Deflate",
        32773: "PackBits",
        32946: "Deflate",
    }
    photo = {0: "WhiteIsZero", 1: "BlackIsZero", 2: "RGB", 3: "Palette", 4: "Transparency Mask", 5: "CMYK", 6: "YCbCr"}
    code = tags.get(259, [1])[0]
    p_code = tags.get(262, [-1])[0]
    order_str = "Little-Endian (II)" if tags["_endian"] == "little" else "Big-Endian (MM)"
    return dict(
        width=width,
        height=height,
        bits=bits,
        dpi=dpi,
        compression=names.get(code, f"Код {code}"),
        note=f"{order_str}; полос/тайлов: {len(offsets)}",
        extra={
            "Порядок байтов": order_str,
            "Цветовая модель (Tag 262)": photo.get(p_code, f"Код {p_code}"),
            "Каналов (SamplesPerPixel)": samples,
            "Количество полос/тайлов": len(offsets),
        },
    )


ZIGZAG_ORDER = [
    0, 1, 8, 16, 9, 2, 3, 10,
    17, 24, 32, 25, 18, 11, 4, 5,
    12, 19, 26, 33, 40, 48, 41, 34,
    27, 20, 13, 6, 7, 14, 21, 28,
    35, 42, 49, 56, 57, 50, 43, 36,
    29, 22, 15, 23, 30, 37, 44, 51,
    58, 59, 52, 45, 38, 31, 39, 46,
    53, 60, 61, 54, 47, 55, 62, 63,
]


def unzigzag(values):
    matrix = [[0] * 8 for _ in range(8)]
    for idx, val in enumerate(values):
        pos = ZIGZAG_ORDER[idx]
        matrix[pos // 8][pos % 8] = val
    return matrix


def jpeg(file, size):
    tail_len = min(65536, size)
    tail = read_at(file, size - tail_len, tail_len, size)
    if b"\xff\xd9" not in tail:
        raise ValueError("JPEG: отсутствует завершающий маркер EOI (FF D9)")
    position, result, exif_dpi, jfif_dpi = 2, {}, "Не указано", "Не указано"
    components = set()
    quant_tables = {}
    sof = (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF)
    sof_names = {
        0xC0: "Baseline DCT (SOF0)",
        0xC1: "Extended Sequential DCT (SOF1)",
        0xC2: "Progressive DCT (SOF2)",
        0xC3: "Lossless (SOF3)",
    }
    while position < size:
        if read_at(file, position, 1, size) != b"\xff":
            raise ValueError("JPEG: ожидается маркер")
        position += 1
        code = read_at(file, position, 1, size)[0]
        while code == 255:
            position += 1
            code = read_at(file, position, 1, size)[0]
        position += 1
        if code in (0, 0xD9):
            raise ValueError("JPEG: нет SOS")
        if code == 1 or 0xD0 <= code <= 0xD8:
            continue
        length = number(read_at(file, position, 2, size), 0, 2, "big")
        if length < 2 or position + length > size:
            raise ValueError("JPEG: сегмент обрезан")
        if code == 0xDB:
            dqt_data = read_at(file, position + 2, length - 2, size)
            ptr = 0
            while ptr < len(dqt_data):
                pq_tq = dqt_data[ptr]
                precision = pq_tq >> 4
                table_id = pq_tq & 0x0F
                ptr += 1
                elem_size = 2 if precision == 1 else 1
                if ptr + 64 * elem_size > len(dqt_data):
                    raise ValueError("JPEG: обрезан сегмент DQT")
                raw_vals = [
                    number(dqt_data, ptr + i * elem_size, elem_size, "big")
                    for i in range(64)
                ]
                ptr += 64 * elem_size
                quant_tables[table_id] = unzigzag(raw_vals)
        elif code in sof:
            data = read_at(file, position + 2, length - 2, size)
            if len(data) < 6 or not data[5] or length != 8 + 3 * data[5]:
                raise ValueError("JPEG: неверный SOF")
            components = {data[6 + 3 * i] for i in range(data[5])}
            if len(components) != data[5]:
                raise ValueError("JPEG: повторные компоненты SOF")
            profile = sof_names.get(code, f"SOF (0x{code:02X})")
            result = dict(
                width=number(data, 3, 2, "big"),
                height=number(data, 1, 2, "big"),
                bits=data[0] * data[5],
                note=f"{profile}; компонентов: {data[5]}",
                compression="JPEG без потерь" if code in (0xC3, 0xC7, 0xCB, 0xCF) else "JPEG с потерями",
                extra={"Профиль кодирования": profile, "Цветовых компонентов": data[5], "Точность на канал": f"{data[0]} бит"},
            )
        elif code == 0xE0 and length >= 16:
            data = read_at(file, position + 2, 14, size)
            if data[:5] == b"JFIF\x00" and data[7] in (1, 2):
                jfif_dpi = resolution(number(data, 8, 2, "big"), number(data, 10, 2, "big"), 2.54 if data[7] == 2 else 1)
        elif code == 0xE1 and length >= 16:
            if read_at(file, position + 2, 6, size) == b"Exif\x00\x00":
                tags = tiff_tags(file, position + 8, position + length)
                unit = tags.get(296, [2])[0]
                if unit in (2, 3):
                    exif_dpi = resolution(tags.get(282, [0])[0], tags.get(283, [0])[0], 2.54 if unit == 3 else 1)
        elif code == 0xDA:
            if not result:
                raise ValueError("JPEG: отсутствует SOF")
            data = read_at(file, position + 2, length - 2, size)
            if not data or not 1 <= data[0] <= 4 or length != 6 + 2 * data[0]:
                raise ValueError("JPEG: неверная длина заголовка SOS")
            selected = {data[1 + 2 * i] for i in range(data[0])}
            if len(selected) != data[0] or not selected.issubset(components):
                raise ValueError("JPEG: неверные компоненты SOS")
            if position + length >= size - 2:
                raise ValueError("JPEG: отсутствуют данные после SOS")
            result["dpi"] = exif_dpi if exif_dpi != "Не указано" else jfif_dpi
            result["extra"]["Источник DPI"] = "EXIF (APP1)" if exif_dpi != "Не указано" else ("JFIF (APP0)" if jfif_dpi != "Не указано" else "По умолчанию")
            if quant_tables:
                result["quant_tables"] = quant_tables
                result["note"] += f"; таблиц DQT: {len(quant_tables)}"
            return result
        position += length
    raise ValueError("JPEG: отсутствует SOS")


def parse_stream(file, display_name, suffix, size):
    row = {
        "Файл": display_name,
        "Формат": "—",
        "Размер, px": "—",
        "DPI, X × Y": "—",
        "Глубина, бит/пиксель": "—",
        "Сжатие": "—",
        "Статус": "OK",
        "Примечание": "",
        "_extra": {},
        "_quant": {},
    }
    try:
        header = read_at(file, 0, min(8, size), size)
        if header == b"\x89PNG\r\n\x1a\n":
            name, parser = "PNG", png
        elif header[:2] == b"\xff\xd8":
            name, parser = "JPEG", jpeg
        elif header[:6] in (b"GIF87a", b"GIF89a"):
            name, parser = "GIF", gif
        elif header[:2] == b"BM":
            name, parser = "BMP", bmp
        elif header[:2] in (b"II", b"MM"):
            name, parser = "TIFF", tiff
        elif header[:1] == b"\x0a":
            name, parser = "PCX", pcx
        else:
            row.update({"Статус": "Не изображение / неизвестный формат", "Примечание": "Сигнатура не распознана"})
            return row
        row["Формат"] = name
        info = parser(file, size)
        if info["dpi"] == "Не указано":
            info["dpi"] = "96.00 × 96.00 (по умолчанию)"
        if info["width"] <= 0 or info["height"] <= 0 or info["bits"] <= 0:
            raise ValueError("Недопустимые размеры или глубина")
        row.update({
            "Размер, px": f'{info["width"]} × {info["height"]}',
            "DPI, X × Y": info["dpi"],
            "Глубина, бит/пиксель": str(info["bits"]),
            "Сжатие": info["compression"],
            "Примечание": info["note"],
            "_extra": info.get("extra", {}),
            "_quant": info.get("quant_tables", {}),
        })
        extensions = {"JPEG": (".jpg", ".jpeg"), "TIFF": (".tif", ".tiff")}
        if suffix.lower() not in extensions.get(name, ("." + name.lower(),)):
            row["Статус"] = "Расширение не совпадает с форматом"
    except NotImplementedError as error:
        row.update({"Статус": "Вариант не поддерживается", "Примечание": str(error)})
    except (OSError, ValueError, IndexError, struct.error, UnicodeDecodeError) as error:
        row.update({"Статус": "Файл поврежден / недоступен", "Примечание": str(error)})
    return row


def read_image(path):
    p = Path(path)
    try:
        with open(p, "rb") as file:
            size = stream_size(file)
            return parse_stream(file, str(p), p.suffix, size)
    except OSError as error:
        return {
            "Файл": str(p),
            "Формат": "—",
            "Размер, px": "—",
            "DPI, X × Y": "—",
            "Глубина, бит/пиксель": "—",
            "Сжатие": "—",
            "Статус": "Файл поврежден / недоступен",
            "Примечание": str(error),
            "_extra": {},
            "_quant": {},
        }


def read_uploaded_batch(uploaded_files):
    results = []
    for uf in uploaded_files:
        raw = uf.getvalue()
        if uf.name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as zf:
                    for info in zf.infolist():
                        if info.is_dir():
                            continue
                        member_bytes = zf.read(info.filename)
                        bio = io.BytesIO(member_bytes)
                        res = parse_stream(bio, f"{uf.name}/{info.filename}", Path(info.filename).suffix, len(member_bytes))
                        res["_preview_bytes"] = member_bytes
                        results.append(res)
            except zipfile.BadZipFile as error:
                results.append({
                    "Файл": uf.name,
                    "Формат": "ZIP",
                    "Размер, px": "—",
                    "DPI, X × Y": "—",
                    "Глубина, бит/пиксель": "—",
                    "Сжатие": "—",
                    "Статус": "Файл поврежден / недоступен",
                    "Примечание": f"Поврежденный ZIP-архив: {error}",
                    "_extra": {},
                    "_quant": {},
                })
        else:
            bio = io.BytesIO(raw)
            res = parse_stream(bio, uf.name, Path(uf.name).suffix, len(raw))
            res["_preview_bytes"] = raw
            results.append(res)
    return results