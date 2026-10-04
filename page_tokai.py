# page_tokai.py — Semua mode untuk grup Tokai Rika
import streamlit as st
import pandas as pd
from datetime import datetime

from icons import icon
from config import COL_FILE_FROM, COL_SAP, LABELS_RINGKASAN
from helpers import sort_bulan_key
from core import (
    cek_duplikat_nama_file, cek_file_sudah_di_master,
    tampilkan_error_duplikat, tampilkan_error_file_sudah_ada,
    ekstrak_dari_banyak_file, ekstrak_dari_master,
    baca_file_apapun, baca_file_pds_delivery,
    buat_template_pds_delivery,
    proses_update, buat_excel,
    tampilkan_info_files, tampilkan_bulan_badges,
)


def render(mode):
    if mode == "Buat Master Baru":
        _buat_master_baru()
    elif mode == "Update Master":
        _update_master()
    else:  # "Hitung PDS & Delivery"
        _hitung_pds()


# ═══════════════════════════════════════════════════════════════════
#  MODE 1: BUAT MASTER BARU
# ═══════════════════════════════════════════════════════════════════
def _buat_master_baru():
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
                label=f"Download Master Baru ({len(df_final)} baris) (.xlsx)",
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


# ═══════════════════════════════════════════════════════════════════
#  MODE 2: UPDATE MASTER
# ═══════════════════════════════════════════════════════════════════
def _update_master():
    st.markdown(f'''
    <div class="section-title">{icon("file-check", 22, "#4CAF50")} Update Master</div>
    <div class="info-box">{icon("info", 18, "#3b82f6")} Upload <b>master lama</b> + <b>data baru</b> + (opsional) <b>file PDS &amp; Delivery</b>.</div>
    ''', unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.markdown(f'''
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            {icon("folder-open", 18, "#4CAF50")}
            <span style="font-weight:600;color:#111827;">1. File Master (Sudah Ada)</span>
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
            <span style="font-weight:600;color:#111827;">2. File Data Baru (bisa banyak)</span>
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
        <span style="font-weight:600;color:#111827;">3. File PDS &amp; Delivery (Opsional)</span>
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
                label="Download",
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
                label=f"Download Master Updated ({len(df_final)} baris) (.xlsx)",
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
                        label="Download Template",
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


# ═══════════════════════════════════════════════════════════════════
#  MODE 3: HITUNG PDS & DELIVERY
# ═══════════════════════════════════════════════════════════════════
def _hitung_pds():
    st.markdown(f'''
    <div class="section-title">{icon("calculator", 22, "#4CAF50")} Hitung PDS &amp; Delivery</div>
    <div class="info-box">{icon("info", 18, "#3b82f6")} Upload <b>master lama</b> + <b>file PDS &amp; Delivery</b>. Master akan diperkaya dengan PDS/Delivery &amp; semua rumus dihitung ulang.</div>
    ''', unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown(f'''
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;">
            {icon("folder-open", 18, "#4CAF50")}
            <span style="font-weight:600;color:#111827;">1. File Master (Sudah Ada)</span>
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
            <span style="font-weight:600;color:#111827;">2. File PDS &amp; Delivery</span>
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
                label="Download Template Kosong",
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
                label=f"Download Master + PDS/Delivery ({len(df_final)} baris) (.xlsx)",
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
                with st.expander(f"{len(pds_info['errors'])} baris bermasalah di file PDS"):
                    for err in pds_info['errors']:
                        st.write(err)

        except Exception as e:
            st.error(f"Error: {e}")
            st.exception(e)

    elif file_master is not None:
        st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Upload juga file <b>PDS &amp; Delivery</b> untuk melanjutkan.</div>', unsafe_allow_html=True)
    elif file_pds is not None:
        st.markdown(f'<div class="warn-box">{icon("alert", 18, "#f59e0b")} Upload juga file <b>master lama</b> untuk melanjutkan.</div>', unsafe_allow_html=True)