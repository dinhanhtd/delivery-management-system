"""
admin/backup.py
===============
Script sao lưu (backup) và phục hồi (restore) tự động cho delivery_db.
"""

import os
import gzip
import shutil
import logging
import argparse
import datetime
import subprocess
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# CONFIG — 
# ─────────────────────────────────────────────────────────────
DB_HOST     = "localhost"
DB_PORT     = 3306
DB_NAME     = "delivery_db"
DB_USER     = "root"
DB_PASSWORD = "1234"          

BACKUP_DIR  = Path(__file__).parent / "backups"   # thư mục lưu backup
KEEP_DAYS   = 7                                    
LOG_DIR     = Path(__file__).parent / ".." / "logs"

# ─────────────────────────────────────────────────────────────
# Logger
# ─────────────────────────────────────────────────────────────
BACKUP_DIR.mkdir(parents=True, exist_ok=True) 

import sys
import os
# Thêm thư mục chứa backup.py (cùng cấp với logger.py) vào sys.path
# insert(0, ...) ưu tiên thư mục này hơn các package cùng tên khác
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from logger import app_logger as _log  # type: ignore

# ─────────────────────────────────────────────────────────────
# Helper: tạo file .my.cnf tạm để không lộ password trên CLI
# ─────────────────────────────────────────────────────────────
def _write_mycnf(path: Path):
    """Ghi file cấu hình MySQL tạm — tránh password hiện trên CLI."""
    path.write_text(
        f"[client]\n"
        f"host={DB_HOST}\n"
        f"port={DB_PORT}\n"
        f"user={DB_USER}\n"
        f"password={DB_PASSWORD}\n",
        encoding="utf-8"
    )
    path.chmod(0o600)   # chỉ owner đọc được


# ─────────────────────────────────────────────────────────────
# BACKUP
# ─────────────────────────────────────────────────────────────
def run_backup() -> Path | None:
    """
    Thực hiện full backup delivery_db → <BACKUP_DIR>/delivery_db_YYYYMMDD_HHMMSS.sql.gz

    Returns:
        Path của file backup nếu thành công, None nếu thất bại.
    """
    timestamp   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    sql_file    = BACKUP_DIR / f"delivery_db_{timestamp}.sql"
    gz_file     = sql_file.with_suffix(".sql.gz")
    mycnf_file  = BACKUP_DIR / ".tmp_mycnf"

    _log.info(f"BACKUP_START | db={DB_NAME} | dest={gz_file.name}")

    try:
        _write_mycnf(mycnf_file)

        cmd = [
            "mysqldump",
            f"--defaults-extra-file={mycnf_file}",
            "--single-transaction",     # consistent snapshot (InnoDB)
            "--routines",               # bao gồm SP + UDF
            "--triggers",               # bao gồm triggers
            "--events",
            "--add-drop-database",
            "--databases", DB_NAME,
        ]

        with open(sql_file, "w", encoding="utf-8") as f:
            result = subprocess.run(
                cmd,
                stdout=f,
                stderr=subprocess.PIPE,
                text=True,
            )

        if result.returncode != 0:
            _log.error(f"BACKUP_FAIL | mysqldump error: {result.stderr.strip()}")
            sql_file.unlink(missing_ok=True)
            return None

        # ── Nén file .sql → .sql.gz ─────────────────────────
        with open(sql_file, "rb") as f_in, gzip.open(gz_file, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        sql_file.unlink()   # xoá file .sql chưa nén

        size_kb = gz_file.stat().st_size // 1024
        _log.info(f"BACKUP_OK | file={gz_file.name} | size={size_kb} KB")
        return gz_file

    except FileNotFoundError:
        _log.error("BACKUP_FAIL | mysqldump không tìm thấy — kiểm tra PATH hoặc cài MySQL Server")
        return None
    except Exception as e:
        _log.error(f"BACKUP_FAIL | {e}")
        return None
    finally:
        mycnf_file.unlink(missing_ok=True)   # luôn xoá file tạm


# ─────────────────────────────────────────────────────────────
# RETENTION — tự động xoá backup cũ
# ─────────────────────────────────────────────────────────────
def purge_old_backups(keep_days: int = KEEP_DAYS) -> int:
    """
    Xoá các file backup cũ hơn keep_days ngày.

    Returns:
        Số file đã xoá.
    """
    cutoff  = datetime.datetime.now() - datetime.timedelta(days=keep_days)
    removed = 0

    for f in BACKUP_DIR.glob("delivery_db_*.sql.gz"):
        mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
        if mtime < cutoff:
            f.unlink()
            _log.info(f"PURGE | removed={f.name} | mtime={mtime:%Y-%m-%d}")
            removed += 1

    if removed:
        _log.info(f"PURGE_DONE | removed={removed} file(s) older than {keep_days} days")
    return removed


# ─────────────────────────────────────────────────────────────
# RESTORE
# ─────────────────────────────────────────────────────────────
def run_restore(backup_file: str) -> bool:
    gz_path = Path(backup_file)
    if not gz_path.exists():
        _log.error(f"RESTORE_FAIL | file not found: {backup_file}")
        return False

    print(f"\n⚠️  CẢNH BÁO: Thao tác này sẽ XOÁ và ghi đè database '{DB_NAME}'!")
    print(f"   File restore: {gz_path.name}")
    confirm = input("   Nhập 'YES' để xác nhận: ").strip()
    if confirm != "YES":
        print("   Huỷ restore.")
        return False

    mycnf_file = BACKUP_DIR / ".tmp_mycnf"
    _log.info(f"RESTORE_START | file={gz_path.name}")

    try:
        _write_mycnf(mycnf_file)

        # Giải nén → pipe thẳng vào mysql
        with gzip.open(gz_path, "rb") as f_in:
            sql_content = f_in.read()

        cmd = [
            "mysql",
            f"--defaults-extra-file={mycnf_file}",
        ]
        result = subprocess.run(
            cmd,
            input=sql_content,
            capture_output=True,
        )

        if result.returncode != 0:
            _log.error(f"RESTORE_FAIL | {result.stderr.decode().strip()}")
            return False

        _log.info(f"RESTORE_OK | file={gz_path.name}")
        print(f"   ✅ Restore thành công từ {gz_path.name}")
        return True

    except FileNotFoundError:
        _log.error("RESTORE_FAIL | mysql client không tìm thấy — kiểm tra PATH")
        return False
    except Exception as e:
        _log.error(f"RESTORE_FAIL | {e}")
        return False
    finally:
        mycnf_file.unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────
# LIST backups
# ─────────────────────────────────────────────────────────────
def list_backups():
    """In danh sách toàn bộ backup hiện có."""
    files = sorted(BACKUP_DIR.glob("delivery_db_*.sql.gz"))
    if not files:
        print("  (Chưa có backup nào)")
        return

    print(f"\n{'File':<45} {'Size':>8}  {'Ngày tạo'}")
    print("─" * 72)
    for f in files:
        mtime   = datetime.datetime.fromtimestamp(f.stat().st_mtime)
        size_kb = f.stat().st_size // 1024
        print(f"  {f.name:<43} {size_kb:>6} KB  {mtime:%Y-%m-%d %H:%M:%S}")
    print(f"\n  Tổng: {len(files)} file(s) trong {BACKUP_DIR}")


# ─────────────────────────────────────────────────────────────
# MAIN — CLI
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Backup & restore script cho delivery_db"
    )
    parser.add_argument(
        "--restore", metavar="FILE",
        help="Restore database từ file .sql.gz chỉ định"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Liệt kê các file backup hiện có"
    )
    parser.add_argument(
        "--keep-days", type=int, default=KEEP_DAYS,
        help=f"Số ngày giữ backup (mặc định: {KEEP_DAYS})"
    )
    args = parser.parse_args()

    print("=" * 60)
    print("  Delivery DB — Backup & Restore Utility")
    print("=" * 60)

    if args.list:
        list_backups()
        return

    if args.restore:
        run_restore(args.restore)
        return

    # Mặc định: chạy backup + purge
    backup_file = run_backup()
    if backup_file:
        print(f"\n  ✅ Backup thành công: {backup_file.name}")
    else:
        print("\n  ❌ Backup thất bại — xem logs/backup.log để biết chi tiết")
        return

    removed = purge_old_backups(keep_days=args.keep_days)
    if removed:
        print(f"  🗑  Đã xoá {removed} backup cũ hơn {args.keep_days} ngày")

    list_backups()
    print("=" * 60)


if __name__ == "__main__":
    main()