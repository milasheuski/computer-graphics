"""View: пользовательский интерфейс цветового конвертера."""

import streamlit as st

from controller import ColorController, ColorState


controller = ColorController()


def sync_widgets(state: ColorState) -> None:
    r, g, b = state.rgb
    c, m, y, k = state.cmyk
    h, l, s = state.hls

    st.session_state.color_state = state
    st.session_state.update({
        "hex_in": state.hex_value,
        "r_slider": r, "g_slider": g, "b_slider": b,
        "r_number": r, "g_number": g, "b_number": b,
        "c_slider": c, "m_slider": m, "y_slider": y, "k_slider": k,
        "c_number": c, "m_number": m, "y_number": y, "k_number": k,
        "h_slider": h, "l_slider": l, "s_slider": s,
        "h_number": h, "l_number": l, "s_number": s,
    })


def apply_result(state: ColorState, warnings: list[str]) -> None:
    sync_widgets(state)
    for message in warnings:
        st.toast(message, icon="⚠️")


def on_rgb_change(source: str) -> None:
    values = [st.session_state[f"{name}_{source}"] for name in ("r", "g", "b")]
    apply_result(*controller.from_rgb(*values))


def on_cmyk_change(source: str) -> None:
    values = [st.session_state[f"{name}_{source}"] for name in ("c", "m", "y", "k")]
    apply_result(*controller.from_cmyk(*values))


def on_hls_change(source: str) -> None:
    values = [st.session_state[f"{name}_{source}"] for name in ("h", "l", "s")]
    apply_result(*controller.from_hls(*values))


def on_hex_change() -> None:
    apply_result(*controller.from_hex(st.session_state.hex_in))


def component_input(label, key_name, minimum, maximum, model, integer=False) -> None:
    callback = {
        "rgb": on_rgb_change,
        "cmyk": on_cmyk_change,
        "hls": on_hls_change,
    }[model]

    st.number_input(
        f"{label}",
        step=1 if integer else 1.0,
        key=f"{key_name}_number",
        on_change=callback,
        args=("number",),
    )
    st.slider(
        f"{label} — ползунок",
        int(minimum) if integer else float(minimum),
        int(maximum) if integer else float(maximum),
        step=1 if integer else 0.1,
        key=f"{key_name}_slider",
        on_change=callback,
        args=("slider",),
    )


st.set_page_config(page_title="Цветовой конвертер", page_icon="🎨", layout="wide")

if "color_state" not in st.session_state:
    initial_state, _ = controller.from_rgb(255, 0, 0)
    sync_widgets(initial_state)

st.title("Цветовой конвертер")

picker_col, preview_col = st.columns([1, 2])
with picker_col:
    st.color_picker("Выберите цвет из палитры", key="hex_in", on_change=on_hex_change)
with preview_col:
    current_hex = st.session_state.color_state.hex_value
    st.markdown(
        f'<div style="height:90px;border-radius:12px;background:{current_hex};'
        f'border:1px solid #888;display:flex;align-items:center;justify-content:center;'
        f'font:600 20px sans-serif;color:{controller.contrast_text(current_hex)}">'
        f'{current_hex.upper()}</div>',
        unsafe_allow_html=True,
    )

st.divider()
rgb_col, cmyk_col, hls_col = st.columns(3)

with rgb_col:
    st.subheader("RGB")
    component_input("R (красный)", "r", 0, 255, "rgb", integer=True)
    component_input("G (зелёный)", "g", 0, 255, "rgb", integer=True)
    component_input("B (синий)", "b", 0, 255, "rgb", integer=True)

with cmyk_col:
    st.subheader("CMYK")
    component_input("C (голубой), %", "c", 0, 100, "cmyk")
    component_input("M (пурпурный), %", "m", 0, 100, "cmyk")
    component_input("Y (жёлтый), %", "y", 0, 100, "cmyk")
    component_input("K (чёрный), %", "k", 0, 100, "cmyk")

with hls_col:
    st.subheader("HLS")
    component_input("H (тон), °", "h", 0, 360, "hls")
    component_input("L (светлота), %", "l", 0, 100, "hls")
    component_input("S (насыщенность), %", "s", 0, 100, "hls")


