import logging
import os
from logging.handlers import RotatingFileHandler

# Thư mục logs nằm trong cùng thư mục với logger.py (project root)
# Dùng abspath để tránh lỗi khi script được gọi từ thư mục khác
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Định dạng chuẩn cho toàn dự án
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-15s | %(funcName)s:%(lineno)d | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def setup_logger(name, log_file, level=logging.INFO):
    """Khởi tạo một logger với cơ chế xoay vòng file"""
    handler = RotatingFileHandler(
        os.path.join(LOG_DIR, log_file), 
        maxBytes=5*1024*1024,
        backupCount=5,        
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))

    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    if not logger.handlers:
        logger.addHandler(handler)
        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(console)
        
    return logger

app_logger   = setup_logger("delivery.app",   "app.log")
db_logger    = setup_logger("delivery.db",    "db.log", level=logging.DEBUG)
audit_logger = setup_logger("delivery.audit", "audit.log")

# Expose LOG_DIR so other modules can locate log files (e.g., audit viewer in GUI)
__all__ = ["app_logger", "db_logger", "audit_logger", "LOG_DIR"]