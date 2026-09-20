import os
import win32com.client as win32

SRC = r"E:\14. Project Nanda\01. Data Forecast From Customer\2026_excel"
DST = r"E:\14. Project Nanda\01. Data Forecast From Customer\2026_bersih"
os.makedirs(DST, exist_ok=True)

excel = win32.Dispatch("Excel.Application")
excel.Visible = False
excel.DisplayAlerts = False

for f in sorted(os.listdir(SRC)):
    if not f.lower().endswith(".xlsx"):
        continue
    src_path = os.path.join(SRC, f)
    dst_path = os.path.join(DST, f)
    try:
        wb = excel.Workbooks.Open(src_path)
        wb.SaveAs(dst_path, FileFormat=51)  # 51 = xlsx
        wb.Close(SaveChanges=False)
        print(f"[OK] {f}")
    except Exception as e:
        print(f"[GAGAL] {f} — {e}")

excel.Quit()