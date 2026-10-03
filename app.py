# ═══════════════════════════════════════════════════════════════════════════
#
#   📊  MASTER DATA TRANSFORMER  v3.0
#   ─────────────────────────────────────────────────────────────────────
#   Fitur v3.0:
#   - 3 Mode Operasi:
#       1. Buat Master Baru    — upload file sumber
#       2. Update Master       — upload master + data baru (+ PDS opsional)
#       3. Hitung PDS/Delivery — upload master + PDS (untuk hitung rumus)
#   - Rumus dihitung di Python (bukan formula Excel)
#   - Template PDS & Delivery (auto-generate)
#   - Kolom SAP Code (dari file PDS/Delivery, diulang per Part Number)
#   - Format PDS/Delivery: SAP CODE | ITEM | Jan-26 | Feb-26 | ...
#   - Warna: qty hijau jika ≠ 0, formula hijau jika ≥ 0 / merah jika < 0 / "-"
#
# ═══════════════════════════════════════════════════════════════════════════


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [01] IMPORT LIBRARY                                                  ║
# ╚═══════════════════════════════════════════════════════════════════════╝
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO
from collections import Counter
import re
import warnings
warnings.filterwarnings('ignore')


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [02] KONFIGURASI HALAMAN STREAMLIT                                   ║
# ╚═══════════════════════════════════════════════════════════════════════╝
st.set_page_config(
    page_title="Master Data Transformer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [03] ICON LIBRARY (SVG INLINE - LUCIDE STYLE)                        ║
# ╚═══════════════════════════════════════════════════════════════════════╝
ICONS = {
    "refresh": '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    "file-plus": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/>',
    "file-check": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="m9 15 2 2 4-4"/>',
    "files": '<path d="M15.5 2H8.6c-.4 0-.8.2-1.1.5-.3.3-.5.7-.5 1.1v12.8c0 .4.2.8.5 1.1.3.3.7.5 1.1.5h9.8c.4 0 .8-.2 1.1-.5.3-.3.5-.7.5-1.1V6.5L15.5 2z"/><path d="M3 7.6v12.8c0 .4.2.8.5 1.1.3.3.7.5 1.1.5h9.8"/><path d="M15 2v5h5"/>',
    "folder-open": '<path d="m6 14 1.45-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.55 6a2 2 0 0 1-1.94 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2"/>',
    "settings": '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/>',
    "bar-chart": '<line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "check-circle": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    "alert": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "folder": '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/>',
    "layers": '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    "table": '<path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/>',
    "sparkles": '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/>',
    "package": '<path d="m7.5 4.27 9 5.15"/><path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>',
    "tag": '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><path d="M16 2v4"/><path d="M8 2v4"/><path d="M3 10h18"/>',
    "eye": '<path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/>',
    "shield-check": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
    "clipboard": '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    "shield-alert": '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
    "history": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
    "sigma": '<path d="M18 7V4H6l6 8-6 8h12v-3"/>',
    "calculator": '<rect width="16" height="20" x="4" y="2" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="16" y1="14" x2="16" y2="18"/><path d="M16 10h.01"/><path d="M12 10h.01"/><path d="M8 10h.01"/><path d="M12 14h.01"/><path d="M8 14h.01"/><path d="M12 18h.01"/><path d="M8 18h.01"/>',
    "clipboard-list": '<rect width="8" height="4" x="8" y="2" rx="1" ry="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="M12 11h4"/><path d="M12 16h4"/><path d="M8 11h.01"/><path d="M8 16h.01"/>',
    "zap": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
}


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [04] HELPER FUNCTIONS UNTUK ICON                                     ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def icon(name, size=18, color="currentColor", stroke=2):
    path = ICONS.get(name, ICONS["info"])
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle;display:inline-block;">{path}</svg>'''


def icon_text(name, text, size=18, color="currentColor", gap="8px"):
    return f'''<span style="display:inline-flex;align-items:center;gap:{gap};">{icon(name, size, color)}<span>{text}</span></span>'''


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [05] KONSTANTA GLOBAL                                                ║
# ╚═══════════════════════════════════════════════════════════════════════╝
PART_COL        = 0
PART_NAME_COL   = 1
ORDER_DATE_COL  = 14

BULAN_SCAN_START = 16
BULAN_SCAN_END   = 31

COL_FILE_FROM = 'File From'
COL_TOTAL     = 'Total'
COL_SAP       = 'SAP Code'

LABEL_PDS       = "Actual PDS"
LABEL_DELIVERY  = "Actual Delivery"
LABEL_FC_LATES  = "% FC Lates vs FC Last Month"
LABEL_FC_ACT    = "% FC vs Act PO"
LABEL_ACT_DEL   = "% Act PO vs Act Delivery"

LABELS_RINGKASAN = [LABEL_PDS, LABEL_DELIVERY, LABEL_FC_LATES, LABEL_FC_ACT, LABEL_ACT_DEL]
LABELS_FORMULA   = [LABEL_FC_LATES, LABEL_FC_ACT, LABEL_ACT_DEL]


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [06] FUNGSI VALIDASI FILE                                            ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def cek_duplikat_nama_file(files):
    if not files:
        return True, []
    nama_files = [f.name for f in files]
    counter = Counter(nama_files)
    duplikat = [nama for nama, count in counter.items() if count > 1]
    return (len(duplikat) == 0), duplikat


def cek_file_sudah_di_master(files, df_master):
    if df_master is None or len(df_master) == 0:
        return []
    if COL_FILE_FROM not in df_master.columns:
        return []

    existing = set(
        df_master[COL_FILE_FROM].dropna().astype(str).str.strip().unique()
    )
    existing.discard('')
    existing.discard('nan')
    existing.discard('None')

    nama_baru = [f.name for f in files]
    sudah_ada = [nama for nama in nama_baru if nama in existing]
    return sudah_ada


def tampilkan_error_duplikat(duplikat):
    if not duplikat:
        return
    list_items = "".join([f"<li><code>{nama}</code></li>" for nama in duplikat])
    st.markdown(f'''
    <div style="padding:16px 20px;border-radius:12px;background:#fef2f2;border-left:4px solid #ef4444;color:#991b1b;margin:12px 0;">
        <div style="display:flex;align-items:center;gap:10px;font-weight:700;font-size:1.05rem;margin-bottom:8px;">
            {icon("shield-alert", 22, "#dc2626")}
            <span>Nama File Duplikat Terdeteksi</span>
        </div>
        <div style="font-size:0.9rem;line-height:1.6;">
            File berikut muncul lebih dari satu kali dalam upload ini:
            <ul style="margin:8px 0 8px 20px;padding:0;">{list_items}</ul>
            <b>Silakan hapus duplikat</b> — pastikan setiap file memiliki nama yang unik, lalu upload ulang.
        </div>
    </div>
    ''', unsafe_allow_html=True)


def tampilkan_error_file_sudah_ada(sudah_ada):
    if not sudah_ada:
        return
    list_items = "".join([f"<li><code>{nama}</code></li>" for nama in sudah_ada])
    st.markdown(f'''
    <div style="padding:16px 20px;border-radius:12px;background:#fef2f2;border-left:4px solid #ef4444;color:#991b1b;margin:12px 0;">
        <div style="display:flex;align-items:center;gap:10px;font-weight:700;font-size:1.05rem;margin-bottom:8px;">
            {icon("history", 22, "#dc2626")}
            <span>File Sudah Pernah Di-upload</span>
        </div>
        <div style="font-size:0.9rem;line-height:1.6;">
            File berikut sudah ada di master (kolom <code>File From</code>):
            <ul style="margin:8px 0 8px 20px;padding:0;">{list_items}</ul>
            <b>Ditolak — tidak diproses.</b><br>
            Hapus dari daftar upload, atau rename file sebelum upload.
        </div>
    </div>
    ''', unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [07] FUNGSI DETEKSI BULAN DINAMIS                                    ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def normalisasi_bulan(val):
    if val is None or pd.isna(val):
        return None
    s = str(val).strip()
    if s == '' or s.lower() in ('nan', 'nat', 'none'):
        return None

    m = re.match(r'^(\d{4})[/\-](\d{1,2})$', s)
    if m:
        y, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return f"{y}/{mo}"

    m2 = re.match(r'^(\d{4})\.(\d{1,2})$', s)
    if m2:
        y, mo = int(m2.group(1)), int(m2.group(2))
        if 1 <= mo <= 12:
            return f"{y}/{mo}"

    return None


def konversi_bulan_header(s):
    """Konversi 'Jan-26' → '2026/1', 'Feb-26' → '2026/2', dst."""
    BULAN_MAP = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    s = str(s).strip()
    m = re.match(r'^([A-Za-z]{3})[\-/](\d{2,4})$', s)
    if not m:
        return None
    bln_str = m.group(1).lower()
    thn_str = m.group(2)
    if bln_str not in BULAN_MAP:
        return None
    thn = int(thn_str)
    if thn < 100:
        thn += 2000
    return f"{thn}/{BULAN_MAP[bln_str]}"


def sort_bulan_key(b):
    y, m = b.split('/')
    return (int(y), int(m))


def bulan_prev(b):
    y, m = b.split('/')
    y, m = int(y), int(m)
    if m == 1:
        return f"{y-1}/12"
    return f"{y}/{m-1}"


def date_to_month_key(date_str):
    if not date_str:
        return None
    try:
        dt = pd.to_datetime(date_str)
        if pd.notna(dt) and not (dt.year == 1970 and dt.month == 1 and dt.day == 1):
            return f"{dt.year}/{dt.month}"
    except:
        pass
    return None


def deteksi_baris_header_bulan(df_raw, max_scan=10, min_bulan=2):
    for i in range(min(max_scan, len(df_raw))):
        row = df_raw.iloc[i]
        kolom_bulan_map = {}
        for col_idx in range(BULAN_SCAN_START, min(BULAN_SCAN_END, len(row))):
            val = row.iloc[col_idx] if col_idx < len(row) else None
            bulan = normalisasi_bulan(val)
            if bulan and bulan not in kolom_bulan_map:
                kolom_bulan_map[bulan] = col_idx
        if len(kolom_bulan_map) >= min_bulan:
            return i, kolom_bulan_map
    return None, {}


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [08] FUNGSI UTILITAS UMUM                                            ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def to_number(val):
    if val is None or pd.isna(val):
        return 0
    try:
        s = str(val).replace(',', '').strip()
        if s == '' or s.lower() in ('nan', 'none', '-'):
            return 0
        return int(float(s))
    except:
        return 0


def to_date_str(val):
    if val is None:
        return ''
    if pd.isna(val):
        return ''
    if isinstance(val, (pd.Timestamp, datetime)):
        try:
            if val.year == 1970 and val.month == 1 and val.day == 1:
                return ''
            return val.strftime('%Y/%m/%d')
        except:
            return ''
    s = str(val).strip()
    if s == '' or s.lower() in ('nan', 'nat', 'none', '1970/01/01', '1970-01-01'):
        return ''
    try:
        dt = pd.to_datetime(val)
        if pd.notna(dt):
            if dt.year == 1970 and dt.month == 1 and dt.day == 1:
                return ''
            return dt.strftime('%Y/%m/%d')
    except:
        pass
    return s


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [09] FUNGSI BACA FILE (MULTI-FORMAT)                                 ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def baca_file_apapun(file_obj):
    file_obj.seek(0)
    try:
        df_raw = pd.read_excel(file_obj, header=None, dtype=str)
        header_row, kolom_bulan_map = deteksi_baris_header_bulan(df_raw)
        if header_row is not None and kolom_bulan_map:
            df_data = df_raw.iloc[header_row + 1:].reset_index(drop=True)
            return df_data, kolom_bulan_map, "Excel"
        raise ValueError("Tidak bisa deteksi baris header bulan di file Excel")
    except Exception as e1:
        file_obj.seek(0)
        try:
            tables = pd.read_html(file_obj)
            df_raw = tables[0].astype(str)
            header_row, kolom_bulan_map = deteksi_baris_header_bulan(df_raw)
            if header_row is not None and kolom_bulan_map:
                df_data = df_raw.iloc[header_row + 1:].reset_index(drop=True)
                return df_data, kolom_bulan_map, "HTML"
        except: pass

        file_obj.seek(0)
        try:
            df_raw = pd.read_csv(file_obj, header=None, dtype=str)
            header_row, kolom_bulan_map = deteksi_baris_header_bulan(df_raw)
            if header_row is not None and kolom_bulan_map:
                df_data = df_raw.iloc[header_row + 1:].reset_index(drop=True)
                return df_data, kolom_bulan_map, "CSV"
        except: pass

        raise ValueError(f"Tidak bisa membaca file: {e1}")


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [10] FUNGSI EKSTRAKSI DATA (1 FILE)                                  ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def ekstrak_data(df, kolom_bulan_map, nama_file=""):
    if len(df) == 0 or not kolom_bulan_map:
        return pd.DataFrame(), {}, {}

    rows = []
    pds_map = {}
    delivery_map = {}
    part_no_terakhir = None

    for idx in range(len(df)):
        row = df.iloc[idx]

        part_no = row.iloc[PART_COL] if PART_COL < len(row) else None
        if part_no is None or pd.isna(part_no):
            continue
        s_part = str(part_no).strip()
        if s_part == '' or s_part.lower() in ('nan', 'none'):
            continue
        if normalisasi_bulan(s_part):
            continue

        s_norm = s_part.lower()
        if s_norm in [lbl.lower() for lbl in LABELS_RINGKASAN]:
            if (s_norm == LABEL_PDS.lower() or s_norm == LABEL_DELIVERY.lower()) and part_no_terakhir:
                nilai = {}
                for bulan, col_idx in kolom_bulan_map.items():
                    v = row.iloc[col_idx] if col_idx < len(row) else None
                    if v is None or pd.isna(v):
                        continue
                    s_v = str(v).strip()
                    if s_v == '' or s_v.lower() in ('nan', 'none', '-'):
                        continue
                    nilai[bulan] = to_number(v)
                if nilai:
                    if s_norm == LABEL_PDS.lower():
                        pds_map.setdefault(part_no_terakhir, {}).update(nilai)
                    else:
                        delivery_map.setdefault(part_no_terakhir, {}).update(nilai)
            continue

        part_name = row.iloc[PART_NAME_COL] if PART_NAME_COL < len(row) else ''
        if pd.isna(part_name): part_name = ''

        date_val = to_date_str(row.iloc[ORDER_DATE_COL]) if ORDER_DATE_COL < len(row) else ''

        row_data = {
            'Part Number': s_part,
            'Part Name': str(part_name).strip(),
            'Date': date_val,
            COL_FILE_FROM: nama_file,
        }
        for bulan, col_idx in kolom_bulan_map.items():
            val = row.iloc[col_idx] if col_idx < len(row) else None
            row_data[bulan] = to_number(val)
        rows.append(row_data)
        part_no_terakhir = s_part

    return pd.DataFrame(rows), pds_map, delivery_map


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [11] FUNGSI EKSTRAKSI DARI BANYAK FILE                               ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def ekstrak_dari_banyak_file(files):
    ok, duplikat = cek_duplikat_nama_file(files)
    if not ok:
        raise ValueError("Nama file duplikat terdeteksi: " + ", ".join(duplikat))

    semua_df = []
    info_files = []
    semua_bulan = set()
    pds_all = {}
    delivery_all = {}

    for f in files:
        try:
            df_data, kolom_bulan_map, fmt = baca_file_apapun(f)
            df_extracted, pds_map, delivery_map = ekstrak_data(df_data, kolom_bulan_map, nama_file=f.name)

            for pn, nilai in pds_map.items():
                pds_all.setdefault(pn, {}).update(nilai)
            for pn, nilai in delivery_map.items():
                delivery_all.setdefault(pn, {}).update(nilai)

            bulan_ditemukan = set(kolom_bulan_map.keys())
            semua_bulan.update(bulan_ditemukan)

            semua_df.append(df_extracted)
            info_files.append({
                'name': f.name,
                'format': fmt,
                'rows_raw': len(df_data),
                'rows_clean': len(df_extracted),
                'bulan': sorted(bulan_ditemukan, key=sort_bulan_key),
                'status': 'OK'
            })
        except Exception as e:
            info_files.append({
                'name': f.name,
                'format': '-',
                'rows_raw': 0,
                'rows_clean': 0,
                'bulan': [],
                'status': f'ERROR: {e}'
            })

    if semua_df:
        df_combined = pd.concat(semua_df, ignore_index=True)
        return df_combined, info_files, semua_bulan, pds_all, delivery_all
    return pd.DataFrame(), info_files, set(), {}, {}


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [11b] BACA FILE PDS & DELIVERY                                       ║
# ║  Format: SAP CODE | ITEM | Jan-26 | Feb-26 | ... | Dec-26             ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def baca_file_pds_delivery(file_obj):
    """
    Baca file PDS & Delivery.
    Format: SAP CODE | ITEM | 2026/1 | 2026/2 | ...
    PDS & Delivery qty SAMA (dari sumber yang sama).
    Return: (pds_map, delivery_map, sap_map, info)
    """
    pds_map = {}
    delivery_map = {}
    sap_map = {}
    errors = []
    total_rows = 0
    valid_rows = 0

    try:
        file_obj.seek(0)
        df = pd.read_excel(file_obj, header=0, dtype=str)
    except:
        try:
            file_obj.seek(0)
            df = pd.read_csv(file_obj, header=0, dtype=str)
        except Exception as e:
            raise ValueError(f"Tidak bisa baca file PDS/Delivery: {e}")

    df.columns = [str(c).strip() for c in df.columns]

    col_sap = None
    col_item = None
    kolom_bulan_map = {}

    for c in df.columns:
        c_low = c.lower()
        if c_low in ('sap code', 'sap_code', 'sapcode', 'sap'):
            col_sap = c
        elif c_low in ('item', 'part number', 'part_number', 'partnumber', 'part no'):
            col_item = c
        else:
            # Header bulan langsung format '2026/1' dst.
            bulan = normalisasi_bulan(c)
            if bulan and bulan not in kolom_bulan_map:
                kolom_bulan_map[bulan] = c

    if col_item is None:
        raise ValueError("Kolom 'ITEM' tidak ditemukan di file PDS/Delivery")
    if not kolom_bulan_map:
        raise ValueError("Tidak ada kolom bulan (2026/1, 2026/2, ...) di file PDS/Delivery")

    def _ada_nilai(v):
        if v is None:
            return False
        try:
            if pd.isna(v):
                return False
        except:
            pass
        s = str(v).strip()
        return s != '' and s.lower() not in ('nan', 'none', '-')

    for idx, row in df.iterrows():
        total_rows += 1

        pn = str(row.get(col_item, '')).strip()
        if not pn or pn.lower() in ('nan', 'none', ''):
            continue

        sap = str(row.get(col_sap, '')).strip() if col_sap else ''
        if sap.lower() in ('nan', 'none'):
            sap = ''

        if sap:
            sap_map.setdefault(pn, sap)

        for bulan, nama_kolom in kolom_bulan_map.items():
            v = row.get(nama_kolom, '')
            if not _ada_nilai(v):
                continue
            num = to_number(v)
            if num == 0:
                continue
            pds_map.setdefault(pn, {})[bulan] = num
            delivery_map.setdefault(pn, {})[bulan] = num

        valid_rows += 1

    return pds_map, delivery_map, sap_map, {
        'rows': total_rows,
        'valid': valid_rows,
        'errors': errors[:10]
    }


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [11c] FUNGSI BIKIN TEMPLATE PDS & DELIVERY                           ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def buat_template_pds_delivery(parts_unik=None, bulan_sorted=None):
    output = BytesIO()

    if parts_unik and bulan_sorted:
        rows = []
        for item in parts_unik:
            pn = item[0] if isinstance(item, (list, tuple)) else item
            row = {'SAP CODE': '', 'ITEM': pn}
            for b in bulan_sorted:
                row[b] = ''
            rows.append(row)
        df = pd.DataFrame(rows)
    else:
        df = pd.DataFrame({
            'SAP CODE': ['1347-03686', '1347-03580', '1347-03687'],
            'ITEM': ['17M036-7010B', '17M036-7010A', '17M037-7010B'],
            '2026/1': [150, 200, 300],
            '2026/2': [160, 210, 320],
            '2026/3': [170, 220, 330],
        })

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='PDS_Delivery', index=False)
        workbook = writer.book
        worksheet = writer.sheets['PDS_Delivery']

        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter',
            'align': 'center', 'fg_color': '#4CAF50',
            'font_color': 'white', 'border': 1
        })
        text_format = workbook.add_format({'border': 1, 'align': 'left'})
        number_format = workbook.add_format({'num_format': '#,##0', 'border': 1, 'align': 'right'})

        for col_num, col_name in enumerate(df.columns):
            worksheet.write(0, col_num, col_name, header_format)

        worksheet.set_column(0, 0, 15, text_format)
        worksheet.set_column(1, 1, 20, text_format)
        if len(df.columns) > 2:
            worksheet.set_column(2, len(df.columns) - 1, 14, number_format)
        worksheet.freeze_panes(1, 0)

    output.seek(0)
    return output


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [11d] FUNGSI EKSTRAK DATA DARI MASTER (untuk MODE 3)                 ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def ekstrak_dari_master(df_master):
    """
    Ambil baris data (Part Number, Part Name, Date, bulan-bulan) dari master.
    Return: (df_data, bulan_sorted_dari_master)
    """
    if df_master is None or len(df_master) == 0:
        return pd.DataFrame(), []

    # Deteksi kolom bulan di master
    bulan_cols = []
    for c in df_master.columns:
        b = normalisasi_bulan(c)
        if b:
            bulan_cols.append(b)

    bulan_sorted = sorted(bulan_cols, key=sort_bulan_key)

    # Ambil baris data (bukan ringkasan)
    df_master = df_master.copy()
    if 'Part Number' in df_master.columns:
        df_master = df_master[~df_master['Part Number'].astype(str).isin(LABELS_RINGKASAN)]

    rows = []
    for idx in range(len(df_master)):
        row = df_master.iloc[idx]
        pn = str(row.get('Part Number', '')).strip()
        if not pn or pn.lower() in ('nan', 'none', ''):
            continue

        pname = str(row.get('Part Name', '')).strip()
        if pname.lower() in ('nan', 'none'):
            pname = ''

        date_val = to_date_str(row.get('Date', ''))

        file_from = str(row.get(COL_FILE_FROM, '')).strip()
        if file_from.lower() in ('nan', 'none'):
            file_from = ''

        sap_code = str(row.get(COL_SAP, '')).strip()
        if sap_code.lower() in ('nan', 'none'):
            sap_code = ''

        row_data = {
            'Part Number': pn,
            'Part Name': pname,
            'Date': date_val,
            COL_FILE_FROM: file_from,
            COL_SAP: sap_code,
        }
        for b in bulan_sorted:
            if b in row.index:
                row_data[b] = to_number(row[b])
            else:
                row_data[b] = 0
        rows.append(row_data)

    df_data = pd.DataFrame(rows)
    return df_data, bulan_sorted


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [12] FUNGSI HITUNG RINGKASAN GRUP                                    ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def hitung_ringkasan_grup(group, bulan_sorted, pds_map=None, delivery_map=None):
    hasil = {label: {} for label in LABELS_FORMULA}
    pds = pds_map or {}
    delivery = delivery_map or {}

    group = group.copy()
    group['_Date_sort'] = pd.to_datetime(group['Date'], errors='coerce')
    group = group.sort_values('_Date_sort', kind='stable').reset_index(drop=True)
    group['_bulan_date'] = group['Date'].apply(date_to_month_key)

    def _ambil_angka(v):
        if v is None:
            return None
        try:
            if pd.isna(v):
                return None
        except:
            pass
        s = str(v).replace(',', '').strip()
        if s == '' or s.lower() in ('nan', 'none', '-'):
            return None
        try:
            return float(s)
        except:
            return None

    # 1. Baris terakhir per bulan (berdasarkan Date, apapun nilai kolomnya)
    #    → untuk qty_lalu
    baris_terakhir_per_bulan = {}
    for bln, sub in group.groupby('_bulan_date', sort=False):
        if bln is None:
            continue
        baris_terakhir_per_bulan[bln] = sub.iloc[-1]

    # 2. Baris terakhir per bulan YANG NILAI KOLOM BULANNYA ≠ 0
    #    → untuk qty_ini
    baris_valid_per_bulan = {}
    for bln, sub in group.groupby('_bulan_date', sort=False):
        if bln is None:
            continue
        for i in range(len(sub) - 1, -1, -1):
            row = sub.iloc[i]
            v = _ambil_angka(row.get(bln))
            if v is not None and v != 0:
                baris_valid_per_bulan[bln] = row
                break

    for b in bulan_sorted:
        b_prev = bulan_prev(b)

        # qty_ini: kolom b di baris terakhir bulan b yang kolom b-nya ≠ 0
        row_ini = baris_valid_per_bulan.get(b)
        qty_ini = None
        if row_ini is not None and b in row_ini.index:
            qty_ini = _ambil_angka(row_ini[b])

        # qty_lalu: kolom b di baris TERAKHIR bulan b_prev (apapun nilai kolom b-nya)
        row_lalu = baris_terakhir_per_bulan.get(b_prev)
        qty_lalu = None
        if row_lalu is not None and b in row_lalu.index:
            qty_lalu = _ambil_angka(row_lalu[b])

        # % FC Lates vs FC Last Month
        if qty_ini is None or qty_lalu is None or qty_lalu == 0:
            hasil[LABEL_FC_LATES][b] = None
        else:
            hasil[LABEL_FC_LATES][b] = 1 - (qty_ini / qty_lalu)

        # % FC vs Act PO
        pds_b = pds.get(b) if pds else None
        if qty_ini is None or pds_b is None or pds_b == 0:
            hasil[LABEL_FC_ACT][b] = None
        else:
            hasil[LABEL_FC_ACT][b] = 1 - (qty_ini / pds_b)

        # % Act PO vs Act Delivery
        del_b = delivery.get(b) if delivery else None
        if pds_b is None or del_b is None or del_b == 0:
            hasil[LABEL_ACT_DEL][b] = None
        else:
            hasil[LABEL_ACT_DEL][b] = 1 - (pds_b / del_b)

    return hasil


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [13] FUNGSI PROSES UPDATE / GABUNG MASTER                            ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def proses_update(df_master_lama, df_baru, semua_bulan, pds_all=None, delivery_all=None, sap_map=None):
    sap_map = sap_map or {}
    bulan_sorted = sorted(semua_bulan, key=sort_bulan_key)
    base_cols = ['Part Number', 'Part Name', 'Date', COL_FILE_FROM]

    def build_kolom_baru():
        return base_cols + [COL_SAP] + bulan_sorted + [COL_TOTAL]

    def normalize_df(df):
        kolom_baru = build_kolom_baru()
        if df is None or len(df) == 0:
            return pd.DataFrame(columns=kolom_baru)
        df = df.copy()
        df = df.drop(columns=['No'], errors='ignore')
        df = df.drop(columns=[COL_TOTAL], errors='ignore')
        df = df.drop(columns=[COL_SAP], errors='ignore')
        if 'Part Number' in df.columns:
            df = df[~df['Part Number'].astype(str).isin(LABELS_RINGKASAN)]
        for c in base_cols:
            if c not in df.columns:
                df[c] = ''
        df['Date'] = df['Date'].apply(to_date_str)
        df[COL_FILE_FROM] = df[COL_FILE_FROM].fillna('').astype(str).str.strip()
        df.loc[df[COL_FILE_FROM].str.lower().isin(['nan', 'none']), COL_FILE_FROM] = ''
        for b in bulan_sorted:
            if b not in df.columns:
                df[b] = 0
            else:
                df[b] = df[b].apply(to_number)
        df[COL_TOTAL] = df[bulan_sorted].sum(axis=1).astype(int)

        # Tambah kolom SAP Code berdasarkan Part Number
        df[COL_SAP] = df['Part Number'].apply(
            lambda pn: sap_map.get(str(pn).strip(), '')
        )

        return df[kolom_baru]

    if df_master_lama is not None and len(df_master_lama) > 0:
        for c in list(df_master_lama.columns):
            b = normalisasi_bulan(c)
            if b:
                semua_bulan.add(b)
        bulan_sorted = sorted(semua_bulan, key=sort_bulan_key)

        df_master_norm = normalize_df(df_master_lama)
        df_combined = pd.concat([df_master_norm, normalize_df(df_baru)], ignore_index=True)
    else:
        df_combined = normalize_df(df_baru)

    df_combined = df_combined.drop_duplicates(
        subset=['Part Number', 'Date'], keep='last'
    ).reset_index(drop=True)

    df_combined['Date_sort'] = pd.to_datetime(df_combined['Date'], errors='coerce')
    df_combined = df_combined.sort_values(
        by=['Part Number', 'Date_sort'], ascending=[True, True]
    ).reset_index(drop=True)
    df_combined = df_combined.drop(columns=['Date_sort'])

    df_final = tambah_baris_ringkasan(
        df_combined, bulan_sorted,
        pds_all or {}, delivery_all or {},
        sap_map
    )
    return df_final, bulan_sorted


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [14] FUNGSI TAMBAH BARIS RINGKASAN                                   ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def tambah_baris_ringkasan(df, bulan_sorted, pds_all=None, delivery_all=None, sap_map=None):
    semua_baris = []
    counter_data = 0
    pds_all = pds_all or {}
    delivery_all = delivery_all or {}
    sap_map = sap_map or {}

    for part_no, group in df.groupby('Part Number', sort=False):
        group = group.copy()
        group['No'] = range(counter_data + 1, counter_data + 1 + len(group))
        counter_data += len(group)
        semua_baris.append(group)

        pds_grup = pds_all.get(part_no, {})
        del_grup = delivery_all.get(part_no, {})

        ringkasan = hitung_ringkasan_grup(group, bulan_sorted, pds_grup, del_grup)

        # Actual PDS
        row_pds = {
            'No': '', 'Part Number': LABEL_PDS, 'Part Name': '',
            'Date': '', COL_FILE_FROM: '', COL_SAP: '',
        }
        for b in bulan_sorted:
            v = pds_grup.get(b)
            row_pds[b] = v if v is not None else ''
        row_pds[COL_TOTAL] = sum(
            v for v in (pds_grup.get(b) for b in bulan_sorted) if v is not None
        )
        semua_baris.append(pd.DataFrame([row_pds]))

        # Actual Delivery
        row_del = {
            'No': '', 'Part Number': LABEL_DELIVERY, 'Part Name': '',
            'Date': '', COL_FILE_FROM: '', COL_SAP: '',
        }
        for b in bulan_sorted:
            v = del_grup.get(b)
            row_del[b] = v if v is not None else ''
        row_del[COL_TOTAL] = sum(
            v for v in (del_grup.get(b) for b in bulan_sorted) if v is not None
        )
        semua_baris.append(pd.DataFrame([row_del]))

        # Formula
        for label in LABELS_FORMULA:
            row_f = {
                'No': '', 'Part Number': label, 'Part Name': '',
                'Date': '', COL_FILE_FROM: '', COL_SAP: '',
            }
            total_pct = 0.0
            ada_nilai = False
            for b in bulan_sorted:
                v = ringkasan.get(label, {}).get(b)
                row_f[b] = v if v is not None else ''
                if v is not None:
                    total_pct += float(v)
                    ada_nilai = True
            row_f[COL_TOTAL] = total_pct if ada_nilai else ''
            semua_baris.append(pd.DataFrame([row_f]))

    df_hasil = pd.concat(semua_baris, ignore_index=True)
    cols = list(df_hasil.columns)
    if 'No' in cols:
        cols.remove('No')
        cols = ['No'] + cols
        df_hasil = df_hasil[cols]
    return df_hasil


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [15] FUNGSI EXPORT KE EXCEL                                          ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def buat_excel(df, bulan_sorted):
    output = BytesIO()

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Master Data', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Master Data']

        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter',
            'align': 'center', 'fg_color': '#4CAF50',
            'font_color': 'white', 'border': 1
        })
        text_format = workbook.add_format({'border': 1, 'align': 'left'})
        center_format = workbook.add_format({'border': 1, 'align': 'center'})

        bulan_ada_format = workbook.add_format({
            'num_format': '#,##0', 'border': 1, 'align': 'right',
            'bg_color': '#C8E6C9',
        })
        bulan_kosong_format = workbook.add_format({
            'num_format': '#,##0', 'border': 1, 'align': 'right',
        })
        total_format = workbook.add_format({
            'num_format': '#,##0', 'border': 1, 'align': 'right',
            'bold': True, 'bg_color': '#A5D6A7',
        })

        ringkasan_merged_format = workbook.add_format({
            'bold': True, 'italic': True,
            'bg_color': '#FFF9C4',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        ringkasan_value_format = workbook.add_format({
            'bg_color': '#FFF9C4',
            'border': 1, 'align': 'right',
            'num_format': '#,##0',
        })
        ringkasan_empty_format = workbook.add_format({
            'bg_color': '#FFF9C4',
            'border': 1, 'align': 'center',
        })

        formula_format = workbook.add_format({
            'border': 1, 'align': 'right',
            'num_format': '0.00%',
            'bg_color': '#FFF9C4',
            'bold': True,
        })
        formula_error_format = workbook.add_format({
            'border': 1, 'align': 'center',
            'bg_color': '#FFCDD2',
            'font_color': '#B71C1C',
            'bold': True,
        })

        cond_hijau = workbook.add_format({
            'bg_color': '#C8E6C9',
            'font_color': '#1B5E20',
            'bold': True,
            'num_format': '0.00%',
            'border': 1, 'align': 'right',
        })
        cond_merah = workbook.add_format({
            'bg_color': '#FFCDD2',
            'font_color': '#B71C1C',
            'bold': True,
            'num_format': '0.00%',
            'border': 1, 'align': 'right',
        })

        col_names = list(df.columns.values)

        for col_num, col_name in enumerate(col_names):
            worksheet.write(0, col_num, col_name, header_format)
            if col_name == 'No':
                worksheet.set_column(col_num, col_num, 6, center_format)
            elif col_name == 'Part Number':
                worksheet.set_column(col_num, col_num, 32, text_format)
            elif col_name == 'Part Name':
                worksheet.set_column(col_num, col_num, 35, text_format)
            elif col_name == 'Date':
                worksheet.set_column(col_num, col_num, 12, center_format)
            elif col_name == COL_FILE_FROM:
                worksheet.set_column(col_num, col_num, 35, text_format)
            elif col_name == COL_SAP:
                worksheet.set_column(col_num, col_num, 15, text_format)
            elif col_name == COL_TOTAL:
                worksheet.set_column(col_num, col_num, 14, total_format)
            else:
                worksheet.set_column(col_num, col_num, 12, bulan_kosong_format)

        idx_no   = col_names.index('No')
        idx_sap  = col_names.index(COL_SAP)
        merge_first = idx_no
        merge_last  = idx_sap

        for row_idx in range(len(df)):
            excel_row = row_idx + 1
            label = str(df.iloc[row_idx].get('Part Number', '')).strip()

            if label in LABELS_RINGKASAN:
                worksheet.merge_range(
                    excel_row, merge_first,
                    excel_row, merge_last,
                    label, ringkasan_merged_format
                )

                for col_idx, col_name in enumerate(col_names):
                    if col_idx <= merge_last:
                        continue

                    if col_name in bulan_sorted:
                        val = df.iloc[row_idx][col_name]

                        if label in (LABEL_PDS, LABEL_DELIVERY):
                            if val == '' or val is None or (isinstance(val, float) and pd.isna(val)):
                                worksheet.write(excel_row, col_idx, '', ringkasan_value_format)
                            else:
                                try:
                                    num = float(val)
                                    worksheet.write(excel_row, col_idx, num, ringkasan_value_format)
                                except:
                                    worksheet.write(excel_row, col_idx, '', ringkasan_value_format)
                        elif label in LABELS_FORMULA:
                            num = None
                            if val is not None and not (isinstance(val, float) and pd.isna(val)) and val != '':
                                try: num = float(val)
                                except: num = None
                            if num is None:
                                worksheet.write(excel_row, col_idx, '-', formula_error_format)
                            else:
                                worksheet.write(excel_row, col_idx, num, formula_format)
                        else:
                            worksheet.write(excel_row, col_idx, '', ringkasan_empty_format)
                    elif col_name == COL_TOTAL:
                        val = df.iloc[row_idx][col_name]
                        kosong = (val == '' or val is None or (isinstance(val, float) and pd.isna(val)))

                        if kosong:
                            worksheet.write(excel_row, col_idx, '', ringkasan_empty_format)
                        else:
                            try:
                                num = float(val)
                            except:
                                num = None

                            if num is None:
                                worksheet.write(excel_row, col_idx, '', ringkasan_empty_format)
                            elif label in (LABEL_PDS, LABEL_DELIVERY):
                                worksheet.write(excel_row, col_idx, num, ringkasan_value_format)
                            elif label in LABELS_FORMULA:
                                worksheet.write(excel_row, col_idx, num, formula_format)
                            else:
                                worksheet.write(excel_row, col_idx, num, ringkasan_value_format)
            else:
                for col_idx, col_name in enumerate(col_names):
                    val = df.iloc[row_idx][col_name]
                    kosong = (val == '' or val is None or (isinstance(val, float) and pd.isna(val)))

                    if col_name in ('Part Number', 'Part Name', COL_FILE_FROM, COL_SAP):
                        worksheet.write(excel_row, col_idx, '' if kosong else val, text_format)
                    elif col_name in ('No', 'Date'):
                        worksheet.write(excel_row, col_idx, '' if kosong else val, center_format)
                    elif col_name == COL_TOTAL:
                        worksheet.write(excel_row, col_idx, '' if kosong else val, total_format)
                    elif col_name in bulan_sorted:
                        if kosong:
                            worksheet.write(excel_row, col_idx, '', bulan_kosong_format)
                        else:
                            try: num_val = float(val)
                            except: num_val = None
                            if num_val is not None and num_val != 0:
                                worksheet.write(excel_row, col_idx, val, bulan_ada_format)
                            else:
                                worksheet.write(excel_row, col_idx, val, bulan_kosong_format)
                    else:
                        worksheet.write(excel_row, col_idx, '' if kosong else val, text_format)

        bulan_to_col_idx = {b: col_names.index(b) for b in bulan_sorted if b in col_names}
        for row_idx in range(len(df)):
            excel_row = row_idx + 1
            label = str(df.iloc[row_idx].get('Part Number', '')).strip()
            if label not in LABELS_FORMULA:
                continue
            for b in bulan_sorted:
                if b not in bulan_to_col_idx:
                    continue
                ci = bulan_to_col_idx[b]
                worksheet.conditional_format(
                    excel_row, ci, excel_row, ci,
                    {'type': 'cell', 'criteria': '>=', 'value': 0, 'format': cond_hijau}
                )
                worksheet.conditional_format(
                    excel_row, ci, excel_row, ci,
                    {'type': 'cell', 'criteria': '<', 'value': 0, 'format': cond_merah}
                )

        worksheet.freeze_panes(1, 0)

    output.seek(0)
    return output


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [16] FUNGSI UI UNTUK MENAMPILKAN INFO                                ║
# ╚═══════════════════════════════════════════════════════════════════════╝
def tampilkan_info_files(info_files):
    total_ok = sum(1 for i in info_files if i['status'] == 'OK')
    total_err = len(info_files) - total_ok

    st.markdown(f'''
    <div style="display:flex;align-items:center;gap:10px;padding:10px 0;font-weight:600;color:#111827;">
        {icon("files", 18, "#4CAF50")}
        <span>File yang diproses: {len(info_files)} total
        <span style="color:#22c55e;">({total_ok} OK</span>
        {f'<span style="color:#ef4444;">, {total_err} gagal)</span>' if total_err > 0 else ')'}
        </span>
    </div>
    ''', unsafe_allow_html=True)

    for i, info in enumerate(info_files, 1):
        if info['status'] == 'OK':
            bulan_str = ", ".join(info['bulan']) if info['bulan'] else "-"
            st.markdown(f'''
            <div style="display:flex;align-items:center;gap:10px;padding:8px 14px;background:#f0fdf4;border-left:3px solid #22c55e;border-radius:8px;margin-bottom:6px;font-size:0.85rem;">
                {icon("check-circle", 16, "#22c55e")}
                <span style="flex:1;color:#15803d;">
                    <b>{i}.</b> {info["name"]} — {info["format"]} — {info["rows_clean"]} baris — bulan: <b>{bulan_str}</b>
                </span>
            </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown(f'''
            <div style="display:flex;align-items:center;gap:10px;padding:8px 14px;background:#fef2f2;border-left:3px solid #ef4444;border-radius:8px;margin-bottom:6px;font-size:0.85rem;">
                {icon("alert", 16, "#ef4444")}
                <span style="flex:1;color:#b91c1c;">
                    <b>{i}.</b> {info["name"]} — {info["status"]}
                </span>
            </div>
            ''', unsafe_allow_html=True)


def tampilkan_bulan_badges(bulan_sorted):
    if not bulan_sorted:
        return
    st.markdown(f'''
    <div style="display:flex;align-items:center;gap:10px;padding:10px 0;flex-wrap:wrap;">
        {icon("calendar", 18, "#4CAF50")}
        <span style="font-weight:600;color:#111827;">Kolom bulan terdeteksi ({len(bulan_sorted)}):</span>
    </div>
    ''', unsafe_allow_html=True)

    badges_html = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;">'
    for b in bulan_sorted:
        badges_html += f'''<span style="display:inline-flex;align-items:center;gap:6px;padding:6px 12px;background:#e8f5e9;color:#2E7D32;border-radius:20px;font-size:0.82rem;font-weight:600;border:1px solid #c8e6c9;">{icon("calendar", 13, "#2E7D32")}{b}</span>'''
    badges_html += f'''<span style="display:inline-flex;align-items:center;gap:6px;padding:6px 12px;background:#c8e6c9;color:#1B5E20;border-radius:20px;font-size:0.82rem;font-weight:700;border:1px solid #a5d6a7;">{icon("sigma", 13, "#1B5E20")}Total</span>'''
    badges_html += '</div>'
    st.markdown(badges_html, unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [17] CUSTOM CSS                                                      ║
# ╚═══════════════════════════════════════════════════════════════════════╝
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
        margin: 0; color: #111827; letter-spacing: -0.5px;
    }
    .main-header .icon-wrap {
        display: flex; align-items: center; justify-content: center;
        width: 56px; height: 56px; border-radius: 16px;
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        color: white;
        box-shadow: 0 4px 12px rgba(76, 175, 80, 0.25);
    }
    .subtitle { color: #6b7280; font-size: 0.9rem; margin-top: 4px; }
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


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [18] HEADER APLIKASI                                                 ║
# ╚═══════════════════════════════════════════════════════════════════════╝
st.markdown(f'''
<div class="main-header">
    <div class="icon-wrap">{icon("refresh", 30, "white", 2.5)}</div>
    <div>
        <h1>Master Data Transformer</h1>
        <div class="subtitle">Transformasi &amp; update data Excel ke Master Data</div>
    </div>
</div>
''', unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [19] SIDEBAR - 3 MODE                                                ║
# ╚═══════════════════════════════════════════════════════════════════════╝
with st.sidebar:
    st.markdown(f'''
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 12px 0;">
        {icon("settings", 20, "#4CAF50")}
        <span style="font-weight:700;font-size:1.05rem;color:#111827;">Pilih Customer</span>
    </div>
    ''', unsafe_allow_html=True)

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
            [
                "Buat Master Baru",
                "Update Master",
                "Hitung PDS & Delivery"
            ],
            index=0,
            label_visibility="collapsed",
            key="mode_tokai"
        )
    else:  # Mitsuba
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
                "Hitung PDS & Delivery"
            ],
            index=0,
            label_visibility="collapsed",
            key="mode_mitsuba"
        )

    st.markdown(f'''
    <div style="display:flex;align-items:center;gap:8px;padding:8px 12px;background:#f0fdf4;border-radius:10px;color:#15803d;font-size:0.8rem;">
        {icon("shield-check", 16, "#15803d")}
        <span>Data diproses lokal di browser</span>
    </div>
    ''', unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [20] MODE 1: BUAT MASTER BARU                                        ║
# ╚═══════════════════════════════════════════════════════════════════════╝
if grup == "Mitsuba":

    # ═══════════════════════════════════════════════════════════════
    #  PAGE 1: BUAT MASTER (PASTE)
    # ═══════════════════════════════════════════════════════════════
    if mode == "Buat Master (Paste)":
        st.markdown(f'''
        <div class="section-title">{icon("package", 22, "#FF9800")} Mitsuba — Buat Master dari Paste</div>
        <div class="info-box">{icon("info", 18, "#3b82f6")} Copy data dari Excel → paste ke tabel (klik sel pertama → Ctrl+V). Baris PDS &amp; Delivery akan dikosongkan dulu — nanti diisi di menu <b>Hitung PDS &amp; Delivery</b>.</div>
        ''', unsafe_allow_html=True)

        # ── Pengaturan kolom bulan ──
        st.markdown(f'<div class="section-title">{icon("calendar", 18, "#FF9800")} Pengaturan Kolom Bulan</div>', unsafe_allow_html=True)

        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            tahun_mulai = st.number_input("Tahun mulai", 2000, 2100, 2026, 1, key="mitsuba_tahun")
        with col_t2:
            bulan_mulai = st.number_input("Bulan mulai", 1, 12, 1, 1, key="mitsuba_bulan")
        with col_t3:
            jumlah_bulan = st.number_input("Jumlah bulan", 1, 60, 12, 1, key="mitsuba_jml")

        kolom_bulan = []
        y, m = int(tahun_mulai), int(bulan_mulai)
        for _ in range(int(jumlah_bulan)):
            kolom_bulan.append(f"{y}/{m}")
            m += 1
            if m > 12:
                m = 1
                y += 1

        badges = "".join([
            f'<span style="display:inline-flex;align-items:center;gap:6px;padding:5px 10px;background:#fff7ed;color:#9a3412;border-radius:16px;font-size:0.78rem;font-weight:600;border:1px solid #fed7aa;margin:3px;">{b}</span>'
            for b in kolom_bulan
        ])
        st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin:8px 0 16px 0;">{badges}</div>', unsafe_allow_html=True)

        # ── Tabel paste ──
        st.markdown(f'<div class="section-title">{icon("table", 18, "#FF9800")} Tabel Data (Paste dari Excel)</div>', unsafe_allow_html=True)

        kolom_fix = ["No", "PART NAME", "PART NO"]
        semua_kolom = kolom_fix + kolom_bulan

        col_a, col_b = st.columns([1, 3])
        with col_a:
            n_rows = st.number_input(
                "Jumlah baris awal",
                min_value=1, max_value=1000, value=10, step=1,
                key="mitsuba_n_rows"
            )
        with col_b:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            st.caption("Klik sel pertama → Ctrl+V untuk paste dari Excel. Tambah baris dengan tombol di bawah tabel.")

        df_kosong = pd.DataFrame({c: [""] * int(n_rows) for c in semua_kolom})

        df_paste = st.data_editor(
            df_kosong,
            num_rows="dynamic",
            use_container_width=True,
            key="mitsuba_editor",
            column_config={
                "No": st.column_config.TextColumn("No", width="small"),
                "PART NAME": st.column_config.TextColumn("PART NAME", width="medium"),
                "PART NO": st.column_config.TextColumn("PART NO", width="medium"),
            }
        )

        # ── Input tanggal ──
        st.markdown(f'<div class="section-title">{icon("calendar", 18, "#FF9800")} Input Tanggal</div>', unsafe_allow_html=True)

        col_d1, col_d2 = st.columns([1, 2])
        with col_d1:
            tanggal_input = st.date_input(
                "Tanggal Order",
                value=datetime(2026, 1, 1),
                key="mitsuba_tanggal"
            )
        with col_d2:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            st.caption("Tanggal ini dipakai untuk semua baris (format: YYYY/MM/DD).")

        # ── Tombol proses ──
        st.markdown("---")
        proses = st.button("Proses Data", type="primary", use_container_width=True, key="mitsuba_proses")

        if proses:
            df_clean = df_paste.dropna(how="all").reset_index(drop=True)
            mask_kosong = df_clean.apply(
                lambda r: all(str(v).strip() == "" for v in r), axis=1
            )
            df_clean = df_clean[~mask_kosong].reset_index(drop=True)

            if len(df_clean) == 0:
                st.warning("Belum ada data yang di-paste.")
                st.stop()

            try:
                rows = []
                for _, r in df_clean.iterrows():
                    part_name = str(r.get("PART NAME", "")).strip()
                    part_no = str(r.get("PART NO", "")).strip()

                    if not part_no and not part_name:
                        continue

                    row_data = {
                        "No": str(r.get("No", "")).strip(),
                        "Part Number": part_no,
                        "Part Name": part_name,
                        "Date": tanggal_input.strftime("%Y/%m/%d"),
                        COL_FILE_FROM: "PASTE",
                        COL_SAP: "",
                    }
                    for b in kolom_bulan:
                        v = r.get(b, "")
                        row_data[b] = to_number(v) if str(v).strip() not in ("", "nan", "-") else 0
                    rows.append(row_data)

                if not rows:
                    st.warning("Tidak ada baris valid yang bisa diproses.")
                    st.stop()

                df_new = pd.DataFrame(rows)

                st.markdown(f'<div class="section-title">{icon("eye", 20, "#FF9800")} Preview Data Parse</div>', unsafe_allow_html=True)
                st.dataframe(df_new.head(20), use_container_width=True)
                st.caption(f"Total: {len(df_new)} baris")

                # Proses jadi master (PDS/Delivery kosong dulu)
                with st.spinner("Menyusun master..."):
                    semua_bulan = set(kolom_bulan)
                    df_final, bulan_final = proses_update(
                        None, df_new, semua_bulan,
                        {}, {}, {}
                    )
                    excel_bytes = buat_excel(df_final, bulan_final)

                tampilkan_bulan_badges(bulan_final)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f'''
                    <div class="stat-card">
                        <div class="icon-wrap">{icon("table", 22, "#2E7D32")}</div>
                        <div><div class="stat-label">Baris Data</div><div class="stat-value">{len(df_new):,}</div></div>
                    </div>''', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'''
                    <div class="stat-card">
                        <div class="icon-wrap">{icon("package", 22, "#2E7D32")}</div>
                        <div><div class="stat-label">Part Unik</div><div class="stat-value">{df_new["Part Number"].nunique():,}</div></div>
                    </div>''', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'''
                    <div class="stat-card">
                        <div class="icon-wrap">{icon("calendar", 22, "#2E7D32")}</div>
                        <div><div class="stat-label">Kolom Bulan</div><div class="stat-value">{len(bulan_final):,}</div></div>
                    </div>''', unsafe_allow_html=True)
                with col4:
                    st.markdown(f'''
                    <div class="stat-card">
                        <div class="icon-wrap">{icon("layers", 22, "#2E7D32")}</div>
                        <div><div class="stat-label">Total Baris Final</div><div class="stat-value">{len(df_final):,}</div></div>
                    </div>''', unsafe_allow_html=True)

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                st.download_button(
                    label=f"Download Master Mitsuba ({len(df_final)} baris) (.xlsx)",
                    data=excel_bytes,
                    file_name=f"Master_Mitsuba_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                    key="mitsuba_download"
                )

                with st.expander("Lihat Master Final"):
                    st.dataframe(df_final, use_container_width=True)

            except Exception as e:
                st.error(f"Error: {e}")
                st.exception(e)

    # ═══════════════════════════════════════════════════════════════
    #  PAGE 2: HITUNG PDS & DELIVERY
    # ═══════════════════════════════════════════════════════════════
    else:  # mode == "Hitung PDS & Delivery"
        st.markdown(f'''
        <div class="section-title">{icon("calculator", 22, "#FF9800")} Mitsuba — Hitung PDS &amp; Delivery</div>
        <div class="info-box">{icon("info", 18, "#3b82f6")} Upload <b>master Mitsuba</b> (hasil page sebelumnya) + <b>file PDS &amp; Delivery</b>. Rumus % akan dihitung otomatis.</div>
        ''', unsafe_allow_html=True)

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown(f'''
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                {icon("folder-open", 18, "#FF9800")}
                <span style="font-weight:600;color:#111827;">File Master Mitsuba</span>
            </div>
            <div style="font-size:0.8rem;color:#6b7280;margin-bottom:6px;">
                Master yang sudah punya data Part &amp; bulan.
            </div>
            ''', unsafe_allow_html=True)
            file_master = st.file_uploader(
                "Upload file master",
                type=['xlsx', 'xls', 'csv'],
                key='master_file_mitsuba_m2',
                label_visibility="collapsed"
            )

        with col_right:
            st.markdown(f'''
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
                {icon("clipboard-list", 18, "#FF9800")}
                <span style="font-weight:600;color:#111827;">File PDS &amp; Delivery</span>
            </div>
            <div style="font-size:0.8rem;color:#6b7280;margin-bottom:6px;">
                Format: SAP CODE | ITEM | Jan-26 | Feb-26 | ... | Dec-26
            </div>
            ''', unsafe_allow_html=True)
            file_pds = st.file_uploader(
                "Upload file PDS & Delivery",
                type=['xlsx', 'xls', 'csv'],
                key='pds_file_mitsuba_m2',
                label_visibility="collapsed"
            )

        st.markdown("---")

        col_t1, col_t2 = st.columns([1, 3])
        with col_t1:
            if st.button("Template PDS/Delivery", use_container_width=True, key='btn_template_mitsuba_m2'):
                template_bytes = buat_template_pds_delivery()
                st.download_button(
                    label="Download Template Kosong",
                    data=template_bytes,
                    file_name="Template_PDS_Delivery.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key='dl_template_mitsuba_m2'
                )

        if file_master is not None and file_pds is not None:
            try:
                with st.spinner("Membaca master..."):
                    try:
                        file_master.seek(0)
                        df_master_lama = pd.read_excel(file_master, header=0, dtype=str)
                    except:
                        file_master.seek(0)
                        df_master_lama, _, _ = baca_file_apapun(file_master)

                with st.spinner("Mengekstrak data dari master..."):
                    df_data, bulan_sorted_master = ekstrak_dari_master(df_master_lama)

                if len(df_data) == 0:
                    st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Tidak ada data di master.</div>', unsafe_allow_html=True)
                    st.stop()

                st.markdown(f'''
                <div style="padding:14px 18px;border-radius:12px;background:#eff6ff;border-left:4px solid #3b82f6;color:#1e40af;font-size:0.9rem;margin:8px 0 16px 0;">
                    <div style="display:flex;align-items:center;gap:10px;font-weight:700;margin-bottom:6px;">
                        {icon("folder", 18, "#3b82f6")}
                        <span>Master berhasil dibaca</span>
                    </div>
                    <ul style="margin:6px 0 0 20px;padding:0;">
                        <li><b>{len(df_data)}</b> baris data</li>
                        <li><b>{df_data["Part Number"].nunique()}</b> Part unik</li>
                        <li><b>{len(bulan_sorted_master)}</b> kolom bulan: {', '.join(bulan_sorted_master)}</li>
                    </ul>
                </div>
                ''', unsafe_allow_html=True)

                with st.spinner("Membaca file PDS & Delivery..."):
                    pds_map, delivery_map, sap_map, pds_info = baca_file_pds_delivery(file_pds)

                total_pds = sum(len(v) for v in pds_map.values())
                total_del = sum(len(v) for v in delivery_map.values())

                st.markdown(f'''
                <div style="padding:14px 18px;border-radius:12px;background:#f0fdf4;border-left:4px solid #22c55e;color:#15803d;font-size:0.9rem;margin:8px 0 16px 0;">
                    <div style="display:flex;align-items:center;gap:10px;font-weight:700;margin-bottom:6px;">
                        {icon("check-circle", 18, "#22c55e")}
                        <span>File PDS &amp; Delivery berhasil dibaca</span>
                    </div>
                    <ul style="margin:6px 0 0 20px;padding:0;">
                        <li>{pds_info['rows']} baris diproses, {pds_info['valid']} valid</li>
                        <li>{total_pds} nilai PDS · {total_del} nilai Delivery</li>
                        <li>{len(sap_map)} SAP Code · {len(set(list(pds_map.keys()) + list(delivery_map.keys())))} Part Number</li>
                    </ul>
                </div>
                ''', unsafe_allow_html=True)

                with st.spinner("Menghitung rumus..."):
                    semua_bulan_m2 = set(bulan_sorted_master)
                    df_final, bulan_final = proses_update(
                        None, df_data, semua_bulan_m2,
                        pds_map, delivery_map, sap_map
                    )
                    excel_bytes = buat_excel(df_final, bulan_final)

                tampilkan_bulan_badges(bulan_final)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f'''
                    <div class="stat-card">
                        <div class="icon-wrap">{icon("folder", 22, "#2E7D32")}</div>
                        <div><div class="stat-label">Baris Master</div><div class="stat-value">{len(df_data):,}</div></div>
                    </div>''', unsafe_allow_html=True)
                with col2:
                    st.markdown(f'''
                    <div class="stat-card">
                        <div class="icon-wrap">{icon("package", 22, "#2E7D32")}</div>
                        <div><div class="stat-label">Part Unik</div><div class="stat-value">{df_data["Part Number"].nunique():,}</div></div>
                    </div>''', unsafe_allow_html=True)
                with col3:
                    st.markdown(f'''
                    <div class="stat-card">
                        <div class="icon-wrap">{icon("clipboard-list", 22, "#2E7D32")}</div>
                        <div><div class="stat-label">Nilai PDS</div><div class="stat-value">{total_pds:,}</div></div>
                    </div>''', unsafe_allow_html=True)
                with col4:
                    st.markdown(f'''
                    <div class="stat-card">
                        <div class="icon-wrap">{icon("zap", 22, "#2E7D32")}</div>
                        <div><div class="stat-label">Nilai Delivery</div><div class="stat-value">{total_del:,}</div></div>
                    </div>''', unsafe_allow_html=True)

                st.markdown(f'<div class="section-title">{icon("eye", 20, "#FF9800")} Preview Hasil</div>', unsafe_allow_html=True)
                st.dataframe(df_final.head(20), use_container_width=True)

                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                st.download_button(
                    label=f"Download Master + PDS/Delivery ({len(df_final)} baris) (.xlsx)",
                    data=excel_bytes,
                    file_name=f"Master_Mitsuba_PDS_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                    key="mitsuba_download_m2"
                )

                with st.expander("Lihat Master Final"):
                    st.dataframe(df_final, use_container_width=True)

            except Exception as e:
                st.error(f"Error: {e}")
                st.exception(e)

        elif file_master is not None:
            st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Upload juga file <b>PDS &amp; Delivery</b> untuk melanjutkan.</div>', unsafe_allow_html=True)
        elif file_pds is not None:
            st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Upload juga file <b>master Mitsuba</b> untuk melanjutkan.</div>', unsafe_allow_html=True)

    st.stop()


# ═══════════════════════════════════════════════════════════════
#  GRUP TOKAI RIKA (logika yang sudah ada)
# ═══════════════════════════════════════════════════════════════
if mode == "Buat Master Baru":
    st.markdown(f'''
    <div class="section-title">{icon("file-plus", 22, "#4CAF50")} Buat Master Baru</div>
    <div class="info-box">{icon("info", 18, "#3b82f6")} Upload <b>satu atau lebih</b> file Excel sumber.</div>
    ''', unsafe_allow_html=True)

    files_baru = st.file_uploader(
        "Upload file Excel sumber (bisa banyak)",
        type=['xlsx', 'xls', 'csv', 'html'],
        key='new_files',
        accept_multiple_files=True,
        help="Klik 'Browse files' → tahan Ctrl/Shift untuk pilih banyak file"
    )

    if files_baru and len(files_baru) > 0:
        ok, duplikat = cek_duplikat_nama_file(files_baru)
        if not ok:
            tampilkan_error_duplikat(duplikat)
            st.stop()

        try:
            with st.spinner(f"Memproses {len(files_baru)} file..."):
                df_new, info_files, semua_bulan, pds_all, delivery_all = ekstrak_dari_banyak_file(files_baru)

            st.markdown(f'<div class="section-title">{icon("files", 20, "#4CAF50")} Ringkasan File</div>', unsafe_allow_html=True)
            tampilkan_info_files(info_files)

            if len(df_new) == 0:
                st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Tidak ada data yang berhasil diekstrak.</div>', unsafe_allow_html=True)
                st.stop()

            bulan_sorted = sorted(semua_bulan, key=sort_bulan_key)
            tampilkan_bulan_badges(bulan_sorted)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("files", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Total File</div><div class="stat-value">{len(files_baru):,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col2:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("table", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Total Baris</div><div class="stat-value">{len(df_new):,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col3:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("package", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Part Unik</div><div class="stat-value">{df_new["Part Number"].nunique():,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col4:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("calendar", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Kolom Bulan</div><div class="stat-value">{len(bulan_sorted):,}</div></div>
                </div>''', unsafe_allow_html=True)

            st.markdown(f'<div class="section-title">{icon("eye", 20, "#4CAF50")} Preview Data Gabungan</div>', unsafe_allow_html=True)
            st.dataframe(df_new.head(20), use_container_width=True)

            with st.spinner("Memproses master..."):
                df_final, bulan_final = proses_update(None, df_new, semua_bulan, pds_all, delivery_all, {})
                excel_bytes = buat_excel(df_final, bulan_final)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label=f"⬇ Download Master Baru ({len(df_final)} baris) (.xlsx)",
                data=excel_bytes,
                file_name=f"Data_Master_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

            with st.expander("Lihat Master Final"):
                st.dataframe(df_final, use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")
            st.exception(e)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [21] MODE 2: UPDATE MASTER                                           ║
# ╚═══════════════════════════════════════════════════════════════════════╝
elif mode == "Update Master":
    st.markdown(f'''
    <div class="section-title">{icon("file-check", 22, "#4CAF50")} Update Master</div>
    <div class="info-box">{icon("info", 18, "#3b82f6")} Upload <b>master lama</b> + <b>data baru</b> + (opsional) <b>file PDS &amp; Delivery</b>.</div>
    ''', unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown(f'''
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            {icon("folder-open", 18, "#4CAF50")}
            <span style="font-weight:600;color:#111827;">1️⃣ File Master (Sudah Ada)</span>
        </div>
        ''', unsafe_allow_html=True)
        file_master = st.file_uploader(
            "Upload file master",
            type=['xlsx', 'xls', 'csv'],
            key='master_file',
            label_visibility="collapsed"
        )

    with col_right:
        st.markdown(f'''
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            {icon("files", 18, "#4CAF50")}
            <span style="font-weight:600;color:#111827;">2️⃣ File Data Baru (bisa banyak)</span>
        </div>
        ''', unsafe_allow_html=True)
        files_baru = st.file_uploader(
            "Upload file data baru",
            type=['xlsx', 'xls', 'csv', 'html'],
            key='update_files',
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

    st.markdown("---")
    st.markdown(f'''
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
        {icon("clipboard-list", 18, "#4CAF50")}
        <span style="font-weight:600;color:#111827;">3️⃣ File PDS &amp; Delivery (Opsional)</span>
    </div>
    <div style="font-size:0.85rem;color:#6b7280;margin-bottom:8px;">
        Format: <b>SAP CODE | ITEM | Jan-26 | Feb-26 | ... | Dec-26</b>
    </div>
    ''', unsafe_allow_html=True)

    col_pds1, col_pds2 = st.columns([3, 1])
    with col_pds1:
        file_pds = st.file_uploader(
            "Upload file PDS & Delivery",
            type=['xlsx', 'xls', 'csv'],
            key='pds_file',
            label_visibility="collapsed"
        )
    with col_pds2:
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("Template Kosong", use_container_width=True, key='btn_template_empty_m2'):
            template_bytes = buat_template_pds_delivery()
            st.download_button(
                label="⬇ Download",
                data=template_bytes,
                file_name="Template_PDS_Delivery.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key='dl_template_empty_m2'
            )

    if file_master is not None and files_baru and len(files_baru) > 0:
        ok, duplikat = cek_duplikat_nama_file(files_baru)
        if not ok:
            tampilkan_error_duplikat(duplikat)
            st.stop()

        try:
            with st.spinner("Membaca master..."):
                try:
                    file_master.seek(0)
                    df_master_lama = pd.read_excel(file_master, header=0, dtype=str)
                except:
                    file_master.seek(0)
                    df_master_lama, _, _ = baca_file_apapun(file_master)

            sudah_ada = cek_file_sudah_di_master(files_baru, df_master_lama)
            if sudah_ada:
                tampilkan_error_file_sudah_ada(sudah_ada)
                st.stop()

            with st.spinner(f"Memproses {len(files_baru)} file data baru..."):
                df_new, info_files, semua_bulan, pds_all, delivery_all = ekstrak_dari_banyak_file(files_baru)

            st.markdown(f'<div class="section-title">{icon("files", 20, "#4CAF50")} Ringkasan File Baru</div>', unsafe_allow_html=True)
            tampilkan_info_files(info_files)

            if len(df_new) == 0:
                st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Tidak ada data baru yang berhasil diekstrak.</div>', unsafe_allow_html=True)
                st.stop()

            # Baca file PDS/Delivery kalau diupload
            pds_file_map = {}
            delivery_file_map = {}
            sap_file_map = {}
            if file_pds is not None:
                with st.spinner("Membaca file PDS & Delivery..."):
                    try:
                        pds_file_map, delivery_file_map, sap_file_map, pds_info = baca_file_pds_delivery(file_pds)
                        total_pds = sum(len(v) for v in pds_file_map.values())
                        total_del = sum(len(v) for v in delivery_file_map.values())
                        st.markdown(f'''
                        <div style="padding:14px 18px;border-radius:12px;background:#f0fdf4;border-left:4px solid #22c55e;color:#15803d;font-size:0.9rem;margin:8px 0 16px 0;">
                            <div style="display:flex;align-items:center;gap:10px;font-weight:700;margin-bottom:6px;">
                                {icon("check-circle", 18, "#22c55e")}
                                <span>File PDS &amp; Delivery berhasil dibaca</span>
                            </div>
                            <ul style="margin:6px 0 0 20px;padding:0;">
                                <li>{pds_info['rows']} baris diproses, {pds_info['valid']} valid</li>
                                <li>{total_pds} nilai PDS · {total_del} nilai Delivery</li>
                                <li>{len(sap_file_map)} SAP Code</li>
                            </ul>
                        </div>
                        ''', unsafe_allow_html=True)
                    except Exception as e:
                        st.warning(f"Gagal baca file PDS/Delivery: {e}")

            # Gabung peta PDS/Delivery
            pds_gabung = {}
            for pn, v in pds_all.items():
                pds_gabung.setdefault(pn, {}).update(v)
            for pn, v in pds_file_map.items():
                pds_gabung.setdefault(pn, {}).update(v)

            delivery_gabung = {}
            for pn, v in delivery_all.items():
                delivery_gabung.setdefault(pn, {}).update(v)
            for pn, v in delivery_file_map.items():
                delivery_gabung.setdefault(pn, {}).update(v)

            sap_gabung = {}
            sap_gabung.update(sap_file_map)

            with st.spinner("Menggabungkan & sorting..."):
                df_final, bulan_final = proses_update(
                    df_master_lama, df_new, semua_bulan,
                    pds_gabung, delivery_gabung, sap_gabung
                )
                excel_bytes = buat_excel(df_final, bulan_final)

            tampilkan_bulan_badges(bulan_final)

            col1, col2, col3, col4, col5 = st.columns(5)
            for col, (label, value, ic) in zip(
                [col1, col2, col3, col4, col5],
                [("Master Lama", len(df_master_lama), "folder"),
                 ("File Baru", len(files_baru), "files"),
                 ("Data Baru", len(df_new), "file-plus"),
                 ("Master Final", len(df_final), "layers"),
                 ("Kolom Bulan", len(bulan_final), "calendar")]
            ):
                with col:
                    st.markdown(f'''
                    <div class="stat-card">
                        <div class="icon-wrap">{icon(ic, 22, "#2E7D32")}</div>
                        <div><div class="stat-label">{label}</div><div class="stat-value">{value:,}</div></div>
                    </div>''', unsafe_allow_html=True)

            st.markdown(f'<div class="section-title">{icon("eye", 20, "#4CAF50")} Preview Data Baru</div>', unsafe_allow_html=True)
            st.dataframe(df_new.head(10), use_container_width=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label=f"⬇ Download Master Updated ({len(df_final)} baris) (.xlsx)",
                data=excel_bytes,
                file_name=f"Data_Master_Updated_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

            # Tombol generate template PDS/Delivery
            parts_unik_list = []
            for pn, group in df_new.groupby('Part Number', sort=False):
                pname = group.iloc[0].get('Part Name', '') if len(group) > 0 else ''
                parts_unik_list.append((pn, pname))

            with st.expander("Buat Template PDS/Delivery (sesuai data)"):
                if st.button("Generate Template", key='btn_gen_template_m2'):
                    template_bytes = buat_template_pds_delivery(parts_unik_list, bulan_final)
                    st.download_button(
                        label="⬇ Download Template",
                        data=template_bytes,
                        file_name=f"Template_PDS_Delivery_{timestamp}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key='dl_template_filled_m2'
                    )

            with st.expander("Lihat Master Final"):
                st.dataframe(df_final, use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")
            st.exception(e)

    elif file_master is not None and (not files_baru or len(files_baru) == 0):
        st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Upload juga file <b>data baru</b>.</div>', unsafe_allow_html=True)
    elif file_master is None and files_baru and len(files_baru) > 0:
        st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Upload juga file <b>master lama</b>.</div>', unsafe_allow_html=True)


# ╔═══════════════════════════════════════════════════════════════════════╗
# ║  [22] MODE 3: HITUNG PDS & DELIVERY SAJA                              ║
# ╚═══════════════════════════════════════════════════════════════════════╝
else:  # mode == "Hitung PDS & Delivery"
    st.markdown(f'''
    <div class="section-title">{icon("calculator", 22, "#4CAF50")} Hitung PDS &amp; Delivery</div>
    <div class="info-box">{icon("info", 18, "#3b82f6")} Upload <b>master lama</b> + <b>file PDS &amp; Delivery</b>. Master akan diperkaya dengan PDS/Delivery &amp; semua rumus dihitung ulang.</div>
    ''', unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown(f'''
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            {icon("folder-open", 18, "#4CAF50")}
            <span style="font-weight:600;color:#111827;">1️⃣ File Master (Sudah Ada)</span>
        </div>
        <div style="font-size:0.8rem;color:#6b7280;margin-bottom:6px;">
            Master yang sudah punya data Part &amp; bulan.
        </div>
        ''', unsafe_allow_html=True)
        file_master = st.file_uploader(
            "Upload file master",
            type=['xlsx', 'xls', 'csv'],
            key='master_file_m3',
            label_visibility="collapsed"
        )

    with col_right:
        st.markdown(f'''
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            {icon("clipboard-list", 18, "#4CAF50")}
            <span style="font-weight:600;color:#111827;">2️⃣ File PDS &amp; Delivery</span>
        </div>
        <div style="font-size:0.8rem;color:#6b7280;margin-bottom:6px;">
            Format: SAP CODE | ITEM | Jan-26 | Feb-26 | ... | Dec-26
        </div>
        ''', unsafe_allow_html=True)
        file_pds = st.file_uploader(
            "Upload file PDS & Delivery",
            type=['xlsx', 'xls', 'csv'],
            key='pds_file_m3',
            label_visibility="collapsed"
        )

    st.markdown("---")

    # Tombol template kosong
    col_t1, col_t2 = st.columns([1, 3])
    with col_t1:
        if st.button("Template PDS/Delivery", use_container_width=True, key='btn_template_empty_m3'):
            template_bytes = buat_template_pds_delivery()
            st.download_button(
                label="⬇ Download Template Kosong",
                data=template_bytes,
                file_name="Template_PDS_Delivery.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key='dl_template_empty_m3'
            )

    if file_master is not None and file_pds is not None:
        try:
            # 1. Baca master
            with st.spinner("Membaca master..."):
                try:
                    file_master.seek(0)
                    df_master_lama = pd.read_excel(file_master, header=0, dtype=str)
                except:
                    file_master.seek(0)
                    df_master_lama, _, _ = baca_file_apapun(file_master)

            # 2. Ekstrak data dari master
            with st.spinner("Mengekstrak data dari master..."):
                df_data, bulan_sorted_master = ekstrak_dari_master(df_master_lama)

            if len(df_data) == 0:
                st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Tidak ada data di master.</div>', unsafe_allow_html=True)
                st.stop()

            # Info master
            st.markdown(f'''
            <div style="padding:14px 18px;border-radius:12px;background:#eff6ff;border-left:4px solid #3b82f6;color:#1e40af;font-size:0.9rem;margin:8px 0 16px 0;">
                <div style="display:flex;align-items:center;gap:10px;font-weight:700;margin-bottom:6px;">
                    {icon("folder", 18, "#3b82f6")}
                    <span>Master berhasil dibaca</span>
                </div>
                <ul style="margin:6px 0 0 20px;padding:0;">
                    <li><b>{len(df_data)}</b> baris data</li>
                    <li><b>{df_data["Part Number"].nunique()}</b> Part unik</li>
                    <li><b>{len(bulan_sorted_master)}</b> kolom bulan: {', '.join(bulan_sorted_master)}</li>
                </ul>
            </div>
            ''', unsafe_allow_html=True)

            # 3. Baca file PDS & Delivery
            with st.spinner("Membaca file PDS & Delivery..."):
                pds_map, delivery_map, sap_map, pds_info = baca_file_pds_delivery(file_pds)

            total_pds = sum(len(v) for v in pds_map.values())
            total_del = sum(len(v) for v in delivery_map.values())

            st.markdown(f'''
            <div style="padding:14px 18px;border-radius:12px;background:#f0fdf4;border-left:4px solid #22c55e;color:#15803d;font-size:0.9rem;margin:8px 0 16px 0;">
                <div style="display:flex;align-items:center;gap:10px;font-weight:700;margin-bottom:6px;">
                    {icon("check-circle", 18, "#22c55e")}
                    <span>File PDS &amp; Delivery berhasil dibaca</span>
                </div>
                <ul style="margin:6px 0 0 20px;padding:0;">
                    <li>{pds_info['rows']} baris diproses, {pds_info['valid']} valid</li>
                    <li>{total_pds} nilai PDS · {total_del} nilai Delivery</li>
                    <li>{len(sap_map)} SAP Code · {len(set(list(pds_map.keys()) + list(delivery_map.keys())))} Part Number</li>
                </ul>
            </div>
            ''', unsafe_allow_html=True)

            # 4. Proses ulang
            with st.spinner("Menghitung rumus..."):
                semua_bulan_m3 = set(bulan_sorted_master)
                df_final, bulan_final = proses_update(
                    None, df_data, semua_bulan_m3,
                    pds_map, delivery_map, sap_map
                )
                excel_bytes = buat_excel(df_final, bulan_final)

            tampilkan_bulan_badges(bulan_final)

            # Stat cards
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("folder", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Baris Master</div><div class="stat-value">{len(df_data):,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col2:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("package", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Part Unik</div><div class="stat-value">{df_data["Part Number"].nunique():,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col3:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("clipboard-list", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Nilai PDS</div><div class="stat-value">{total_pds:,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col4:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("zap", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Nilai Delivery</div><div class="stat-value">{total_del:,}</div></div>
                </div>''', unsafe_allow_html=True)

            st.markdown(f'<div class="section-title">{icon("eye", 20, "#4CAF50")} Preview Hasil</div>', unsafe_allow_html=True)
            st.dataframe(df_final.head(20), use_container_width=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label=f"⬇ Download Master + PDS/Delivery ({len(df_final)} baris) (.xlsx)",
                data=excel_bytes,
                file_name=f"Data_Master_PDS_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

            with st.expander("Lihat Master Final"):
                st.dataframe(df_final, use_container_width=True)

            # Error dari PDS/Delivery
            if pds_info['errors']:
                with st.expander(f"⚠️ {len(pds_info['errors'])} baris bermasalah di file PDS"):
                    for err in pds_info['errors']:
                        st.write(err)

        except Exception as e:
            st.error(f"Error: {e}")
            st.exception(e)

    elif file_master is not None:
        st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Upload juga file <b>PDS &amp; Delivery</b> untuk melanjutkan.</div>', unsafe_allow_html=True)
    elif file_pds is not None:
        st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Upload juga file <b>master lama</b> untuk melanjutkan.</div>', unsafe_allow_html=True)