# page_mitsuba.py — Semua mode untuk grup Mitsuba
import streamlit as st
import pandas as pd
from datetime import datetime

from icons import icon
from config import COL_FILE_FROM, COL_SAP
from helpers import sort_bulan_key, buat_label_bulan, to_number
from core import (
    baca_file_apapun, baca_file_pds_delivery,
    ekstrak_dari_master, proses_update, buat_excel,
    buat_template_pds_delivery,
    tampilkan_bulan_badges,
)


def render(mode):
    if mode == "Buat Master (Paste)":
        _buat_master_paste()
    elif mode == "Update Master":
        _update_master()
    else:  # "Hitung PDS & Delivery"
        _hitung_pds()


# ═══════════════════════════════════════════════════════════════════
#  MODE 1: BUAT MASTER (PASTE)
# ═══════════════════════════════════════════════════════════════════
def _buat_master_paste():
    st.markdown(f'''
    <div class="section-title">{icon("package", 22, "#FF9800")} Buat Master dari Paste</div>
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

    kolom_bulan = buat_label_bulan(tahun_mulai, bulan_mulai, jumlah_bulan)

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


# ═══════════════════════════════════════════════════════════════════
#  MODE 2: UPDATE MASTER
# ═══════════════════════════════════════════════════════════════════
def _update_master():
    st.markdown(f'''
    <div class="section-title">{icon("file-check", 22, "#FF9800")} Update Master</div>
    <div class="info-box">{icon("info", 18, "#3b82f6")} Upload <b>master terakhir</b> + <b>paste data baru</b> dari Excel. Data dengan kombinasi <b>Part Number + Date</b> yang sama akan di-<b>update</b>, sisanya ditambahkan.</div>
    ''', unsafe_allow_html=True)

    # ── Upload master ──
    st.markdown(f'<div class="section-title">{icon("folder-open", 18, "#FF9800")} 1. Upload Master Terakhir</div>', unsafe_allow_html=True)

    file_master = st.file_uploader(
        "Upload file master",
        type=['xlsx', 'xls', 'csv'],
        key='master_file_mitsuba_update',
        label_visibility="collapsed"
    )

    # ── Pengaturan kolom bulan ──
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

    # ── Tabel paste ──
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

    df_kosong = pd.DataFrame({c: [""] * int(n_rows) for c in semua_kolom})

    df_paste = st.data_editor(
        df_kosong,
        num_rows="dynamic",
        use_container_width=True,
        key="mitsuba_upd_editor",
        column_config={
            "No": st.column_config.TextColumn("No", width="small"),
            "PART NAME": st.column_config.TextColumn("PART NAME", width="medium"),
            "PART NO": st.column_config.TextColumn("PART NO", width="medium"),
        }
    )

    # ── Input tanggal ──
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
        st.caption("Tanggal ini dipakai untuk semua baris data baru (format: YYYY/MM/DD).")

    # ── Tombol update ──
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
                try:
                    file_master.seek(0)
                    df_master_lama = pd.read_excel(file_master, header=0, dtype=str)
                except:
                    file_master.seek(0)
                    df_master_lama, _, _ = baca_file_apapun(file_master)

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

            st.markdown(f'<div class="section-title">{icon("eye", 20, "#FF9800")} Preview Data Baru</div>', unsafe_allow_html=True)
            st.dataframe(df_new.head(20), use_container_width=True)
            st.caption(f"Total: {len(df_new)} baris")

            with st.spinner("Menggabungkan master..."):
                semua_bulan = set(kolom_bulan)
                df_final, bulan_final = proses_update(
                    df_master_lama, df_new, semua_bulan,
                    {}, {}, {}
                )
                excel_bytes = buat_excel(df_final, bulan_final)

            tampilkan_bulan_badges(bulan_final)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("folder", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Master Lama</div><div class="stat-value">{len(df_master_lama):,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col2:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("file-plus", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Data Baru</div><div class="stat-value">{len(df_new):,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col3:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("layers", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Master Final</div><div class="stat-value">{len(df_final):,}</div></div>
                </div>''', unsafe_allow_html=True)
            with col4:
                st.markdown(f'''
                <div class="stat-card">
                    <div class="icon-wrap">{icon("calendar", 22, "#2E7D32")}</div>
                    <div><div class="stat-label">Kolom Bulan</div><div class="stat-value">{len(bulan_final):,}</div></div>
                </div>''', unsafe_allow_html=True)

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
#  MODE 3: HITUNG PDS & DELIVERY
# ═══════════════════════════════════════════════════════════════════
def _hitung_pds():
    st.markdown(f'''
    <div class="section-title">{icon("calculator", 22, "#FF9800")} Hitung PDS &amp; Delivery</div>
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