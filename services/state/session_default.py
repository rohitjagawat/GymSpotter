import streamlit as st

def initial_session_defaults():
    for key,value in dict(active=False,exercise='Squats',paused=False,page='Overview',
                           last_save=0.,last_snapshot={},workout_id=None,voice_enabled=False).items():
        st.session_state.setdefault(key,value)


