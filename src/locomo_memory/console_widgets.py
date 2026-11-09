"""Compact controls for small choices; searchable menus for larger collections."""
import streamlit as st


def compact_choice(label, options, *, key, format_func=str):
    values = list(options)
    if not values:
        raise ValueError('choice_requires_options')
    if key in st.session_state and st.session_state[key] not in values:
        del st.session_state[key]
    with st.container(key='choice_' + key):
        if len(values) == 1:
            st.caption(label)
            st.text(format_func(values[0]))
            st.session_state[key] = values[0]
            return values[0]
        if len(values) <= 6:
            return st.radio(label, values, format_func=format_func, key=key, horizontal=True)
        return st.selectbox(label, values, format_func=format_func, key=key)
