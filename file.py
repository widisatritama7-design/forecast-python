import zipfile
import shutil
from pathlib import Path

# ============================================================
# EXTRACT ZIP & COLLECT ALL EXCEL FILES
# ============================================================

def main():
    print("=" * 60)
    print("   EXTRACT ZIP & COLLECT ALL EXCEL FILES")
    print("=" * 60)

    zip_input = input("\nMasukkan path file ZIP: ").strip().strip('"')

    if not zip_input:
        print("Path ZIP kosong.")
        return

    zip_path = Path(zip_input)

    if not zip_path.exists():
        print(f"File tidak ditemukan: {zip_path}")
        return

    if zip_path.suffix.lower() != ".zip":
        print("File yang dipilih bukan file ZIP.")
        return

    # Folder output dibuat di lokasi yang sama dengan ZIP
    base_dir = zip_path.parent
    extract_dir = base_dir / f"{zip_path.stem}_extracted"
    excel_dir = base_dir / f"{zip_path.stem}_excel"

    extract_dir.mkdir(parents=True, exist_ok=True)
    excel_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[1/3] Mengekstrak ZIP...")
    print(f"      ZIP     : {zip_path}")
    print(f"      Extract : {extract_dir}")

    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(extract_dir)
    except zipfile.BadZipFile:
        print("ERROR: File ZIP rusak atau tidak valid.")
        return
    except Exception as e:
        print(f"ERROR saat ekstraksi: {e}")
        return

    print("\n[2/3] Mencari semua file Excel...")

    # Format Excel yang dicari
    excel_extensions = {
        ".xlsx",
        ".xls",
        ".xlsm",
        ".xlsb",
        ".xltx",
        ".xltm",
    }

    excel_files = [
        file
        for file in extract_dir.rglob("*")
        if file.is_file() and file.suffix.lower() in excel_extensions
    ]

    print(f"      Ditemukan: {len(excel_files)} file Excel")

    if not excel_files:
        print("\nTidak ada file Excel yang ditemukan.")
        return

    print("\n[3/3] Mengumpulkan file Excel...")

    copied = 0
    skipped = 0

    for source in excel_files:
        destination = excel_dir / source.name

        # Jika nama file sama, jangan overwrite.
        # Tambahkan nomor: file.xlsx -> file_1.xlsx
        if destination.exists():
            counter = 1
            while True:
                new_name = f"{source.stem}_{counter}{source.suffix}"
                destination = excel_dir / new_name

                if not destination.exists():
                    break

                counter += 1

        try:
            shutil.copy2(source, destination)
            copied += 1
            print(f"      ✓ {source.relative_to(extract_dir)}")
        except Exception as e:
            skipped += 1
            print(f"      ✗ Gagal: {source}")
            print(f"        {e}")

    print("\n" + "=" * 60)
    print("SELESAI")
    print("=" * 60)
    print(f"Total Excel ditemukan : {len(excel_files)}")
    print(f"Berhasil dikumpulkan  : {copied}")
    print(f"Gagal                  : {skipped}")
    print(f"\nFolder hasil Excel:")
    print(f"{excel_dir}")
    print(f"\nFolder hasil ekstrak:")
    print(f"{extract_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()
