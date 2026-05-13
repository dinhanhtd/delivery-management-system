"""
db_config.py
============
Cấu hình kết nối database dùng chung cho toàn bộ project.
Import file này trong auth.py, generate_data.py, và streamlit_app.py.

Nhất quán với:
  - schema.sql          : delivery_db, charset = utf8mb4, 12 bảng
  - create_mysql_users.sql : user = app_service
"""

# ──────────────────────────────────────────────────────────────
# Kết nối database
# ──────────────────────────────────────────────────────────────
# DB_CONFIG — plain connect params, KHÔNG có pool keys.
# Dùng cho: mysql.connector.connect() — auth.py, generate_data.py
# LƯU Ý: mysql.connector.connect() không chấp nhận pool_name/pool_size;
# nếu truyền vào sẽ báo lỗi "Unrecognized option: pool_name".
DB_CONFIG = {
    "host":            "localhost",
    "port":            3306,
    "user":            "app_service",
    "password":        "AppService_Pass@2024",
    "database":        "delivery_db",
    "charset":         "utf8mb4",
    "use_unicode":     True,
    "autocommit":      False,
    "connect_timeout": 10,
}

# DB_POOL_CONFIG — bao gồm pool params.
# Dùng cho: MySQLConnectionPool trong streamlit_app.py
# pool_size=5 đủ cho 1 user dùng local; tăng lên 10+ khi deploy nhiều user.
DB_POOL_CONFIG = {
    **DB_CONFIG,
    "pool_name":          "delivery_pool",
    "pool_size":          5,
    "pool_reset_session": True,
}


# ──────────────────────────────────────────────────────────────
# Tên bảng — đồng bộ với schema.sql (12 bảng)
# ──────────────────────────────────────────────────────────────
class Tables:
    # Core tables (gốc)
    USERS                  = "Users"
    ORDER_CATEGORIES       = "OrderCategories"
    CUSTOMERS              = "Customers"
    VEHICLES               = "Vehicles"
    ORDERS                 = "Orders"
    DELIVERIES             = "Deliveries"
    DELIVERY_ATTEMPTS      = "DeliveryAttempts"
    EXPENSES               = "Expenses"

    # Advanced / Customer Intelligence tables
    CUSTOMER_PREFERENCES   = "CustomerPreferences"   # giờ giao ưa thích, blackout
    ORDER_ISSUES           = "OrderIssues"            # sự cố đơn hàng
    DELIVERY_RESCHEDULED   = "DeliveryRescheduled"    # lịch sử lên lịch lại
    DELIVERY_RATINGS       = "DeliveryRatings"        # đánh giá sau giao hàng


# ──────────────────────────────────────────────────────────────
# Tên view — đồng bộ với schema.sql (7 view)
# ──────────────────────────────────────────────────────────────
class Views:
    CURRENT_SCHEDULE       = "vw_current_schedule"
    COST_PER_ORDER         = "vw_cost_per_order"
    OUTSTANDING_ORDERS     = "vw_outstanding_orders"
    AVAILABLE_VEHICLES     = "vw_available_vehicles"
    FAILED_ATTEMPTS        = "vw_failed_attempts_summary"
    AT_RISK_DELIVERIES     = "vw_at_risk_deliveries"       # dashboard "Đơn rủi ro cao"
    CUSTOMER_ORDER_SUMMARY = "vw_customer_order_summary"   # Customer Intelligence tab


# ──────────────────────────────────────────────────────────────
# Stored Procedures — đồng bộ với schema.sql (5 SP)
# ──────────────────────────────────────────────────────────────
class Procedures:
    ASSIGN_DELIVERY        = "sp_assign_delivery"        # phân công xe + tài xế (ACID)
    SMART_RESCHEDULE       = "sp_smart_reschedule"       # xử lý thất bại thông minh (ACID)
    RESOLVE_ISSUE          = "sp_resolve_issue"          # giải quyết sự cố (ACID)
    RESOLVE_ISSUE_V2       = "sp_resolve_issue_v2"       # giải quyết sự cố v2 - ROW_COUNT check
    GET_DELIVERY_COST      = "sp_get_delivery_cost"      # tổng chi phí chuyến giao


# ──────────────────────────────────────────────────────────────
# User-Defined Functions — đồng bộ với schema.sql (4 UDF)
# ──────────────────────────────────────────────────────────────
class Functions:
    AVG_DELIVERY_COST      = "fn_avg_delivery_cost"        # chi phí TB toàn hệ thống
    DELIVERIES_PER_VEHICLE = "fn_deliveries_per_vehicle"   # số chuyến theo xe
    CUSTOMER_SUCCESS_RATE  = "fn_customer_success_rate"    # tỉ lệ giao thành công theo KH
    CUSTOMER_RISK_LEVEL    = "fn_customer_risk_level"      # mức độ rủi ro: low/medium/high/critical


# ──────────────────────────────────────────────────────────────
# Role values — khớp với ENUM trong bảng Users
# ──────────────────────────────────────────────────────────────
class Roles:
    MANAGER     = "delivery_manager"
    DISPATCHER  = "dispatcher"
    ACCOUNTANT  = "accountant"
    ALL         = [MANAGER, DISPATCHER, ACCOUNTANT]