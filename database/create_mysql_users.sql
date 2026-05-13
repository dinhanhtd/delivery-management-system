-- ============================================================
-- admin/create_mysql_users.sql
-- Tạo tài khoản MySQL thực tế và gán Role
--
-- Chạy file này SAU KHI đã chạy schema.sql (để có sẵn các role)
-- Cú pháp: mysql -u root -p < admin/create_mysql_users.sql
--
-- File này CHỈ chứa CREATE USER + GRANT — không chứa schema DDL
-- ============================================================

USE delivery_db;

-- ============================================================
-- PHẦN 1: TẠO USER ACCOUNTS
-- Thay đổi mật khẩu trước khi deploy thực tế!
-- ============================================================

-- Xoá user cũ nếu tồn tại (để chạy lại an toàn)
DROP USER IF EXISTS 'dm_user'@'localhost';
DROP USER IF EXISTS 'dispatcher_user'@'localhost';
DROP USER IF EXISTS 'accountant_user'@'localhost';
DROP USER IF EXISTS 'app_service'@'localhost';

-- ── User 1: Delivery Manager ─────────────────────────────
-- Tài khoản cho quản lý giao hàng — full quyền
CREATE USER 'dm_user'@'localhost'
    IDENTIFIED BY 'DM_StrongPass@2024'
    PASSWORD EXPIRE INTERVAL 90 DAY        -- bắt đổi mật khẩu sau 90 ngày
    FAILED_LOGIN_ATTEMPTS 5
    PASSWORD_LOCK_TIME 1;                  -- khoá 1 ngày nếu sai 5 lần

-- ── User 2: Dispatcher ───────────────────────────────────
-- Tài khoản cho điều phối viên — quản lý đơn và giao hàng
CREATE USER 'dispatcher_user'@'localhost'
    IDENTIFIED BY 'Dispatch_Pass@2024'
    PASSWORD EXPIRE INTERVAL 90 DAY
    FAILED_LOGIN_ATTEMPTS 5
    PASSWORD_LOCK_TIME 1;

-- ── User 3: Accountant ───────────────────────────────────
-- Tài khoản cho kế toán — chỉ đọc báo cáo và chi phí
CREATE USER 'accountant_user'@'localhost'
    IDENTIFIED BY 'Account_Pass@2024'
    PASSWORD EXPIRE INTERVAL 90 DAY
    FAILED_LOGIN_ATTEMPTS 5
    PASSWORD_LOCK_TIME 1;

-- ── User 4: Application Service Account ──────────────────
-- Tài khoản dùng cho Python app kết nối vào DB
-- Chỉ cấp quyền vừa đủ (principle of least privilege)
CREATE USER 'app_service'@'localhost'
    IDENTIFIED BY 'AppService_Pass@2024'
    PASSWORD EXPIRE NEVER;                 -- service account không expire


-- ============================================================
-- PHẦN 2: GÁN ROLE VÀO USER
-- Roles đã được định nghĩa trong schema.sql
-- ============================================================

-- Gán role tương ứng
GRANT 'delivery_manager_role' TO 'dm_user'@'localhost';
GRANT 'dispatcher_role'       TO 'dispatcher_user'@'localhost';
GRANT 'accountant_role'       TO 'accountant_user'@'localhost';

-- app_service cần quyền đủ để Python app chạy CRUD + gọi SP
GRANT SELECT, INSERT, UPDATE, DELETE ON delivery_db.* TO 'app_service'@'localhost';
GRANT EXECUTE ON delivery_db.*                        TO 'app_service'@'localhost';

-- ============================================================
-- PHẦN 3: ĐẶT DEFAULT ROLE (tự động active khi login)
-- Nếu không set, user phải chạy SET ROLE mỗi khi login
-- ============================================================

SET DEFAULT ROLE 'delivery_manager_role' TO 'dm_user'@'localhost';
SET DEFAULT ROLE 'dispatcher_role'       TO 'dispatcher_user'@'localhost';
SET DEFAULT ROLE 'accountant_role'       TO 'accountant_user'@'localhost';


-- ============================================================
-- PHẦN 4: FLUSH và XÁC NHẬN
-- ============================================================

FLUSH PRIVILEGES;

-- Kiểm tra user đã tạo
SELECT
    User                    AS 'Tên user',
    Host                    AS 'Host',
    password_expired        AS 'Pw expired?',
    account_locked          AS 'Locked?',
    Password_lifetime       AS 'Pw lifetime (ngày)'
FROM mysql.user
WHERE User IN ('dm_user','dispatcher_user','accountant_user','app_service')
ORDER BY User;

-- Kiểm tra role đã gán
SELECT
    FROM_USER   AS 'Role',
    TO_USER     AS 'Được gán cho user'
FROM mysql.role_edges
ORDER BY TO_USER;

-- Kiểm tra quyền chi tiết của từng user
SHOW GRANTS FOR 'dm_user'@'localhost';
SHOW GRANTS FOR 'dispatcher_user'@'localhost';
SHOW GRANTS FOR 'accountant_user'@'localhost';
SHOW GRANTS FOR 'app_service'@'localhost';

-- ============================================================
-- END OF FILE
-- ============================================================