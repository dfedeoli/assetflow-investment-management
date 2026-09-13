"""
Shared UI helper widgets for AssetFlow.
"""

import streamlit as st


def currency_input(label: str, key: str, initial_value: float = 0.0) -> float:
    """
    Calculator-style currency input (Brazilian format).

    Digits fill from the right: typing 1-2-3-4-5 produces 123,45.
    No thousand separators — just digits and a comma: 12345,67.
    After each interaction (Enter / click elsewhere) the field is replaced
    with a fresh widget showing the correctly formatted value.
    Returns the current value as a float.
    """
    cents_key = f"{key}_cents"
    gen_key = f"{key}_gen"  # generation counter — changing it forces a new widget

    if cents_key not in st.session_state:
        st.session_state[cents_key] = int(round(initial_value * 100))
    if gen_key not in st.session_state:
        st.session_state[gen_key] = 0

    gen = st.session_state[gen_key]
    widget_key = f"{key}_{gen}"
    formatted = _cents_to_display(st.session_state[cents_key])

    raw = st.text_input(label, value=formatted, key=widget_key)

    digits = "".join(c for c in (raw or "") if c.isdigit())
    new_cents = int(digits.lstrip("0") or "0") if digits else 0

    if new_cents != st.session_state[cents_key]:
        st.session_state[cents_key] = new_cents
        st.session_state[gen_key] = gen + 1
        st.rerun()

    return st.session_state[cents_key] / 100.0


def _cents_to_display(cents: int) -> str:
    """Format integer centavos without thousand separators: 1234567 -> '12345,67'"""
    reais = cents // 100
    centavos = cents % 100
    return f"{reais},{centavos:02d}"
