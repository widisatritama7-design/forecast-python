# helpers.py
import pandas as pd
import re
from datetime import datetime

from config import (
    LABELS_RINGKASAN, LABEL_PDS, LABEL_DELIVERY,
    COL_FILE_FROM, COL_TOTAL, COL_SAP,
    BULAN_SCAN_START, BULAN_SCAN_END
)


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


def buat_label_bulan(tahun_mulai, bulan_mulai, jumlah_bulan):
    kolom_bulan = []
    y, m = int(tahun_mulai), int(bulan_mulai)
    for _ in range(int(jumlah_bulan)):
        kolom_bulan.append(f"{y}/{m}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return kolom_bulan