from html import escape
import streamlit as st
from services.config.workout_config import ROOT

MARK = '<svg class="brand-mark" viewBox="0 0 40 40" fill="none" aria-hidden="true"><path d="M5 14v12m6-17v22m18-22v22m6-17v12M11 20h18" stroke="currentColor" stroke-width="5"/></svg>'
BARBELL = '''<svg viewBox="0 0 440 330" fill="none" aria-hidden="true">
<defs><linearGradient id="steel" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#d9d5cc"/><stop offset=".45" stop-color="#737780"/><stop offset=".6" stop-color="#b9bcc2"/><stop offset="1" stop-color="#40444b"/></linearGradient>
<linearGradient id="plate" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#575a60"/><stop offset=".5" stop-color="#24272c"/><stop offset="1" stop-color="#111216"/></linearGradient></defs>
<path d="M20 165H420" stroke="#131416" stroke-width="23"/><rect x="20" y="156" width="400" height="17" rx="5" fill="url(#steel)"/>
<path d="M145 157v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15m8-15v15" stroke="#26292d" stroke-width="2"/>
<rect x="55" y="113" width="23" height="104" rx="9" fill="url(#plate)" stroke="#6b6c72"/>
<rect x="77" y="79" width="31" height="171" rx="12" fill="url(#plate)" stroke="#74767c"/>
<rect x="107" y="67" width="31" height="195" rx="12" fill="url(#plate)" stroke="#9a9a9d"/>
<rect x="113" y="80" width="5" height="169" rx="2" fill="#f07a45"/>
<rect x="302" y="67" width="31" height="195" rx="12" fill="url(#plate)" stroke="#9a9a9d"/>
<rect x="308" y="80" width="5" height="169" rx="2" fill="#f07a45"/>
<rect x="333" y="79" width="31" height="171" rx="12" fill="url(#plate)" stroke="#74767c"/>
<rect x="364" y="113" width="23" height="104" rx="9" fill="url(#plate)" stroke="#6b6c72"/>
<path d="M44 151v27m353-27v27" stroke="#b8b8bb" stroke-width="9"/>
</svg>'''


def theme():
    st.markdown('<style>'+(ROOT/'static/style.css').read_text(encoding='utf-8')+'</style>', unsafe_allow_html=True)


def brand():
    st.markdown('<div class="brand">'+MARK+'<span>GYM<em>SPOTTER</em></span></div>', unsafe_allow_html=True)


def hero(eyebrow,title,accent,description):
    st.markdown(f'<div class="hero"><div class="hero-copy"><div class="eyebrow">{escape(eyebrow)}</div>'
        f'<div class="display">{escape(title)}<br><span>{escape(accent)}</span></div>'
        f'<p>{escape(description)}</p><span class="tag">STRENGTH &amp; CONDITIONING</span>'
        '<span class="tag">12 MOVEMENTS</span><span class="tag">LIVE COACHING</span></div>'
        f'<div class="hero-art">{BARBELL}<span class="art-label">BUILT ONE REP AT A TIME.</span></div></div>', unsafe_allow_html=True)


def coach(cue):
    st.markdown(f'<div class="coach-card"><div class="eyebrow">YOUR CORNER / COACHING</div><p>{escape(cue)}</p></div>', unsafe_allow_html=True)


def exercise_card(index,name,cfg):
    st.markdown(f'<div class="exercise-card"><span class="number">{index:02}</span>'
        f'<div class="eyebrow">{escape(cfg["group"])}</div><h3>{escape(name)}</h3>'
        f'<p>{escape(cfg["checks"])}</p><span class="tag">{cfg["view"].upper()} VIEW</span>'
        f'<span class="tag">{"TIMED HOLD" if cfg["kind"]=="hold" else "REP TRACKING"}</span>'
        f'<div class="exercise-glyph">{MARK}</div></div>', unsafe_allow_html=True)


def camera_empty():
    camera = '<svg viewBox="0 0 64 64" fill="none" aria-hidden="true"><rect x="7" y="17" width="36" height="31" rx="4" stroke="currentColor" stroke-width="2"/><path d="M43 27l13-7v25l-13-7" stroke="currentColor" stroke-width="2"/><circle cx="25" cy="32" r="8" stroke="#f07a45" stroke-width="2"/></svg>'
    st.markdown('<div class="camera-empty"><div><div class="target">'+camera+'</div><h2>STEP INTO YOUR SESSION.</h2>'
        '<p>Set your movement. Frame your body.<br>Your next set starts here.</p>'
        '<span class="tag">CAMERA OFF</span></div></div>', unsafe_allow_html=True)
