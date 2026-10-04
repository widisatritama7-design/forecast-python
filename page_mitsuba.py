# page_mitsuba.py — Semua mode untuk grup Mitsuba
import streamlit as st
import pandas as pd
import re
from datetime import datetime
from io import BytesIO

from icons import icon
from config import (
    COL_FILE_FROM, COL_SAP, COL_TOTAL,
    LABEL_PDS, LABEL_DELIVERY,
    LABEL_FC_LATES, LABEL_FC_ACT, LABEL_ACT_DEL,
    LABELS_RINGKASAN, LABELS_FORMULA,
)
from helpers import sort_bulan_key, buat_label_bulan, to_number, normalisasi_bulan
from core import (
    proses_update, buat_excel,
    tampilkan_bulan_badges,
)


def render(mode):
    if mode == "Buat Master (Paste)":
        _buat_master_paste()
    elif mode == "Update Master":
        _update_master()
    elif mode == "Input Actual PDS":
        _input_pds()
    else:  # "Input Actual Delivery"
        _input_delivery()


# ═══════════════════════════════════════════════════════════════════
#  HELPER
# ═══════════════════════════════════════════════════════════════════
def _baca_master_excel(file_obj):
    file_obj.seek(0)
    xls = pd.ExcelFile(file_obj)
    sheet_master = None
    for s in xls.sheet_names:
        if 'master' in s.lower():
            sheet_master = s
            break
    if sheet_master is None:
        sheet_master = xls.sheet_names[0]

    df_raw = pd.read_excel(xls, sheet_name=sheet_master, header=None, dtype=str)

    if len(df_raw) == 0:
        return pd.DataFrame()

    header_row = df_raw.iloc[0].tolist()
    header_bersih = []
    for c in header_row:
        c_str = str(c).strip()
        b = normalisasi_bulan(c_str)
        header_bersih.append(b if b else c_str)

    df = df_raw.iloc[1:].reset_index(drop=True)
    df.columns = header_bersih

    for c in df.columns:
        try:
            df[c] = pd.Series(list(df[c]), dtype=object, index=df.index)
        except:
            pass

    if 'No' in df.columns and 'Part Number' in df.columns:
        for i in range(len(df)):
            no_val = str(df.at[df.index[i], 'No']).strip()
            pn_val = str(df.at[df.index[i], 'Part Number']).strip()
            if no_val in LABELS_RINGKASAN and (pn_val == '' or pn_val.lower() in ('nan', 'none')):
                df.at[df.index[i], 'Part Number'] = no_val

    return df


def _deteksi_bulan_master(df_master):
    bulan_cols = []
    for c in df_master.columns:
        b = normalisasi_bulan(c)
        if b:
            bulan_cols.append(b)
    return sorted(bulan_cols, key=sort_bulan_key)


def _parse_qty(v):
    if v is None:
        return None
    s = str(v).strip()
    if s == '' or s.lower() in ('nan', 'none', '-'):
        return None
    s = s.replace(',', '')
    if s.count('.') > 1:
        s = s.replace('.', '')
    elif s.count('.') == 1:
        parts = s.split('.')
        if len(parts[1]) == 3:
            s = s.replace('.', '')
    try:
        return float(s)
    except:
        return None


def _normalize_label(s):
    if s is None:
        return ''
    s = str(s)
    s = s.replace('\xa0', ' ').replace('\u200b', '').replace('\t', ' ')
    s = re.sub(r'\s+', ' ', s).strip()
    return s.lower()


def _is_ringkasan(pn):
    return _normalize_label(pn) in [_normalize_label(l) for l in LABELS_RINGKASAN]


def _is_pds(pn):
    return _normalize_label(pn) == _normalize_label(LABEL_PDS)


def _is_delivery(pn):
    return _normalize_label(pn) == _normalize_label(LABEL_DELIVERY)


def _is_formula(pn):
    n = _normalize_label(pn)
    return n in [_normalize_label(l) for l in LABELS_FORMULA]


def _konversi_kolom_object(df):
    for c in df.columns:
        dtype_str = str(df[c].dtype).lower()
        if 'string' in dtype_str or 'arrow' in dtype_str:
            try:
                df[c] = df[c].astype(object)
            except Exception:
                df[c] = pd.Series([v for v in df[c]], dtype=object, index=df.index)
    return df


# ═══════════════════════════════════════════════════════════════════
#  EDITOR HELPER — bikin data_editor yang tidak reset saat paste
# ═══════════════════════════════════════════════════════════════════
def _buat_editor(kolom_list, n_rows, editor_key, editor_key_data, editor_key_nrows, column_config=None):
    """
    Bikin st.data_editor dengan fix bug sync delay.
    """
    sig = f"{int(n_rows)}|{'|'.join(map(str, kolom_list))}"
    sig_key = editor_key_nrows + "_sig"

    if editor_key_data not in st.session_state or st.session_state.get(sig_key) != sig:
        st.session_state[editor_key_data] = pd.DataFrame({
            c: [""] * int(n_rows) for c in kolom_list
        })
        st.session_state[editor_key_nrows] = int(n_rows)
        st.session_state[sig_key] = sig

    if column_config is None:
        column_config = {}

    # Simpan data SEBELUM editor
    df_before = st.session_state[editor_key_data].copy()

    df_result = st.data_editor(
        st.session_state[editor_key_data],
        num_rows="dynamic",
        use_container_width=True,
        key=editor_key,
        column_config=column_config
    )

    # Cek apakah ada perubahan (bandingkan nilai)
    ada_perubahan = False
    try:
        if df_before.shape != df_result.shape:
            ada_perubahan = True
        else:
            # Bandingkan nilai
            diff = (df_before.fillna("").astype(str) != df_result.fillna("").astype(str))
            if diff.any().any():
                ada_perubahan = True
    except:
        ada_perubahan = True

    # Simpan hasil ke session
    st.session_state[editor_key_data] = df_result

    # Kalau ada perubahan, paksa rerun SEKALI untuk sync
    rerun_key = editor_key + "_last_rerun"
    if ada_perubahan:
        # Cegah infinite loop: cek apakah data sudah sama dengan yang di session
        current_str = df_result.fillna("").astype(str).to_json()
        last_str = st.session_state.get(rerun_key, "")
        if current_str != last_str:
            st.session_state[rerun_key] = current_str
            st.rerun()

    return df_result


# ═══════════════════════════════════════════════════════════════════
#  UPDATE PDS
# ═══════════════════════════════════════════════════════════════════
def _update_pds_ke_master(df_master, pds_map, bulan_key):
    df = df_master.copy()
    df.columns = [str(c).strip() for c in df.columns]

    for c in df.columns:
        try:
            df[c] = pd.Series(list(df[c]), dtype=object, index=df.index)
        except:
            pass

    if bulan_key not in df.columns:
        if COL_TOTAL in df.columns:
            idx_total = df.columns.get_loc(COL_TOTAL)
            df.insert(idx_total, bulan_key, '')
        else:
            df[bulan_key] = ''

    if bulan_key in df.columns:
        df[bulan_key] = df[bulan_key].astype(object)

    mask_pds = df['Part Number'].apply(_is_pds)
    jumlah_baris_pds = int(mask_pds.sum())

    if jumlah_baris_pds == 0:
        return df

    if jumlah_baris_pds == 1:
        total_pds = sum(pds_map.values())
        idx_pds = df.index[mask_pds][0]
        df.at[idx_pds, bulan_key] = total_pds
    else:
        part_no_aktif = None
        for i in range(len(df)):
            pn = str(df.iloc[i]['Part Number']).strip()

            if _is_pds(pn):
                if part_no_aktif and part_no_aktif in pds_map:
                    df.at[df.index[i], bulan_key] = pds_map[part_no_aktif]
                continue

            if _is_ringkasan(pn):
                continue

            if pn and pn.lower() not in ('nan', 'none', ''):
                part_no_aktif = pn

    return df


# ═══════════════════════════════════════════════════════════════════
#  UPDATE DELIVERY
# ═══════════════════════════════════════════════════════════════════
def _update_delivery_ke_master(df_master, delivery_map, sap_map, bulan_list):
    df = df_master.copy()
    df.columns = [str(c).strip() for c in df.columns]

    for c in df.columns:
        try:
            df[c] = pd.Series(list(df[c]), dtype=object, index=df.index)
        except:
            pass

    for b in bulan_list:
        if b not in df.columns:
            if COL_TOTAL in df.columns:
                idx_total = df.columns.get_loc(COL_TOTAL)
                df.insert(idx_total, b, '')
            else:
                df[b] = ''
        df[b] = df[b].astype(object)

    mask_del = df['Part Number'].apply(_is_delivery)
    jumlah_baris_del = int(mask_del.sum())

    if jumlah_baris_del == 0:
        return df

    if jumlah_baris_del == 1:
        idx_del = df.index[mask_del][0]
        for b in bulan_list:
            total = sum(delivery_map.get(pn, {}).get(b, 0) for pn in delivery_map)
            if total > 0:
                df.at[idx_del, b] = total
    else:
        part_no_aktif = None
        for i in range(len(df)):
            pn = str(df.iloc[i]['Part Number']).strip()

            if _is_delivery(pn):
                if part_no_aktif and part_no_aktif in delivery_map:
                    for b, qty in delivery_map[part_no_aktif].items():
                        if b in df.columns:
                            df.at[df.index[i], b] = qty
                continue

            if _is_ringkasan(pn):
                continue

            if pn and pn.lower() not in ('nan', 'none', ''):
                part_no_aktif = pn
                if pn in sap_map and COL_SAP in df.columns:
                    df.at[df.index[i], COL_SAP] = sap_map[pn]

    return df


# ═══════════════════════════════════════════════════════════════════
#  HITUNG ULANG FORMULA
# ═══════════════════════════════════════════════════════════════════
def _hitung_ulang_formula(df_master, bulan_sorted):
    df = df_master.copy()
    df.columns = [str(c).strip() for c in df.columns]

    for c in df.columns:
        try:
            df[c] = pd.Series(list(df[c]), dtype=object, index=df.index)
        except:
            pass

    mask_pds = df['Part Number'].apply(_is_pds)
    mask_del = df['Part Number'].apply(_is_delivery)
    mask_lates = df['Part Number'].apply(lambda x: _normalize_label(x) == _normalize_label(LABEL_FC_LATES))
    mask_act = df['Part Number'].apply(lambda x: _normalize_label(x) == _normalize_label(LABEL_FC_ACT))
    mask_actdel = df['Part Number'].apply(lambda x: _normalize_label(x) == _normalize_label(LABEL_ACT_DEL))

    n_pds = int(mask_pds.sum())
    n_del = int(mask_del.sum())

    idx_pds_list = df.index[mask_pds].tolist()
    idx_del_list = df.index[mask_del].tolist()
    idx_lates_list = df.index[mask_lates].tolist()
    idx_act_list = df.index[mask_act].tolist()
    idx_actdel_list = df.index[mask_actdel].tolist()

    if n_pds == 1 and n_del == 1:
        idx_pds = idx_pds_list[0]
        idx_del = idx_del_list[0]
        idx_lates = idx_lates_list[0] if idx_lates_list else None
        idx_act = idx_act_list[0] if idx_act_list else None
        idx_actdel = idx_actdel_list[0] if idx_actdel_list else None

        for b in bulan_sorted:
            if b not in df.columns:
                continue

            pds_b = _parse_qty(df.iloc[idx_pds][b])
            del_b = _parse_qty(df.iloc[idx_del][b])

            fc_b = 0.0
            fc_ada = False
            for i in range(len(df)):
                pn = str(df.iloc[i]['Part Number']).strip()
                if _is_ringkasan(pn):
                    continue
                v = _parse_qty(df.iloc[i][b]) if b in df.columns else None
                if v is not None:
                    fc_b += v
                    fc_ada = True

            if idx_act is not None:
                if not fc_ada or pds_b is None or pds_b == 0:
                    df.at[df.index[idx_act], b] = '-'
                else:
                    df.at[df.index[idx_act], b] = 1 - (fc_b / pds_b)

            if idx_actdel is not None:
                if pds_b is None or del_b is None or del_b == 0:
                    df.at[df.index[idx_actdel], b] = '-'
                else:
                    df.at[df.index[idx_actdel], b] = 1 - (pds_b / del_b)

            if idx_lates is not None:
                y, m = b.split('/')
                y, m = int(y), int(m)
                b_prev = f"{y-1}/12" if m == 1 else f"{y}/{m-1}"

                fc_prev = 0.0
                ada_prev = False
                for i in range(len(df)):
                    pn = str(df.iloc[i]['Part Number']).strip()
                    if _is_ringkasan(pn):
                        continue
                    if b_prev in df.columns:
                        v = _parse_qty(df.iloc[i][b_prev])
                        if v is not None:
                            fc_prev += v
                            ada_prev = True

                if not fc_ada or not ada_prev or fc_prev == 0:
                    df.at[df.index[idx_lates], b] = '-'
                else:
                    df.at[df.index[idx_lates], b] = 1 - (fc_b / fc_prev)

    else:
        part_order = []
        part_rows = {}
        pds_rows = {}
        del_rows = {}
        formula_rows = {}

        part_no_aktif = None
        for i in range(len(df)):
            pn = str(df.iloc[i]['Part Number']).strip()

            if _is_pds(pn):
                if part_no_aktif:
                    pds_rows[part_no_aktif] = i
                continue
            if _is_delivery(pn):
                if part_no_aktif:
                    del_rows[part_no_aktif] = i
                continue
            if _is_formula(pn):
                if part_no_aktif:
                    formula_rows.setdefault(part_no_aktif, {})[pn] = i
                continue
            if _is_ringkasan(pn):
                continue

            if pn and pn.lower() not in ('nan', 'none', ''):
                if pn not in part_order:
                    part_order.append(pn)
                    part_rows[pn] = []
                part_rows[pn].append(i)
                part_no_aktif = pn

        for pn in part_order:
            baris_f = formula_rows.get(pn, {})
            idx_pds = pds_rows.get(pn)
            idx_del = del_rows.get(pn)
            data_rows = part_rows.get(pn, [])

            baris_terakhir_per_bulan = {}
            baris_valid_per_bulan = {}
            for ri in data_rows:
                date_val = str(df.iloc[ri].get('Date', '')).strip()
                if not date_val:
                    continue
                try:
                    dt = pd.to_datetime(date_val)
                    bln = f"{dt.year}/{dt.month}"
                except:
                    continue
                baris_terakhir_per_bulan[bln] = ri
                v = _parse_qty(df.iloc[ri][bln]) if bln in df.columns else None
                if v is not None and v != 0:
                    baris_valid_per_bulan[bln] = ri

            for b in bulan_sorted:
                if b not in df.columns:
                    continue

                qty_ini = None
                if b in baris_valid_per_bulan:
                    ri = baris_valid_per_bulan[b]
                    try:
                        qty_ini = _parse_qty(df.at[df.index[ri], b])
                    except:
                        qty_ini = None

                y, m = b.split('/')
                y, m = int(y), int(m)
                b_prev = f"{y-1}/12" if m == 1 else f"{y}/{m-1}"
                qty_lalu = None
                if b_prev in baris_terakhir_per_bulan:
                    ri = baris_terakhir_per_bulan[b_prev]
                    if b in df.columns:
                        try:
                            qty_lalu = _parse_qty(df.at[df.index[ri], b])
                        except:
                            qty_lalu = None

                pds_b = None
                if idx_pds is not None and b in df.columns:
                    try:
                        pds_b = _parse_qty(df.at[df.index[idx_pds], b])
                    except:
                        pds_b = None

                del_b = None
                if idx_del is not None and b in df.columns:
                    try:
                        del_b = _parse_qty(df.at[df.index[idx_del], b])
                    except:
                        del_b = None

                for label in LABELS_FORMULA:
                    ri = None
                    for k, v in baris_f.items():
                        if _normalize_label(k) == _normalize_label(label):
                            ri = v
                            break
                    if ri is None:
                        continue

                    if label == LABEL_FC_LATES:
                        if qty_ini is None or qty_lalu is None or qty_lalu == 0:
                            df.at[df.index[ri], b] = '-'
                        else:
                            df.at[df.index[ri], b] = 1 - (qty_ini / qty_lalu)
                    elif label == LABEL_FC_ACT:
                        if qty_ini is None or pds_b is None or pds_b == 0:
                            df.at[df.index[ri], b] = '-'
                        else:
                            df.at[df.index[ri], b] = 1 - (qty_ini / pds_b)
                    elif label == LABEL_ACT_DEL:
                        if pds_b is None or del_b is None or del_b == 0:
                            df.at[df.index[ri], b] = '-'
                        else:
                            df.at[df.index[ri], b] = 1 - (pds_b / del_b)

    return df


def _hitung_total_baris_ringkasan(df_master):
    df = df_master.copy()
    df.columns = [str(c).strip() for c in df.columns]

    for c in df.columns:
        try:
            df[c] = pd.Series(list(df[c]), dtype=object, index=df.index)
        except:
            pass

    if COL_TOTAL not in df.columns:
        return df

    bulan_cols = [c for c in df.columns if normalisasi_bulan(c)]

    for i in range(len(df)):
        pn = str(df.iloc[i]['Part Number']).strip()
        if not _is_ringkasan(pn):
            continue

        total = 0.0
        ada = False
        for b in bulan_cols:
            v = _parse_qty(df.iloc[i][b])
            if v is not None:
                total += v
                ada = True
        df.at[df.index[i], COL_TOTAL] = total if ada else ''

    return df


# ═══════════════════════════════════════════════════════════════════
#  MODE 1: BUAT MASTER (PASTE)
# ═══════════════════════════════════════════════════════════════════
def _buat_master_paste():
    st.markdown(f'''
    <div class="section-title">{icon("package", 22, "#FF9800")} Buat Master dari Paste</div>
    <div class="info-box">{icon("info", 18, "#3b82f6")} Copy data dari Excel → paste ke tabel (klik sel pertama → Ctrl+V).</div>
    ''', unsafe_allow_html=True)

    st.markdown(f'<div class="section-title">{icon("calendar", 18, "#FF9800")} Pengaturan Kolom Bulan</div>', unsafe_allow_html=True)

    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        tahun_mulai = st.number_input("Tahun mulai", 2000, 2100, 2026, 1, key="mitsuba_tahun")
    with col_t2:
        bulan_mulai = st.number_input("Bulan mulai", 1, 12, 1, 1, key="mitsuba_bulan")
    with col_t3:
        jumlah_bulan = st.number_input("Jumlah bulan", 1, 60, 12, 1, key="mitsuba_jml")

    kolom_bulan = buat_label_bulan(tahun_mulai, bulan_mulai, jumlah_bulan)

    badges = "".join([
        f'<span style="display:inline-flex;align-items:center;gap:6px;padding:5px 10px;background:#fff7ed;color:#9a3412;border-radius:16px;font-size:0.78rem;font-weight:600;border:1px solid #fed7aa;margin:3px;">{b}</span>'
        for b in kolom_bulan
    ])
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin:8px 0 16px 0;">{badges}</div>', unsafe_allow_html=True)

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
        st.caption("Klik sel pertama → Ctrl+V untuk paste dari Excel.")

    df_paste = _buat_editor(
        kolom_list=semua_kolom,
        n_rows=n_rows,
        editor_key="mitsuba_editor",
        editor_key_data="mitsuba_editor_data",
        editor_key_nrows="mitsuba_editor_nrows",
        column_config={
            "No": st.column_config.TextColumn("No", width="small"),
            "PART NAME": st.column_config.TextColumn("PART NAME", width="medium"),
            "PART NO": st.column_config.TextColumn("PART NO", width="medium"),
        }
    )

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

            with st.spinner("Menyusun master..."):
                semua_bulan = set(kolom_bulan)
                df_final, bulan_final = proses_update(
                    None, df_new, semua_bulan,
                    {}, {}, {}
                )
                excel_bytes = buat_excel(df_final, bulan_final)

            tampilkan_bulan_badges(bulan_final)

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


# ═══════════════════════════════════════════════════════════════════
#  MODE 2: UPDATE MASTER
# ═══════════════════════════════════════════════════════════════════
def _update_master():
    st.markdown(f'''
    <div class="section-title">{icon("file-check", 22, "#FF9800")} Update Master</div>
    <div class="info-box">{icon("info", 18, "#3b82f6")} Upload <b>master terakhir</b> + <b>paste data baru</b> dari Excel.</div>
    ''', unsafe_allow_html=True)

    st.markdown(f'<div class="section-title">{icon("folder-open", 18, "#FF9800")} 1. Upload Master Terakhir</div>', unsafe_allow_html=True)

    file_master = st.file_uploader(
        "Upload file master",
        type=['xlsx', 'xls', 'csv'],
        key='master_file_mitsuba_update',
        label_visibility="collapsed"
    )

    st.markdown(f'<div class="section-title">{icon("calendar", 18, "#FF9800")} 2. Pengaturan Kolom Bulan</div>', unsafe_allow_html=True)

    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        tahun_mulai = st.number_input("Tahun mulai", 2000, 2100, 2026, 1, key="mitsuba_upd_tahun")
    with col_t2:
        bulan_mulai = st.number_input("Bulan mulai", 1, 12, 1, 1, key="mitsuba_upd_bulan")
    with col_t3:
        jumlah_bulan = st.number_input("Jumlah bulan", 1, 60, 12, 1, key="mitsuba_upd_jml")

    kolom_bulan = buat_label_bulan(tahun_mulai, bulan_mulai, jumlah_bulan)

    badges = "".join([
        f'<span style="display:inline-flex;align-items:center;gap:6px;padding:5px 10px;background:#fff7ed;color:#9a3412;border-radius:16px;font-size:0.78rem;font-weight:600;border:1px solid #fed7aa;margin:3px;">{b}</span>'
        for b in kolom_bulan
    ])
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin:8px 0 16px 0;">{badges}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="section-title">{icon("table", 18, "#FF9800")} 3. Paste Data Baru</div>', unsafe_allow_html=True)

    kolom_fix = ["No", "PART NAME", "PART NO"]
    semua_kolom = kolom_fix + kolom_bulan

    col_a, col_b = st.columns([1, 3])
    with col_a:
        n_rows = st.number_input(
            "Jumlah baris awal",
            min_value=1, max_value=1000, value=10, step=1,
            key="mitsuba_upd_n_rows"
        )
    with col_b:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        st.caption("Klik sel pertama → Ctrl+V untuk paste dari Excel.")

    df_paste = _buat_editor(
        kolom_list=semua_kolom,
        n_rows=n_rows,
        editor_key="mitsuba_upd_editor",
        editor_key_data="mitsuba_upd_editor_data",
        editor_key_nrows="mitsuba_upd_editor_nrows",
        column_config={
            "No": st.column_config.TextColumn("No", width="small"),
            "PART NAME": st.column_config.TextColumn("PART NAME", width="medium"),
            "PART NO": st.column_config.TextColumn("PART NO", width="medium"),
        }
    )

    st.markdown(f'<div class="section-title">{icon("calendar", 18, "#FF9800")} 4. Input Tanggal</div>', unsafe_allow_html=True)

    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        tanggal_input = st.date_input(
            "Tanggal Order",
            value=datetime(2026, 1, 1),
            key="mitsuba_upd_tanggal"
        )
    with col_d2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        st.caption("Tanggal ini dipakai untuk semua baris data baru.")

    st.markdown("---")
    proses = st.button("Update Master", type="primary", use_container_width=True, key="mitsuba_update_proses")

    if proses:
        if file_master is None:
            st.warning("Upload file master terlebih dahulu.")
            st.stop()

        df_clean = df_paste.dropna(how="all").reset_index(drop=True)
        mask_kosong = df_clean.apply(
            lambda r: all(str(v).strip() == "" for v in r), axis=1
        )
        df_clean = df_clean[~mask_kosong].reset_index(drop=True)

        if len(df_clean) == 0:
            st.warning("Belum ada data baru yang di-paste.")
            st.stop()

        try:
            with st.spinner("Membaca master lama..."):
                df_master_lama = _baca_master_excel(file_master)

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

            with st.spinner("Menggabungkan master..."):
                semua_bulan = set(kolom_bulan)
                for c in df_master_lama.columns:
                    b = normalisasi_bulan(c)
                    if b:
                        semua_bulan.add(b)

                df_final, bulan_final = proses_update(
                    df_master_lama, df_new, semua_bulan,
                    {}, {}, {}
                )
                excel_bytes = buat_excel(df_final, bulan_final)

            tampilkan_bulan_badges(bulan_final)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label=f"Download Master Updated ({len(df_final)} baris) (.xlsx)",
                data=excel_bytes,
                file_name=f"Master_Mitsuba_Updated_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
                key="mitsuba_update_download"
            )

            with st.expander("Lihat Master Final"):
                st.dataframe(df_final, use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")
            st.exception(e)


# ═══════════════════════════════════════════════════════════════════
#  MODE 3: INPUT ACTUAL PDS
# ═══════════════════════════════════════════════════════════════════
def _input_pds():
    st.markdown(f'''
    <div class="section-title">{icon("clipboard-list", 22, "#FF9800")} Input Actual PDS</div>
    <div class="info-box">{icon("info", 18, "#3b82f6")} Upload <b>master terbaru</b>, pilih <b>bulan PDS</b>, lalu paste tabel <b>ITEM | Qty</b> ke cell.</div>
    ''', unsafe_allow_html=True)

    st.markdown(f'<div class="section-title">{icon("folder-open", 18, "#FF9800")} 1. Upload Master Terbaru</div>', unsafe_allow_html=True)

    file_master = st.file_uploader(
        "Upload file master",
        type=['xlsx', 'xls', 'csv'],
        key='master_file_mitsuba_pds',
        label_visibility="collapsed"
    )

    st.markdown(f'<div class="section-title">{icon("calendar", 18, "#FF9800")} 2. Pilih Bulan PDS</div>', unsafe_allow_html=True)

    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        tahun_pds = st.number_input("Tahun", 2000, 2100, 2026, 1, key="pds_tahun")
    with col_b2:
        bulan_pds = st.number_input("Bulan (1-12)", 1, 12, 1, 1, key="pds_bulan")
    with col_b3:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        st.caption("1 bulan = 1 file Excel")

    bulan_key = f"{int(tahun_pds)}/{int(bulan_pds)}"

    st.markdown(f'<div class="section-title">{icon("table", 18, "#FF9800")} 3. Paste Tabel PDS (ke cell)</div>', unsafe_allow_html=True)
    st.caption("Format: ITEM | Qty")

    col_a, col_b = st.columns([1, 3])
    with col_a:
        n_rows_pds = st.number_input(
            "Jumlah baris awal",
            min_value=1, max_value=1000, value=10, step=1,
            key="pds_n_rows"
        )
    with col_b:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        st.caption("Klik sel pertama → Ctrl+V untuk paste dari Excel.")

    kolom_pds = ["ITEM", "Qty"]

    df_pds_paste = _buat_editor(
        kolom_list=kolom_pds,
        n_rows=n_rows_pds,
        editor_key="pds_editor",
        editor_key_data="pds_editor_data",
        editor_key_nrows="pds_editor_nrows",
        column_config={
            "ITEM": st.column_config.TextColumn("ITEM", width="large"),
            "Qty": st.column_config.TextColumn("Qty", width="medium"),
        }
    )

    st.markdown("---")
    proses = st.button("Proses PDS", type="primary", use_container_width=True, key="btn_proses_pds")

    if proses:
        if file_master is None:
            st.warning("Upload file master terlebih dahulu.")
            st.stop()

        df_clean = df_pds_paste.dropna(how="all").reset_index(drop=True)
        mask_kosong = df_clean.apply(
            lambda r: all(str(v).strip() == "" for v in r), axis=1
        )
        df_clean = df_clean[~mask_kosong].reset_index(drop=True)

        if len(df_clean) == 0:
            st.warning("Belum ada data PDS yang di-paste.")
            st.stop()

        try:
            with st.spinner("Membaca master..."):
                df_master = _baca_master_excel(file_master)

            pds_map = {}
            for _, r in df_clean.iterrows():
                item = str(r.get('ITEM', '')).strip()
                qty_raw = str(r.get('Qty', '')).strip()
                if not item or item.lower() in ('nan', 'none', ''):
                    continue
                qty = _parse_qty(qty_raw)
                if qty is None or qty == 0:
                    continue
                pds_map[item] = qty

            if not pds_map:
                st.warning("Tidak ada baris PDS valid yang bisa diproses.")
                st.stop()

            with st.spinner("Mengupdate master..."):
                df_updated = _update_pds_ke_master(df_master, pds_map, bulan_key)
                bulan_sorted = _deteksi_bulan_master(df_updated)
                excel_bytes = buat_excel(df_updated, bulan_sorted)

            st.success(f"Berhasil mengupdate {len(pds_map)} item PDS untuk bulan {bulan_key}.")

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label=f"Download Master + PDS ({len(df_updated)} baris) (.xlsx)",
                data=excel_bytes,
                file_name=f"Master_Mitsuba_PDS_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
                key="dl_pds"
            )

            with st.expander("Lihat Master Final"):
                st.dataframe(df_updated, use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")
            st.exception(e)


# ═══════════════════════════════════════════════════════════════════
#  MODE 4: INPUT ACTUAL DELIVERY
# ═══════════════════════════════════════════════════════════════════
def _input_delivery():
    st.markdown(f'''
    <div class="section-title">{icon("calculator", 22, "#FF9800")} Input Actual Delivery</div>
    <div class="info-box">{icon("info", 18, "#3b82f6")} Upload <b>master hasil Input PDS</b>, atur <b>bulan Delivery</b>, lalu paste tabel <b>ITEM | SAP CODE | bulan-bulan</b> ke cell.</div>
    ''', unsafe_allow_html=True)

    st.markdown(f'<div class="section-title">{icon("folder-open", 18, "#FF9800")} 1. Upload Master Hasil PDS</div>', unsafe_allow_html=True)

    file_master = st.file_uploader(
        "Upload file master",
        type=['xlsx', 'xls'],
        key='master_file_mitsuba_del',
        label_visibility="collapsed"
    )

    st.markdown(f'<div class="section-title">{icon("calendar", 18, "#FF9800")} 2. Pengaturan Bulan Delivery</div>', unsafe_allow_html=True)

    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        tahun_mulai = st.number_input("Tahun mulai", 2000, 2100, 2026, 1, key="del_tahun")
    with col_t2:
        bulan_mulai = st.number_input("Bulan mulai", 1, 12, 1, 1, key="del_bulan")
    with col_t3:
        jumlah_bulan = st.number_input("Jumlah bulan", 1, 60, 12, 1, key="del_jml")

    kolom_bulan = buat_label_bulan(tahun_mulai, bulan_mulai, jumlah_bulan)

    badges = "".join([
        f'<span style="display:inline-flex;align-items:center;gap:6px;padding:5px 10px;background:#fff7ed;color:#9a3412;border-radius:16px;font-size:0.78rem;font-weight:600;border:1px solid #fed7aa;margin:3px;">{b}</span>'
        for b in kolom_bulan
    ])
    st.markdown(f'<div style="display:flex;flex-wrap:wrap;gap:4px;margin:8px 0 16px 0;">{badges}</div>', unsafe_allow_html=True)

    st.markdown(f'<div class="section-title">{icon("table", 18, "#FF9800")} 3. Paste Tabel Delivery (ke cell)</div>', unsafe_allow_html=True)
    st.caption("Format: ITEM | SAP CODE | bulan-bulan")

    kolom_del = ["ITEM", "SAP CODE"] + kolom_bulan

    col_a, col_b = st.columns([1, 3])
    with col_a:
        n_rows_del = st.number_input(
            "Jumlah baris awal",
            min_value=1, max_value=1000, value=10, step=1,
            key="del_n_rows"
        )
    with col_b:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        st.caption("Klik sel pertama → Ctrl+V untuk paste dari Excel.")

    df_del_paste = _buat_editor(
        kolom_list=kolom_del,
        n_rows=n_rows_del,
        editor_key="del_editor",
        editor_key_data="del_editor_data",
        editor_key_nrows="del_editor_nrows",
        column_config={
            "ITEM": st.column_config.TextColumn("ITEM", width="large"),
            "SAP CODE": st.column_config.TextColumn("SAP CODE", width="medium"),
        }
    )

    st.markdown("---")
    proses = st.button("Proses & Hitung", type="primary", use_container_width=True, key="btn_proses_del")

    if proses:
        if file_master is None:
            st.warning("Upload master hasil PDS terlebih dahulu.")
            st.stop()

        df_clean = df_del_paste.dropna(how="all").reset_index(drop=True)
        mask_kosong = df_clean.apply(
            lambda r: all(str(v).strip() == "" for v in r), axis=1
        )
        df_clean = df_clean[~mask_kosong].reset_index(drop=True)

        if len(df_clean) == 0:
            st.warning("Belum ada data Delivery yang di-paste.")
            st.stop()

        try:
            with st.spinner("Membaca master..."):
                df_master = _baca_master_excel(file_master)

            delivery_map = {}
            sap_map = {}
            for _, r in df_clean.iterrows():
                item = str(r.get('ITEM', '')).strip()
                if not item or item.lower() in ('nan', 'none', ''):
                    continue
                sap = str(r.get('SAP CODE', '')).strip()
                if sap.lower() in ('nan', 'none'):
                    sap = ''
                if sap:
                    sap_map[item] = sap

                bulan_vals = {}
                for b in kolom_bulan:
                    qty = _parse_qty(r.get(b, ''))
                    if qty is not None and qty != 0:
                        bulan_vals[b] = qty
                if bulan_vals:
                    delivery_map[item] = bulan_vals

            if not delivery_map:
                st.warning("Tidak ada nilai Delivery yang valid.")
                st.stop()

            with st.spinner("Mengupdate master..."):
                df_updated = _update_delivery_ke_master(
                    df_master, delivery_map, sap_map, kolom_bulan
                )
                bulan_sorted = _deteksi_bulan_master(df_updated)
                df_updated = _hitung_ulang_formula(df_updated, bulan_sorted)
                df_updated = _hitung_total_baris_ringkasan(df_updated)
                excel_bytes = buat_excel(df_updated, bulan_sorted)

            st.success("Berhasil mengupdate Delivery & menghitung rumus.")

            total_del = sum(len(v) for v in delivery_map.values())

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("folder", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Baris Master</div><div class="stat-value">{len(df_updated):,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col2:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("package", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Part Unik</div><div class="stat-value">{len(delivery_map):,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col3:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("zap", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Nilai Delivery</div><div class="stat-value">{total_del:,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col4:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("calendar", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Kolom Bulan</div><div class="stat-value">{len(bulan_sorted):,}</div></div>
                </div>''', unsafe_allow_html=True)

            st.markdown(f'<div class="section-title">{icon("eye", 20, "#FF9800")} Preview Hasil</div>', unsafe_allow_html=True)
            st.dataframe(df_updated.head(30), use_container_width=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label=f"Download Master Final ({len(df_updated)} baris) (.xlsx)",
                data=excel_bytes,
                file_name=f"Master_Mitsuba_Final_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
                key="dl_delivery_final"
            )

            with st.expander("Lihat Master Final"):
                st.dataframe(df_updated, use_container_width=True)

        except Exception as e:
            st.error(f"Error: {e}")
            st.exception(e)