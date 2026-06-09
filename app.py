"""
app.py — Darwin AI Content Studio
Requiere .streamlit/config.toml con base="light" para estilos correctos.
"""
from __future__ import annotations

import streamlit as st
from content_generator import GenerationRequest, generate_post
from memory_store import (
    append_approved, append_feedback, append_tone_example,
    read_recent_feedback, get_memory_stats,
)
from tone_learner import update_profile_from_feedback

st.set_page_config(
    page_title="Darwin AI · Content Studio",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], * {
    font-family: 'Plus Jakarta Sans', -apple-system, sans-serif !important;
}

/* Forzar tema claro — sin config.toml */
:root {
    --background-color: #F4F6F9 !important;
    --secondary-background-color: #FFFFFF !important;
    --text-color: #101828 !important;
    --primary-color: #0066FF !important;
}
html[data-theme="dark"], [data-theme="dark"] * {
    color-scheme: light !important;
}
.stApp, .stApp > * {
    background-color: #F4F6F9 !important;
    color: #101828 !important;
}
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="column"] {
    background-color: transparent !important;
    color: #101828 !important;
}

/* Sidebar */
[data-testid="stSidebar"] { background: #FFFFFF !important; border-right: 1px solid #E4E7EC !important; }
[data-testid="stSidebar"] * { color: #101828 !important; }

/* Ocultar botón colapsar sidebar */
[data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"],
button[aria-label="Close sidebar"],
button[aria-label="Collapse sidebar"] { display: none !important; visibility: hidden !important; }

/* Inputs — especificidad máxima con :is() */
.stApp :is(div[data-testid="stTextInput"]) input,
.stApp :is(div[data-testid="stTextArea"]) textarea {
    background: #FFFFFF !important;
    border: 1.5px solid #D0D5DD !important;
    border-radius: 10px !important;
    color: #101828 !important;
    box-shadow: none !important;
    outline: none !important;
    -webkit-text-fill-color: #101828 !important;
}
.stApp :is(div[data-testid="stTextInput"]) input:focus,
.stApp :is(div[data-testid="stTextArea"]) textarea:focus {
    border-color: #0066FF !important;
    box-shadow: 0 0 0 3px rgba(0,102,255,0.1) !important;
}
div[data-testid="stTextArea"] textarea {
    line-height: 1.7 !important;
}

/* Selectbox — fondo blanco */
[data-testid="stSelectbox"] button,
[data-testid="stSelectbox"] [data-testid="stBaseButton-minimal"] { display: none !important; }
[data-testid="stSelectbox"] > div > div {
    background: #FFFFFF !important;
    border: 1.5px solid #D0D5DD !important;
    border-radius: 10px !important;
    color: #101828 !important;
}
[data-testid="stSelectbox"] svg { color: #667085 !important; }

/* Radio */
div[data-testid="stRadio"] label p { color: #101828 !important; font-weight: 500 !important; }

/* Botones */
button[kind="primary"] {
    background: #0066FF !important; color: #fff !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 700 !important; box-shadow: none !important;
}
button[kind="primary"]:hover { background: #0052CC !important; }
button[kind="secondary"] {
    background: #fff !important; color: #344054 !important;
    border: 1.5px solid #D0D5DD !important; border-radius: 10px !important;
    font-weight: 600 !important; box-shadow: none !important;
    color: #101828 !important;
}
[data-testid="stFormSubmitButton"] button {
    background: #0066FF !important; color: #fff !important;
    border-radius: 10px !important; font-weight: 700 !important;
}

/* Ocultar chrome */
#MainMenu, footer { visibility: hidden; }
[data-testid="InputInstructions"] { display: none !important; }
/* Ocultar anchor links en headers */
h1 a, h2 a, h3 a, [data-testid="stHeadingWithActionElements"] a { display: none !important; }

.block-container { padding-top: 24px; max-width: 760px; margin: 0 auto; padding-left: 2rem; padding-right: 2rem; }

/* Componentes custom */
.dw-logo { display:flex; align-items:center; gap:10px; padding:4px 0 20px 0; }
.dw-icon { width:34px; height:34px; background:#0066FF; border-radius:9px; display:flex;
    align-items:center; justify-content:center; color:#fff; font-size:16px; font-weight:800; flex-shrink:0; }
.dw-name { font-size:15px; font-weight:700; color:#101828; }
.dw-sub  { font-size:11px; color:#98A2B3; }

.sb-lbl { font-size:10px; font-weight:700; letter-spacing:1px; text-transform:uppercase; color:#98A2B3; margin:18px 0 8px 0; }

.stat-grid { display:grid; grid-template-columns:1fr 1fr; gap:7px; }
.stat-t { background:#F9FAFB; border:1px solid #E4E7EC; border-radius:10px; padding:10px 12px; }
.stat-t .n { font-size:22px; font-weight:800; color:#0066FF; line-height:1; }
.stat-t .l { font-size:11px; color:#667085; margin-top:2px; }

.fb-pill { background:#EEF4FF; border:1px solid #C7D7FF; border-radius:9px;
    padding:9px 11px; margin-bottom:7px; font-size:12px; color:#101828; line-height:1.5; }
.fb-pill .fm { font-size:10px; color:#0066FF; font-weight:700; margin-bottom:2px;
    text-transform:uppercase; letter-spacing:0.4px; }

.inspo-step { display:inline-block; background:#EEF4FF; color:#0066FF; font-size:10px;
    font-weight:700; padding:3px 8px; border-radius:5px; margin-bottom:6px; }
.inspo-hint { font-size:11px; color:#667085; line-height:1.5; margin-bottom:10px; }

.main-card { background:#FFFFFF; border:1px solid #E4E7EC; border-radius:18px;
    padding:24px; margin-bottom:14px; box-shadow:0 1px 3px rgba(0,0,0,0.04); }
.card-ey { font-size:10px; font-weight:700; letter-spacing:1px; text-transform:uppercase;
    color:#98A2B3; margin-bottom:14px; text-align:center; width:100%; display:block; }

/* Input font size más chico */
input { font-size: 13px !important; }
[data-testid="stSelectbox"] > div > div { font-size: 13px !important; }

.chip-row { display:flex; flex-wrap:wrap; gap:7px; margin:12px 0 18px 0; }
.chip { background:#F9FAFB; border:1px solid #E4E7EC; border-radius:8px;
    padding:5px 11px; font-size:12px; color:#344054; font-weight:500; }
.chip b { color:#101828; font-weight:700; }
.chip.ok  { background:#ECFDF3; border-color:#ABEFC6; color:#027A48; }
.chip.ok b { color:#027A48; }
.chip.err { background:#FEF3F2; border-color:#FCA5A5; color:#B42318; }
.chip.err b { color:#B42318; }

.divider { height:1px; background:#F2F4F7; margin:18px 0; }

.gen-hdr { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
.gen-title { font-size:14px; font-weight:700; color:#101828; }
.badges { display:flex; gap:5px; flex-wrap:wrap; }
.badge { font-size:11px; font-weight:600; padding:3px 9px; border-radius:20px;
    background:#EEF4FF; color:#3538CD; }
.badge-g { background:#ECFDF3; color:#027A48; }

.reject-wrap { background:#FFFBF5; border:1.5px solid #FBBF24; border-radius:14px;
    padding:18px; margin-top:14px; }
.reject-ttl { font-size:13px; font-weight:700; color:#92400E; margin-bottom:12px; }

.notice-ok   { background:#ECFDF3; border:1px solid #ABEFC6; border-radius:10px;
    padding:11px 15px; font-size:13px; color:#027A48; font-weight:600; margin-bottom:18px; }
.notice-info { background:#EEF4FF; border:1px solid #C7D7FF; border-radius:10px;
    padding:11px 15px; font-size:13px; color:#3538CD; font-weight:600; margin-bottom:18px; }

.page-hdr { border-bottom:1px solid #E4E7EC; padding-bottom:20px; margin-bottom:22px; }
.page-hdr h1 { font-size:24px; font-weight:800; color:#101828; letter-spacing:-0.5px; margin:0 0 5px 0; }
.page-hdr p  { font-size:13px; color:#667085; margin:0; }
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────

for k, v in [("current_post",None),("current_req",None),("generation_count",0),
              ("last_action",None),("show_reject",False),("last_language","español")]:
    if k not in st.session_state:
        st.session_state[k] = v

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div class="dw-logo">
        <div class="dw-icon">D</div>
        <div><div class="dw-name">Darwin AI</div><div class="dw-sub">Content Studio</div></div>
    </div>""", unsafe_allow_html=True)

    stats = get_memory_stats()
    st.markdown('<div class="sb-lbl">Memoria</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="stat-grid">
        <div class="stat-t"><div class="n">{stats["tone_examples"]}</div><div class="l">Ejemplos tono</div></div>
        <div class="stat-t"><div class="n">{stats["approved_posts"]}</div><div class="l">Aprobados</div></div>
        <div class="stat-t"><div class="n">{stats["rejected_posts"]}</div><div class="l">Rechazos</div></div>
        <div class="stat-t"><div class="n">{"✓" if stats["has_tone_profile"] else "✗"}</div><div class="l">Perfil activo</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<div class="sb-lbl">Último feedback</div>', unsafe_allow_html=True)
    recent_fb = read_recent_feedback(n=3)
    if recent_fb:
        for fb in reversed(recent_fb):
            st.markdown(f"""
            <div class="fb-pill">
                <div class="fm">{fb.get("platform","").upper()} · {fb.get("topic","")[:30]}</div>
                {fb.get("reason","")}
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("<p style='font-size:12px;color:#98A2B3;'>Sin feedback todavía.</p>", unsafe_allow_html=True)

    st.markdown('<div class="sb-lbl">Inspiración externa</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="inspo-step">① Opcional · antes de generar</div>
    <div class="inspo-hint">Pegá un post de otra cuenta como referencia. El sistema toma el ángulo pero adapta todo al tono de Darwin.</div>
    """, unsafe_allow_html=True)
    inspiration_post = st.text_area(
        "inspiración", height=110,
        placeholder="Pegá el post de referencia acá…",
        label_visibility="collapsed",
        key="inspo_val",
    )
    st.markdown("<p style='font-size:11px;color:#D0D5DD;margin-top:28px;'>Darwin AI · Content Studio v0.1</p>", unsafe_allow_html=True)

# ── Main ───────────────────────────────────────────────────────────────────────

st.markdown("""
<div class="page-hdr">
    <h1>Generador de posts</h1>
    <p>Completá el briefing · generá · aprobá o rechazá con feedback · el sistema aprende</p>
</div>""", unsafe_allow_html=True)

if st.session_state.last_action == "approved":
    st.markdown('<div class="notice-ok">✓ Post aprobado. Se usará como ejemplo de tono en la próxima generación.</div>', unsafe_allow_html=True)
    st.session_state.last_action = None
elif st.session_state.last_action == "rejected":
    st.markdown('<div class="notice-info">↻ Feedback guardado. El post fue regenerado con la corrección.</div>', unsafe_allow_html=True)
    st.session_state.last_action = None

# ── Briefing ───────────────────────────────────────────────────────────────────

st.markdown('<div class="main-card"><div class="gen-title">① Briefing</div>', unsafe_allow_html=True)

with st.form("briefing_form"):
    topic = st.text_input(
        "Tema o noticia",
        placeholder="Ej: OpenAI lanza o3 y las PYMES de LATAM aceleran la adopción de agentes IA",
    )

    col_obj, col_lang, col_plat = st.columns(3)
    with col_obj:
        objective = st.selectbox("Objetivo", ["awareness","lead_gen","engagement","educación"],
            format_func=lambda x: {"awareness":"Awareness","lead_gen":"Leads",
                                    "engagement":"Engagement","educación":"Educación"}[x])
    with col_lang:
        language = st.selectbox("Idioma", ["español","inglés","portugués"],
            format_func=lambda x: x.capitalize())
    with col_plat:
        platform = st.selectbox("Red social", ["linkedin","instagram"],
            format_func=lambda x: "LinkedIn" if x=="linkedin" else "Instagram")

    submitted = st.form_submit_button("Generar post →", type="primary", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── Generación ─────────────────────────────────────────────────────────────────

if submitted:
    if not topic.strip():
        st.warning("Completá el tema antes de generar.")
    else:
        st.session_state.last_language = language
        req = GenerationRequest(
            platform=platform, topic=topic, objective=objective, language=language,
            inspiration_post=st.session_state.get("inspo_val") or None,
        )
        with st.spinner("Generando post..."):
            try:
                post = generate_post(req)
                st.session_state.current_post = post
                st.session_state.current_req  = req
                st.session_state.generation_count += 1
                st.session_state.last_action  = None
                st.session_state.show_reject  = False
            except Exception as e:
                st.error(f"Error al generar: {e}")
                st.stop()

# ── Panel aprobación ───────────────────────────────────────────────────────────

post = st.session_state.current_post
req  = st.session_state.current_req

if post is not None:
    fb_count = get_memory_stats()["rejected_posts"]
    gen_num  = st.session_state.generation_count
    lang_cap = st.session_state.last_language.capitalize()
    badge_l  = f'<span class="badge badge-g">↑ {fb_count} rechazo(s) aprendidos</span>' if fb_count > 0 else ""

    st.markdown(f"""
    <div class="main-card">
        <div class="gen-hdr">
            <span class="gen-title">② Revisión · Generación #{gen_num}</span>
            <div class="badges">
                {badge_l}
                <span class="badge">{post.platform.capitalize()}</span>
                <span class="badge">{lang_cap}</span>
            </div>
        </div>""", unsafe_allow_html=True)

    edited_text = st.text_area("Post", value=post.text, height=300, label_visibility="collapsed")

    wc = len(edited_text.split())
    cc = len(edited_text)
    lo, hi = {"linkedin":(150,300),"instagram":(80,150)}.get(post.platform,(100,300))
    ok = lo <= wc <= hi
    cls = "ok" if ok else "err"
    lbl = "✓" if ok else ("↑ largo" if wc > hi else "↓ corto")

    st.markdown(f"""
    <div class="chip-row">
        <div class="chip {cls}"><b>{wc}</b> palabras {lbl}</div>
        <div class="chip"><b>{cc}</b> caracteres</div>
        <div class="chip">Rango: <b>{lo}–{hi}</b></div>
        <div class="chip"><b>{post.prompt_tokens + post.completion_tokens}</b> tokens</div>
    </div>
    <div class="divider"></div>""", unsafe_allow_html=True)

    col_ok, col_no = st.columns(2)
    with col_ok:
        if st.button("Aprobar post", type="primary", use_container_width=True):
            post.text = edited_text
            append_approved({"text":post.text,"platform":post.platform,"topic":post.topic,"model":post.model})
            append_tone_example({"text":post.text,"platform":post.platform,
                                  "performance":"high","notes":"Aprobado en app","word_count":len(post.text.split())})
            st.session_state.last_action  = "approved"
            st.session_state.current_post = None
            st.rerun()
    with col_no:
        if st.button("Rechazar y dar feedback", use_container_width=True):
            st.session_state.show_reject = not st.session_state.show_reject

    st.markdown('</div>', unsafe_allow_html=True)  # cierra main-card

    if st.session_state.show_reject:
        st.markdown('<div class="reject-wrap"><div class="reject-ttl">⚠ ¿Por qué no sirve este post?</div>', unsafe_allow_html=True)
        reason = st.text_input("Motivo", placeholder="Ej: Muy genérico, sin datos concretos ni mención a LATAM")
        tags = st.multiselect("Tags", ["falta_latam","muy_formal","falta_cta",
                                        "muy_largo","muy_corto","muy_generico","tono_incorrecto"])
        st.markdown('</div>', unsafe_allow_html=True)

        if st.button("↻  Confirmar rechazo y regenerar", type="primary", use_container_width=True):
            if not reason.strip():
                st.warning("Agregá un motivo para que el sistema pueda aprender.")
            else:
                append_feedback({"text":post.text,"platform":post.platform,
                                  "topic":post.topic,"reason":reason,"tags":tags})
                if tags:
                    update_profile_from_feedback(tags)
                with st.spinner("Regenerando con feedback incorporado..."):
                    try:
                        new_post = generate_post(req)
                        st.session_state.current_post = new_post
                        st.session_state.generation_count += 1
                        st.session_state.last_action  = "rejected"
                        st.session_state.show_reject  = False
                    except Exception as e:
                        st.error(f"Error al regenerar: {e}")
                st.rerun()
