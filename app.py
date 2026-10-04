# app.py — Entry point Streamlit
import streamlit as st

from icons import icon
from page_tokai import render as render_tokai
from page_mitsuba import render as render_mitsuba

st.set_page_config(
    page_title="Master Data Transformer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ═══════════════════════════════════════════════════════════════════
#  CUSTOM CSS
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    .stApp { background: #fafbfc; }
    .main-header {
        display: flex; align-items: center; gap: 16px;
        padding: 8px 0 20px 0;
        border-bottom: 2px solid #f0f2f5;
        margin-bottom: 20px;
    }
    .main-header h1 {
        font-size: 1.85rem; font-weight: 700;
        margin: 0 0 2px 0;
        color: #111827; letter-spacing: -0.5px;
        line-height: 1.1;
    }
    .main-header .icon-wrap {
        display: flex; align-items: center; justify-content: center;
        width: 56px; height: 56px; border-radius: 16px;
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.25);
    }
    .subtitle {
        color: #6b7280;
        font-size: 0.9rem;
        margin: 0;
        line-height: 1.2;
    }
    .stat-card {
        background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px;
        padding: 18px 20px; display: flex; align-items: center; gap: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: all 0.2s;
    }
    .stat-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        transform: translateY(-2px);
    }
    .stat-card .icon-wrap {
        display: flex; align-items: center; justify-content: center;
        width: 44px; height: 44px; border-radius: 12px;
        background: #e8f5e9; color: #2E7D32;
        flex-shrink: 0;
    }
    .stat-label { font-size: 0.75rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.6px; font-weight: 600; }
    .stat-value { font-size: 1.5rem; font-weight: 700; color: #111827; margin-top: 2px; line-height: 1.1; }
    .info-box {
        display: flex; align-items: center; gap: 12px;
        padding: 14px 18px; border-radius: 12px;
        background: #eff6ff; border-left: 4px solid #3b82f6;
        color: #1e40af; font-size: 0.9rem;
        margin: 8px 0 16px 0;
    }
    .warn-box {
        display: flex; align-items: center; gap: 12px;
        padding: 14px 18px; border-radius: 12px;
        background: #fffbeb; border-left: 4px solid #f59e0b;
        color: #b45309; font-size: 0.9rem;
        margin: 8px 0 16px 0;
    }
    .section-title {
        display: flex; align-items: center; gap: 10px;
        font-size: 1.2rem; font-weight: 700; color: #111827;
        margin: 24px 0 12px 0; letter-spacing: -0.3px;
    }
    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid #e5e7eb;
    }
    section[data-testid="stSidebar"] .stRadio > label { display: none; }
    section[data-testid="stSidebar"] .stRadio > div { gap: 8px; }
    section[data-testid="stSidebar"] .stRadio > div > label {
        background: #f9fafb;
        padding: 12px 16px;
        border-radius: 10px;
        border: 1.5px solid #e5e7eb;
        transition: all 0.2s;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] .stRadio > div > label:hover {
        background: #f0fdf4;
        border-color: #4CAF50;
    }
    .stFileUploader > div > div {
        border: 2px dashed #d1d5db;
        border-radius: 12px;
        background: #ffffff;
        transition: all 0.2s;
    }
    .stFileUploader > div > div:hover {
        border-color: #4CAF50;
        background: #f0fdf4;
    }
    .stDownloadButton > button {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        color: white;
        border: none;
        padding: 12px 24px;
        border-radius: 10px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.25);
        transition: all 0.2s;
    }
    .stDownloadButton > button:hover {
        box-shadow: 0 6px 16px rgba(76, 175, 80, 0.4);
        transform: translateY(-2px);
        color: white;
    }
    details {
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 8px 12px;
        background: #ffffff;
    }
    .stDataFrame {
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
#  HEADER
# ═══════════════════════════════════════════════════════════════════
st.markdown(f'''
<div class="main-header">
    <div class="icon-wrap">{icon("refresh", 30, "white", 2.5)}</div>
    <div>
        <h1>Master Data Forecast Transformer</h1>
    </div>
</div>
''', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
#  SIDEBAR — Pilih Customer & Mode
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    import base64
    from pathlib import Path

    logo_path = Path(__file__).parent / "logo.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()

        st.markdown(f'''
        <div style="
            display:flex;
            align-items:center;
            justify-content:center;
            margin-top:-3.5rem;
            margin-bottom:0.5rem;
            height:3rem;
            padding-left:3.5rem;
            padding-right:3.5rem;
        ">
            <img src="data:image/png;base64,{logo_b64}"
                 style="max-height:96px;height:auto;max-width:100%;object-fit:contain;display:block;"/>
        </div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown(f'''
        <div style="margin-top:-3.5rem;margin-bottom:0.5rem;color:#ef4444;font-size:0.75rem;padding-left:8px;">
            Logo tidak ditemukan
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("<hr style='margin:4px 0 12px 0;border:none;border-top:1px solid #e5e7eb;'>", unsafe_allow_html=True)

    grup = st.radio(
        "Grup",
        ["Tokai Rika", "Mitsuba"],
        index=0,
        label_visibility="collapsed",
        key="pilih_grup"
    )

    st.markdown("<hr style='margin:10px 0;border:none;border-top:1px solid #e5e7eb;'>", unsafe_allow_html=True)

    if grup == "Tokai Rika":
        st.markdown(f'''
        <div style="display:flex;align-items:center;gap:10px;padding:4px 0 12px 0;">
            {icon("layers", 18, "#4CAF50")}
            <span style="font-weight:700;font-size:0.95rem;color:#111827;">Mode Operasi</span>
        </div>
        ''', unsafe_allow_html=True)

        mode = st.radio(
            "Mode",
            ["Buat Master Baru", "Update Master", "Hitung PDS & Delivery"],
            index=0,
            label_visibility="collapsed",
            key="mode_tokai"
        )
    else:
        st.markdown(f'''
        <div style="display:flex;align-items:center;gap:10px;padding:4px 0 12px 0;">
            {icon("package", 18, "#FF9800")}
            <span style="font-weight:700;font-size:0.95rem;color:#111827;">Mode Operasi</span>
        </div>
        ''', unsafe_allow_html=True)

        mode = st.radio(
            "Mode",
            [
                "Buat Master (Paste)",
                "Update Master",
                "Input Actual PDS",
                "Input Actual Delivery"
            ],
            index=0,
            label_visibility="collapsed",
            key="mode_mitsuba"
        )


# ═══════════════════════════════════════════════════════════════════
#  RENDER HALAMAN
# ═══════════════════════════════════════════════════════════════════
if grup == "Tokai Rika":
    render_tokai(mode)
else:
    render_mitsuba(mode)