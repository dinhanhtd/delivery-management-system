"""
security/auth.py
================
Module xác thực người dùng cho Delivery Service Management System.

Xử lý:
  - Đăng nhập với bcrypt (PasswordHash trong bảng Users)
  - Phân quyền theo Role: delivery_manager | dispatcher | accountant
  - Session management trong bộ nhớ (không lưu token ra file)
  - Audit log ghi ra file mỗi lần login/logout

Nhất quán với schema:
  - Bảng: Users
  - Cột:  UserID, Username, PasswordHash, Role, FullName, Email, IsActive
  - Role values: 'delivery_manager', 'dispatcher', 'accountant'
"""

import bcrypt
import logging
import datetime
import os
import mysql.connector
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Audit logger — ghi mọi sự kiện login/logout/fail ra file
# ─────────────────────────────────────────────────────────────
from logger import audit_logger as _audit


# ─────────────────────────────────────────────────────────────
# Dataclass đại diện cho phiên đăng nhập
# ─────────────────────────────────────────────────────────────
@dataclass
class UserSession:
    user_id:    int
    username:   str
    full_name:  str
    role:       str          # 'delivery_manager' | 'dispatcher' | 'accountant'
    email:      Optional[str]
    login_time: datetime.datetime = field(default_factory=datetime.datetime.now)

    # ── Quyền truy cập theo role ─────────────────────────────
    PERMISSIONS: dict = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        self.PERMISSIONS = {
            "delivery_manager": {
                "can_manage_customers", "can_manage_orders", "can_manage_vehicles",
                "can_manage_deliveries", "can_view_expenses", "can_manage_expenses",
                "can_view_reports", "can_manage_users", "can_assign_delivery",
                "can_record_attempt",
            },
            "dispatcher": {
                "can_manage_orders", "can_manage_deliveries",
                "can_assign_delivery", "can_record_attempt",
                "can_view_vehicles", "can_view_customers",
            },
            "accountant": {
                "can_view_expenses", "can_view_reports",
                "can_view_orders",
            },
        }

    def can(self, permission: str) -> bool:
        """Kiểm tra quyền. Dùng trong GUI để ẩn/hiện nút."""
        return permission in self.PERMISSIONS.get(self.role, set())

    @property
    def display_role(self) -> str:
        labels = {
            "delivery_manager": "Quản lý giao hàng",
            "dispatcher":       "Điều phối viên",
            "accountant":       "Kế toán",
        }
        return labels.get(self.role, self.role)

    @property
    def session_duration(self) -> str:
        delta = datetime.datetime.now() - self.login_time
        m, s = divmod(int(delta.total_seconds()), 60)
        return f"{m} phút {s} giây"


# ─────────────────────────────────────────────────────────────
# AuthManager — singleton quản lý phiên đăng nhập
# ─────────────────────────────────────────────────────────────
class AuthManager:
    """
    Quản lý toàn bộ vòng đời xác thực.

    Cách dùng:
        auth = AuthManager(db_config)
        session = auth.login("admin", "Admin@123")
        if session:
            print(session.display_role)
            if session.can("can_manage_orders"):
                ...
        auth.logout()
    """

    MAX_ATTEMPTS = 5          # Khóa sau N lần sai liên tiếp
    LOCKOUT_MINUTES = 15      # Thời gian khóa

    def __init__(self, db_config: dict):
        self._db_config   = db_config
        self._session:    Optional[UserSession] = None
        self._fail_count: dict[str, int] = {}       # username → số lần sai
        self._lockout:    dict[str, datetime.datetime] = {}  # username → thời điểm khóa

    # ── Kết nối DB ───────────────────────────────────────────
    # Lọc ra các key chỉ dùng cho MySQLConnectionPool (không hợp lệ với connect())
    _POOL_KEYS = frozenset({"pool_name", "pool_size", "pool_reset_session"})

    def _get_connection(self):
        cfg = {k: v for k, v in self._db_config.items()
               if k not in self._POOL_KEYS}
        return mysql.connector.connect(**cfg)

    # ── Kiểm tra tài khoản bị khóa ───────────────────────────
    def _is_locked(self, username: str) -> bool:
        if username not in self._lockout:
            return False
        unlock_at = self._lockout[username] + datetime.timedelta(minutes=self.LOCKOUT_MINUTES)
        if datetime.datetime.now() >= unlock_at:
            # Tự động mở khóa sau thời gian chờ
            del self._lockout[username]
            self._fail_count[username] = 0
            return False
        return True

    def _lockout_remaining(self, username: str) -> int:
        """Số phút còn lại trước khi mở khóa."""
        if username not in self._lockout:
            return 0
        unlock_at = self._lockout[username] + datetime.timedelta(minutes=self.LOCKOUT_MINUTES)
        delta = unlock_at - datetime.datetime.now()
        return max(0, int(delta.total_seconds() // 60) + 1)

    # ── Đăng nhập ────────────────────────────────────────────
    def login(self, username: str, password: str) -> tuple[Optional[UserSession], str]:
        """
        Xác thực username + password.

        Returns:
            (UserSession, "")        nếu thành công
            (None, "thông báo lỗi") nếu thất bại
        """
        username = username.strip()

        # 1. Kiểm tra tài khoản bị khóa
        if self._is_locked(username):
            mins = self._lockout_remaining(username)
            msg = f"Tài khoản tạm khóa. Thử lại sau {mins} phút."
            _audit.warning(f"LOGIN_BLOCKED | user={username} | reason=lockout")
            return None, msg

        # 2. Truy vấn database
        try:
            conn   = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT UserID, Username, PasswordHash, Role,
                       FullName, Email, IsActive
                FROM   Users
                WHERE  Username = %s
                LIMIT  1
                """,
                (username,)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
        except mysql.connector.Error as e:
            _audit.error(f"LOGIN_DB_ERROR | user={username} | error={e}")
            return None, "Lỗi kết nối database. Vui lòng thử lại."

        # 3. Kiểm tra user tồn tại
        if row is None:
            self._record_fail(username)
            _audit.warning(f"LOGIN_FAIL | user={username} | reason=not_found")
            return None, "Sai tên đăng nhập hoặc mật khẩu."

        # 4. Kiểm tra tài khoản đang hoạt động
        if not row["IsActive"]:
            _audit.warning(f"LOGIN_FAIL | user={username} | reason=inactive")
            return None, "Tài khoản đã bị vô hiệu hóa. Liên hệ quản trị viên."

        # 5. Xác minh mật khẩu với bcrypt
        #    bcrypt.checkpw so sánh plain-text với hash đã lưu trong DB
        password_ok = bcrypt.checkpw(
            password.encode("utf-8"),
            row["PasswordHash"].encode("utf-8")
        )

        if not password_ok:
            self._record_fail(username)
            fails = self._fail_count.get(username, 0)
            remaining = self.MAX_ATTEMPTS - fails
            _audit.warning(f"LOGIN_FAIL | user={username} | reason=wrong_password | attempts={fails}")
            if remaining > 0:
                return None, f"Sai mật khẩu. Còn {remaining} lần thử."
            else:
                return None, f"Tài khoản bị khóa {self.LOCKOUT_MINUTES} phút do nhập sai nhiều lần."

        # 6. Đăng nhập thành công — tạo session
        self._fail_count[username] = 0          # reset bộ đếm lỗi
        self._session = UserSession(
            user_id   = row["UserID"],
            username  = row["Username"],
            full_name = row["FullName"],
            role      = row["Role"],
            email     = row["Email"],
        )
        _audit.info(f"LOGIN_OK | user={username} | role={row['Role']} | id={row['UserID']}")
        return self._session, ""

    # ── Đăng xuất ────────────────────────────────────────────
    def logout(self):
        if self._session:
            _audit.info(
                f"LOGOUT | user={self._session.username} "
                f"| duration={self._session.session_duration}"
            )
        self._session = None

    # ── Đổi mật khẩu ─────────────────────────────────────────
    def change_password(
        self,
        username: str,
        old_password: str,
        new_password: str
    ) -> tuple[bool, str]:
        """
        Đổi mật khẩu. Yêu cầu xác nhận mật khẩu cũ.
        Mật khẩu mới phải dài ít nhất 8 ký tự.

        Note: KHÔNG gọi self.login() ở đây vì nó sẽ record fail
        và có thể khoá tài khoản. Verify trực tiếp bằng bcrypt.
        """
        if len(new_password) < 8:
            return False, "Mật khẩu mới phải có ít nhất 8 ký tự."

        # Verify old password trực tiếp với DB — KHÔNG đụng vào _fail_count
        try:
            conn   = self._get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT PasswordHash, IsActive FROM Users WHERE Username=%s",
                (username,)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
        except mysql.connector.Error as e:
            return False, f"Lỗi DB khi xác thực: {e}"

        if not row:
            return False, "Tài khoản không tồn tại."
        if not row["IsActive"]:
            return False, "Tài khoản đã bị vô hiệu hoá."

        if not bcrypt.checkpw(
            old_password.encode("utf-8"),
            row["PasswordHash"].encode("utf-8")
        ):
            _audit.warning(f"PASSWORD_CHANGE_FAIL | user={username} | reason=wrong_old_password")
            return False, "Mật khẩu cũ không đúng."

        # Băm mật khẩu mới
        new_hash = bcrypt.hashpw(
            new_password.encode("utf-8"),
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        try:
            conn   = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE Users SET PasswordHash = %s WHERE Username = %s",
                (new_hash, username)
            )
            conn.commit()
            cursor.close()
            conn.close()
        except mysql.connector.Error as e:
            return False, f"Lỗi DB khi đổi mật khẩu: {e}"

        _audit.info(f"PASSWORD_CHANGED | user={username}")
        return True, "Đổi mật khẩu thành công."

    # ── Tạo tài khoản mới (chỉ manager) ─────────────────────
    def create_user(
        self,
        actor_session: UserSession,
        username: str,
        password: str,
        role: str,
        full_name: str,
        email: str = ""
    ) -> tuple[bool, str]:
        """Chỉ delivery_manager mới được tạo tài khoản mới."""
        if not actor_session.can("can_manage_users"):
            return False, "Không có quyền tạo tài khoản."

        valid_roles = {"delivery_manager", "dispatcher", "accountant"}
        if role not in valid_roles:
            return False, f"Role không hợp lệ. Chọn: {', '.join(valid_roles)}"

        if len(password) < 8:
            return False, "Mật khẩu phải có ít nhất 8 ký tự."

        pw_hash = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=12)
        ).decode("utf-8")

        try:
            conn   = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Users (Username, PasswordHash, Role, FullName, Email)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (username, pw_hash, role, full_name, email or None)
            )
            conn.commit()
            new_id = cursor.lastrowid
            cursor.close()
            conn.close()
        except mysql.connector.IntegrityError:
            return False, f"Tên đăng nhập '{username}' đã tồn tại."
        except mysql.connector.Error as e:
            return False, f"Lỗi DB: {e}"

        _audit.info(
            f"USER_CREATED | by={actor_session.username} "
            f"| new_user={username} | role={role} | id={new_id}"
        )
        return True, f"Tạo tài khoản '{username}' thành công (ID={new_id})."

    # ── Helper nội bộ ────────────────────────────────────────
    def _record_fail(self, username: str):
        self._fail_count[username] = self._fail_count.get(username, 0) + 1
        if self._fail_count[username] >= self.MAX_ATTEMPTS:
            self._lockout[username] = datetime.datetime.now()
            _audit.warning(
                f"ACCOUNT_LOCKED | user={username} "
                f"| attempts={self._fail_count[username]} "
                f"| lock_minutes={self.LOCKOUT_MINUTES}"
            )

    # ── Trạng thái hiện tại ───────────────────────────────────
    @property
    def current_session(self) -> Optional[UserSession]:
        return self._session

    @property
    def is_logged_in(self) -> bool:
        return self._session is not None


# ─────────────────────────────────────────────────────────────
# Hàm tiện ích — dùng trong generate_data.py và GUI
# ─────────────────────────────────────────────────────────────
def hash_password(plain_text: str) -> str:
    """
    Băm mật khẩu bcrypt với cost factor 12.
    Dùng khi tạo tài khoản (generate_data.py, create_user).
    """
    return bcrypt.hashpw(
        plain_text.encode("utf-8"),
        bcrypt.gensalt(rounds=12)
    ).decode("utf-8")


def verify_password(plain_text: str, hashed: str) -> bool:
    """
    Xác minh mật khẩu. Dùng độc lập nếu không cần AuthManager.
    """
    return bcrypt.checkpw(
        plain_text.encode("utf-8"),
        hashed.encode("utf-8")
    )


# ─────────────────────────────────────────────────────────────
# Quick test — chạy trực tiếp file này để kiểm tra
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from db_config import DB_CONFIG   # import từ file cấu hình chung

    auth = AuthManager(DB_CONFIG)

    print("=== Test đăng nhập đúng ===")
    session, err = auth.login("admin", "Admin@123")
    if session:
        print(f"  OK  : {session.full_name} ({session.display_role})")
        print(f"  Quyền manage_orders: {session.can('can_manage_orders')}")
        print(f"  Quyền manage_users : {session.can('can_manage_users')}")
    else:
        print(f"  FAIL: {err}")

    print("\n=== Test sai mật khẩu ===")
    _, err = auth.login("admin", "wrongpass")
    print(f"  Kết quả: {err}")

    print("\n=== Test tài khoản không tồn tại ===")
    _, err = auth.login("nonexistent", "pass")
    print(f"  Kết quả: {err}")

    print("\n=== Test hash mật khẩu ===")
    h = hash_password("TestPass@123")
    print(f"  Hash  : {h[:30]}...")
    print(f"  Verify: {verify_password('TestPass@123', h)}")

    auth.logout()
    print("\n=== Audit log đã ghi vào logs/auth_audit.log ===")