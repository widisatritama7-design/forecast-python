# core.py — Fungsi inti (dipakai Tokai Rika & Mitsuba)
import pandas as pd
import streamlit as st
from io import BytesIO
from collections import Counter

from config import (
    LABELS_RINGKASAN, LABELS_FORMULA,
    LABEL_PDS, LABEL_DELIVERY,
    LABEL_FC_LATES, LABEL_FC_ACT, LABEL_ACT_DEL,
    COL_FILE_FROM, COL_TOTAL, COL_SAP,
    PART_COL, PART_NAME_COL, ORDER_DATE_COL,
)
from helpers import (
    to_number, to_date_str,
    normalisasi_bulan,
    sort_bulan_key, bulan_prev,
    date_to_month_key,
    deteksi_baris_header_bulan,
)
from icons import icon


# ═══════════════════════════════════════════════════════════════════
#  VALIDASI FILE
# ═══════════════════════════════════════════════════════════════════
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
    existing = set(df_master[COL_FILE_FROM].dropna().astype(str).str.strip().unique())
    existing.discard('')
    existing.discard('nan')
    existing.discard('None')
    nama_baru = [f.name for f in files]
    return [nama for nama in nama_baru if nama in existing]


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


# ═══════════════════════════════════════════════════════════════════
#  BACA FILE (MULTI-FORMAT)
# ═══════════════════════════════════════════════════════════════════
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
        except:
            pass

        file_obj.seek(0)
        try:
            df_raw = pd.read_csv(file_obj, header=None, dtype=str)
            header_row, kolom_bulan_map = deteksi_baris_header_bulan(df_raw)
            if header_row is not None and kolom_bulan_map:
                df_data = df_raw.iloc[header_row + 1:].reset_index(drop=True)
                return df_data, kolom_bulan_map, "CSV"
        except:
            pass

        raise ValueError(f"Tidak bisa membaca file: {e1}")


# ═══════════════════════════════════════════════════════════════════
#  EKSTRAKSI DATA (1 FILE)
# ═══════════════════════════════════════════════════════════════════
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
        if pd.isna(part_name):
            part_name = ''

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


# ═══════════════════════════════════════════════════════════════════
#  EKSTRAKSI DARI BANYAK FILE
# ═══════════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════════
#  BACA FILE PDS & DELIVERY
# ═══════════════════════════════════════════════════════════════════
def baca_file_pds_delivery(file_obj):
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


# ═══════════════════════════════════════════════════════════════════
#  TEMPLATE PDS & DELIVERY
# ═══════════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════════
#  EKSTRAK DATA DARI MASTER (untuk MODE 3)
# ═══════════════════════════════════════════════════════════════════
def ekstrak_dari_master(df_master):
    if df_master is None or len(df_master) == 0:
        return pd.DataFrame(), []

    bulan_cols = []
    for c in df_master.columns:
        b = normalisasi_bulan(c)
        if b:
            bulan_cols.append(b)
    bulan_sorted = sorted(bulan_cols, key=sort_bulan_key)

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


# ═══════════════════════════════════════════════════════════════════
#  HITUNG RINGKASAN GRUP
# ═══════════════════════════════════════════════════════════════════
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

    baris_terakhir_per_bulan = {}
    for bln, sub in group.groupby('_bulan_date', sort=False):
        if bln is None:
            continue
        baris_terakhir_per_bulan[bln] = sub.iloc[-1]

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

        row_ini = baris_valid_per_bulan.get(b)
        qty_ini = None
        if row_ini is not None and b in row_ini.index:
            qty_ini = _ambil_angka(row_ini[b])

        row_lalu = baris_terakhir_per_bulan.get(b_prev)
        qty_lalu = None
        if row_lalu is not None and b in row_lalu.index:
            qty_lalu = _ambil_angka(row_lalu[b])

        if qty_ini is None or qty_lalu is None or qty_lalu == 0:
            hasil[LABEL_FC_LATES][b] = None
        else:
            hasil[LABEL_FC_LATES][b] = 1 - (qty_ini / qty_lalu)

        pds_b = pds.get(b) if pds else None
        if qty_ini is None or pds_b is None or pds_b == 0:
            hasil[LABEL_FC_ACT][b] = None
        else:
            hasil[LABEL_FC_ACT][b] = 1 - (qty_ini / pds_b)

        del_b = delivery.get(b) if delivery else None
        if pds_b is None or del_b is None or del_b == 0:
            hasil[LABEL_ACT_DEL][b] = None
        else:
            hasil[LABEL_ACT_DEL][b] = 1 - (pds_b / del_b)

    return hasil


# ═══════════════════════════════════════════════════════════════════
#  PROSES UPDATE / GABUNG MASTER
# ═══════════════════════════════════════════════════════════════════
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
        df[COL_SAP] = df['Part Number'].apply(lambda pn: sap_map.get(str(pn).strip(), ''))
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


# ═══════════════════════════════════════════════════════════════════
#  TAMBAH BARIS RINGKASAN
# ═══════════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════════
#  EXPORT KE EXCEL
# ═══════════════════════════════════════════════════════════════════
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
            'bg_color': '#C8E6C9', 'font_color': '#1B5E20',
            'bold': True, 'num_format': '0.00%',
            'border': 1, 'align': 'right',
        })
        cond_merah = workbook.add_format({
            'bg_color': '#FFCDD2', 'font_color': '#B71C1C',
            'bold': True, 'num_format': '0.00%',
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

        idx_no = col_names.index('No')
        idx_sap = col_names.index(COL_SAP)
        merge_first = idx_no
        merge_last = idx_sap

        for row_idx in range(len(df)):
            excel_row = row_idx + 1
            label = str(df.iloc[row_idx].get('Part Number', '')).strip()

            if label in LABELS_RINGKASAN:
                worksheet.merge_range(
                    excel_row, merge_first, excel_row, merge_last,
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
                                try:
                                    num = float(val)
                                except:
                                    num = None
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
                            try:
                                num_val = float(val)
                            except:
                                num_val = None
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


# ═══════════════════════════════════════════════════════════════════
#  UI: TAMPILKAN INFO FILE
# ═══════════════════════════════════════════════════════════════════
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