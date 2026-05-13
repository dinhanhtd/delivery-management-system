"""
generate_data.py  — Delivery Service Management System
=======================================================
Sinh du lieu mau cho schema.sql.
"""

import random
import bcrypt
import datetime
import mysql.connector
from faker import Faker

# ─────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────
# LƯU Ý BẢO MẬT: Script này dùng tài khoản root vì cần quyền:
#   • TRUNCATE TABLE (app_service chỉ có SELECT/INSERT/UPDATE/DELETE)
#   • SET foreign_key_checks = 0 (cần SUPER hoặc SESSION_VARIABLES_ADMIN)
# Script này chỉ chạy MỘT LẦN trong quá trình setup ban đầu,
# KHÔNG dùng trong môi trường production.
# Thay mật khẩu bên dưới cho phù hợp với cài đặt MySQL của bạn.
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "root",
    "password": "1234",        # ← Thay bằng mật khẩu root thực của bạn
    "database": "delivery_db",
    "charset":  "utf8mb4",
    "autocommit": False,
}

ROWS = 15   # so dong mau toi thieu cho moi bang chinh

fake = Faker("vi_VN")
Faker.seed(42)
random.seed(42)


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────
def hash_pw(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def vn_phone() -> str:
    prefix = random.choice([
        "032","033","034","035","036","038",
        "070","079","077","076","078",
        "082","083","084","085","086",
        "090","093","094","096","097","098",
    ])
    return prefix + "".join(str(random.randint(0,9)) for _ in range(7))


def vn_plate() -> str:
    city_codes = ["29","30","51","43","92","36","26","47"]
    letters    = "ABCDEFGHJKLMNPSTUVXY"
    return f"{random.choice(city_codes)}{random.choice(letters)}-{random.randint(10000,99999)}"


def bulk_insert(cur, table: str, rows: list) -> list:
    if not rows:
        return []
    cols    = list(rows[0].keys())
    ph      = ", ".join(["%s"] * len(cols))
    col_str = ", ".join([f"`{c}`" for c in cols])
    sql     = f"INSERT INTO `{table}` ({col_str}) VALUES ({ph})"
    ids     = []
    for row in rows:
        cur.execute(sql, [row[c] for c in cols])
        ids.append(cur.lastrowid)
    return ids


# ─────────────────────────────────────────────────────────
# DATA GENERATORS
# ─────────────────────────────────────────────────────────
def gen_users() -> list:
    predefined = [
        ("admin",       "Admin@123",  "delivery_manager", "Tran Diep Dinh Anh"),
        ("dispatcher1", "Dispatch@1", "dispatcher",       "Dinh Anh 2.0"),
        ("dispatcher2", "Dispatch@2", "dispatcher",       "Dinh Anh 3.0"),
        ("accountant1", "Account@1",  "accountant",       "Dinh Anh 4.0"),
        ("accountant2", "Account@2",  "accountant",       "Dinh Anh 5.0"),
    ]
    users = []
    for uname, pw, role, fname in predefined:
        users.append({
            "Username":     uname,
            "PasswordHash": hash_pw(pw),
            "Role":         role,
            "FullName":     fname,
            "Email":        f"{uname}@delivery.vn",
            "IsActive":     1,
        })
    roles = ["delivery_manager","dispatcher","accountant"]
    for i in range(max(0, ROWS - len(predefined))):
        uname = fake.user_name() + str(random.randint(10,99))
        users.append({
            "Username":     uname,
            "PasswordHash": hash_pw(fake.password(length=10, special_chars=True)),
            "Role":         random.choice(roles),
            "FullName":     fake.name(),
            "Email":        fake.email(),
            "IsActive":     random.choice([1,1,1,0]),
        })
    return users


def gen_order_categories() -> list:
    return [
        {"CategoryName":"standard",
         "Description":"Hang hoa thuong — van chuyen tieu chuan",
         "MaxDeliveryHours":48, "RequiresSignature":0,"RequiresInsurance":0,
         "SurchargeRate":0.00,  "AllowedVehicleTypes":"motorbike,van,truck,refrigerated_truck"},
        {"CategoryName":"fragile",
         "Description":"Hang de vo — can boc goi ky, xe co giam chan",
         "MaxDeliveryHours":36, "RequiresSignature":1,"RequiresInsurance":0,
         "SurchargeRate":10.00, "AllowedVehicleTypes":"van,truck,refrigerated_truck"},
        {"CategoryName":"high_value",
         "Description":"Hang gia tri cao — yeu cau bao hiem, chu ky xac nhan",
         "MaxDeliveryHours":24, "RequiresSignature":1,"RequiresInsurance":1,
         "SurchargeRate":15.00, "AllowedVehicleTypes":"van,truck"},
        {"CategoryName":"fragile_high_value",
         "Description":"Hang de vo + gia tri cao — uu tien cao nhat",
         "MaxDeliveryHours":12, "RequiresSignature":1,"RequiresInsurance":1,
         "SurchargeRate":25.00, "AllowedVehicleTypes":"van,truck"},
        {"CategoryName":"refrigerated",
         "Description":"Hang can bao quan lanh — thuc pham, duoc pham",
         "MaxDeliveryHours":12, "RequiresSignature":0,"RequiresInsurance":0,
         "SurchargeRate":20.00, "AllowedVehicleTypes":"refrigerated_truck"},
    ]


def gen_customers(n: int) -> list:
    cities = {
        "Ha Noi":           ["Hoan Kiem","Dong Da","Ba Dinh","Cau Giay","Tay Ho"],
        "TP. Ho Chi Minh":  ["Quan 1","Quan 3","Binh Thanh","Go Vap","Tan Binh"],
        "Da Nang":          ["Hai Chau","Thanh Khe","Lien Chieu"],
        "Hai Phong":        ["Hong Bang","Le Chan","Ngo Quyen"],
        "Can Tho":          ["Ninh Kieu","Binh Thuy","Cai Rang"],
    }
    custs = []
    for _ in range(n):
        city     = random.choice(list(cities))
        district = random.choice(cities[city])
        custs.append({
            "CustomerName": fake.name(),
            "PhoneNumber":  vn_phone(),
            "Email":        fake.email(),
            "Address":      f"So {random.randint(1,200)}, Duong so {random.randint(1,50)}, {district}, {city}",
            "Ward":         f"Phuong {random.randint(1,10)}",
            "District":     district,
            "City":         city,
            "Notes":        random.choice([None, None, "Goi truoc 30 phut", "De o cong bao ve"]),
        })
    return custs


def gen_customer_preferences(customer_ids: list) -> list:
    slots    = ["morning","afternoon","evening","anytime"]
    contacts = ["call","sms","email","any"]
    prefs = []
    for cid in customer_ids:
        prefs.append({
            "CustomerID":        cid,
            "PreferredTimeSlot": random.choice(slots),
            "BlackoutStart":     None,
            "BlackoutEnd":       None,
            "ContactMethod":     random.choice(contacts),
            "MaxDailyAttempts":  random.randint(1,3),
            "SpecialNotes":      random.choice([None, None, "Chi giao ban ngay"]),
        })
    return prefs


def gen_vehicles(n: int) -> list:
    types = ["motorbike","van","truck","refrigerated_truck"]
    wt_range = {"motorbike":(0.5,30),"van":(5,500),"truck":(50,3000),"refrigerated_truck":(50,2000)}
    max_val  = {"motorbike":2_000_000,"van":20_000_000,"truck":50_000_000,"refrigerated_truck":30_000_000}
    used_plates = set()
    vehs = []
    for _ in range(n):
        vt = random.choice(types)
        plate = vn_plate()
        while plate in used_plates:
            plate = vn_plate()
        used_plates.add(plate)
        wlo, whi = wt_range[vt]
        vehs.append({
            "VehicleType":    vt,
            "LicensePlate":   plate,
            "Availability":   random.choices(
                                  ["available","in_use","maintenance"],
                                  weights=[60,30,10])[0],
            "MaxWeightKg":    round(random.uniform(wlo, whi), 1),
            "MaxValueVND":    max_val[vt],
            "CanCarryFragile":0 if vt == "motorbike" else 1,
            "Notes":          None,
        })
    return vehs


def gen_orders(n: int, cust_ids: list, cat_ids: list) -> list:
    """
    Logic thời gian phụ thuộc vào Status của đơn hàng:
      - pending / assigned / in_transit (đơn đang chạy):
            OrderDate lùi tối đa 1–48 giờ → deadline vẫn còn trong tương lai,
            tránh HoursRemaining bị âm rất nặng trên giao diện.
      - delivered / failed / returned (đơn đã kết thúc):
            OrderDate lùi 0–30 ngày → phản ánh lịch sử thực tế.
      DeadlineDate luôn = OrderDate + 24..72 giờ (trigger không bị vi phạm).
    """
    # Status được chọn TRƯỚC để quyết định khoảng thời gian order_date
    active_statuses   = ["pending", "assigned", "in_transit"]
    finished_statuses = ["delivered", "failed", "returned"]
    all_statuses      = active_statuses + finished_statuses

    cat_map = {
        "standard": 0, "fragile": 1, "high_value": 2,
        "fragile_high_value": 3, "refrigerated": 4,
    }
    orders = []
    for _ in range(n):
        is_fragile = random.random() < 0.30
        declared   = random.randint(50_000, 15_000_000)
        is_hv      = declared > 5_000_000
        if   is_fragile and is_hv: cat = "fragile_high_value"
        elif is_fragile:            cat = "fragile"
        elif is_hv:                 cat = "high_value"
        else:                       cat = random.choice(["standard", "refrigerated"])

        # Bước 1: chọn status trước
        status = random.choice(all_statuses)

        # Bước 2: tính order_date dựa vào status
        if status in active_statuses:
            # Đơn đang chạy → chỉ lùi 1–48 giờ, deadline vẫn dương
            order_date = datetime.datetime.now() - datetime.timedelta(
                hours=random.randint(1, 48)
            )
        else:
            # Đơn đã kết thúc → lùi 3–30 ngày (đủ xa để phản ánh lịch sử)
            order_date = datetime.datetime.now() - datetime.timedelta(
                days=random.randint(3, 30)
            )

        # Bước 3: deadline luôn sau order_date 24–72 giờ
        deadline = order_date + datetime.timedelta(hours=random.randint(24, 72))

        orders.append({
            "CustomerID":          random.choice(cust_ids),
            "CategoryID":          cat_ids[cat_map[cat]],
            "OrderDate":           order_date,
            "Status":              status,
            "DeclaredValueVND":    declared,
            "WeightKg":            round(random.uniform(0.1, 50), 2),
            "IsFragile":           int(is_fragile),
            "IsHighValue":         int(is_hv),
            "RecipientName":       fake.name(),
            "RecipientPhone":      vn_phone(),
            "DeliveryAddress":     fake.address().replace('\n', ', '),
            "SpecialInstructions": random.choice([
                None, None, None, "Goi truoc khi giao", "Hang de vo de nhe",
                "Giao tan tay", "Chi giao gio hanh chinh",
            ]),
            "DeadlineDate":        deadline,
        })
    return orders


def gen_deliveries(n: int, order_ids: list, veh_ids: list,
                   ord_dates: dict) -> tuple:
    """
    [F1] ScheduledDate is always >= DATE(OrderDate) for that order.
         This satisfies trigger trg_validate_delivery_date.
    Returns: (list_of_dicts_to_insert, list_of_info_dicts)
    """
    drivers = [
        ("Nguyen Van An","0901234567"), ("Tran Thi Binh","0912345678"),
        ("Le Van Chien","0923456789"),  ("Pham Thi Dung","0934567890"),
        ("Hoang Van Em","0945678901"),  ("Vu Thi Phuong","0956789012"),
        ("Dang Van Giang","0967890123"),("Bui Thi Hanh","0978901234"),
    ]
    statuses = ["scheduled","in_progress","completed","failed","returned"]
    delivs_to_insert = []
    deliv_info       = []
    used_veh_dates: set = set()

    for i in range(n):
        oid = order_ids[i % len(order_ids)]
        vid = random.choice(veh_ids)

        # [F1] ScheduledDate >= DATE(OrderDate)
        order_date = ord_dates[oid]
        if isinstance(order_date, datetime.datetime):
            order_date_d = order_date.date()
        else:
            order_date_d = order_date

        # Schedule 0–3 days after order (never before)
        sched = order_date_d + datetime.timedelta(days=random.randint(0, 3))

        tries = 0
        while (vid, str(sched)) in used_veh_dates and tries < 20:
            vid   = random.choice(veh_ids)
            sched = order_date_d + datetime.timedelta(days=random.randint(0, 3))
            tries += 1
        if tries >= 20:
            continue
        used_veh_dates.add((vid, str(sched)))

        dname, dphone = random.choice(drivers)
        status = random.choice(statuses)
        actual = None

        if status == "completed":
            actual = datetime.datetime.combine(
                sched, datetime.time(random.randint(8,18), random.randint(0,59))
            )

        d_dict = {
            "OrderID":            oid,
            "VehicleID":          vid,
            "DriverName":         dname,
            "DriverPhone":        dphone,
            "ScheduledDate":      sched,
            "DeliveryDate":       sched if status in ("completed","failed") else None,
            "Status":             status,
            "ActualDeliveryTime": actual,
            "Notes":              None,
        }
        delivs_to_insert.append(d_dict)
        deliv_info.append({"ScheduledDate": sched})

    return delivs_to_insert, deliv_info


def gen_delivery_attempts(deliv_ids: list, deliv_info: list) -> list:
    retry_reasons = ["no_answer","not_home","wrong_address","other"]
    fatal_reasons = ["refused","damaged_on_arrival"]
    attempts = []

    indices = random.sample(range(len(deliv_ids)),
                            k=max(1, len(deliv_ids) * 4 // 10))

    for idx in indices:
        did        = deliv_ids[idx]
        sched_date = deliv_info[idx]["ScheduledDate"]
        n_att      = random.randint(1, 3)
        base_time  = datetime.datetime.combine(sched_date, datetime.time(8, 0))
        base_time += datetime.timedelta(hours=random.randint(1, 4))

        for att_no in range(1, n_att + 1):
            is_last = (att_no == n_att) or (att_no == 3)
            reason  = (random.choice(retry_reasons + fatal_reasons)
                       if is_last else random.choice(retry_reasons))

            next_att = None
            if att_no < 3 and reason not in fatal_reasons:
                next_att = base_time + datetime.timedelta(hours=4)

            attempts.append({
                "DeliveryID":           did,
                "AttemptNumber":        att_no,
                "AttemptTime":          base_time,
                "FailureReason":        reason,
                "ContactAttempted":     random.choice([0,1]),
                "Notes":                random.choice([
                    "Nguoi nhan khong bat may","Khong co nguoi o nha", None, None]),
                "NextAttemptScheduled": next_att,
                "ResolvedAt":           None,
            })

            if reason in fatal_reasons:
                break
            base_time += datetime.timedelta(hours=random.randint(3, 6))

    return attempts


def gen_order_issues(order_ids: list, deliv_ids: list) -> list:
    issue_types  = ["damaged","wrong_item","missing_item",
                    "refused_quality","address_mismatch","other"]
    severities   = ["low","medium","high","critical"]
    # Note: 'pending' will be set for unresolved issues;
    # resolved ones will use sp_resolve_issue later.
    resolutions  = ["resend","refund","partial_refund",
                    "reinspect","dismissed","pending"]
    issues = []
    n_issues = max(2, len(order_ids) // 3)

    for oid in random.sample(order_ids, k=min(n_issues, len(order_ids))):
        resolved_before = random.choice([True, False])
        did        = random.choice(deliv_ids) if deliv_ids else None
        resolution = random.choice(resolutions) if resolved_before else "pending"
        issues.append({
            "OrderID":        oid,
            "DeliveryID":     did,
            "IssueType":      random.choice(issue_types),
            "ReportedBy":     random.choice(["driver","customer","manager"]),
            "Severity":       random.choice(severities),
            "Description":    random.choice([
                "Hang bi vo trong qua trinh van chuyen",
                "Khach tu choi nhan hang vi khong dung mo ta",
                "Sai dia chi giao hang",
                "Hang co dau hieu bi tam uot",
                None,
            ]),
            "Resolution":     resolution,
            "ResolutionNotes":("Da xu ly" if resolution != "pending" else None),
            "ResolvedAt":     (
                datetime.datetime.now() - datetime.timedelta(hours=random.randint(1,48))
                if resolution != "pending" else None
            ),
        })
    return issues


def gen_delivery_rescheduled(deliv_ids: list,
                              deliv_info: list) -> list:
    """
    [F1] NewScheduledDate > OldScheduledDate (always in the future)
    """
    reasons = ["customer_busy","package_issue","driver_issue",
               "weather","traffic","other"]
    slots   = ["morning","afternoon","evening","anytime"]
    reschs  = []
    sample  = random.sample(deliv_ids, k=max(1, len(deliv_ids) // 4))

    for did in sample:
        idx      = deliv_ids.index(did)
        old_date = deliv_info[idx]["ScheduledDate"]
        # [F1] New date is always AFTER old date
        new_date = old_date + datetime.timedelta(days=random.randint(1, 3))
        reschs.append({
            "OriginalDeliveryID": did,
            "Reason":             random.choice(reasons),
            "OldScheduledDate":   old_date,
            "NewScheduledDate":   new_date,
            "NewTimeSlot":        random.choice(slots),
            "AutoScheduled":      random.choice([0,1]),
            "Notes":              random.choice([None, "Len lich tu dong theo yeu cau khach"]),
        })
    return reschs


def gen_expenses(deliv_ids: list) -> list:
    exp_types = {
        "fuel":          (20_000, 150_000),
        "toll":          (5_000,  30_000),
        "handling":      (10_000, 80_000),
        "insurance":     (5_000,  50_000),
        "failed_attempt":(10_000, 20_000),
        "other":         (5_000,  30_000),
    }
    exps = []
    for did in deliv_ids:
        for _ in range(random.randint(1, 3)):
            etype = random.choice(list(exp_types))
            lo, hi = exp_types[etype]
            exps.append({
                "DeliveryID":  did,
                "ExpenseType": etype,
                "Amount":      round(random.randint(lo//1000, hi//1000) * 1000, 0),
                "Description": f"Chi phi {etype} chuyen #{did}",
                "ExpenseDate": (datetime.date.today() -
                                datetime.timedelta(days=random.randint(0, 10))),
            })
    return exps


def gen_delivery_ratings(completed_deliv_ids: list) -> list:
    ratings = []
    sample  = random.sample(completed_deliv_ids,
                            k=max(1, len(completed_deliv_ids) // 3))
    for did in sample:
        ratings.append({
            "DeliveryID":     did,
            "OrderCondition": random.randint(3, 5),
            "DriverService":  random.randint(3, 5),
            "DeliveryTime":   random.randint(2, 5),
            "Comment":        random.choice([
                None, None, "Giao nhanh, hang nguyen ven",
                "Tai xe than thien", "Giao dung gio",
            ]),
        })
    return ratings


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
def main():
    print("=" * 62)
    print("  Delivery DB — Sample Data Generator (Fixed)")
    print(f"  ROWS per table = {ROWS}")
    print("=" * 62)

    conn = mysql.connector.connect(**DB_CONFIG)
    cur  = conn.cursor()
    cur.execute("USE delivery_db")
    cur.execute("SET foreign_key_checks = 0")

    tables = [
        "DeliveryRatings","OrderIssues","DeliveryRescheduled",
        "Expenses","DeliveryAttempts","Deliveries",
        "Orders","Vehicles","CustomerPreferences","Customers",
        "OrderCategories","Users",
    ]
    for t in tables:
        cur.execute(f"TRUNCATE TABLE `{t}`")
    cur.execute("SET foreign_key_checks = 1")
    conn.commit()
    print("✓ Da xoa du lieu cu")

    # 1. Users
    print(f"  Sinh {max(ROWS,5)} Users (bcrypt — co the cham)...")
    user_ids = bulk_insert(cur, "Users", gen_users())
    conn.commit()
    print(f"✓ Users: {len(user_ids)} dong")

    # 2. OrderCategories
    cat_ids = bulk_insert(cur, "OrderCategories", gen_order_categories())
    conn.commit()
    print(f"✓ OrderCategories: {len(cat_ids)} dong")

    # 3. Customers
    cust_ids = bulk_insert(cur, "Customers", gen_customers(ROWS))
    conn.commit()
    print(f"✓ Customers: {len(cust_ids)} dong")

    # 4. CustomerPreferences
    pref_ids = bulk_insert(cur, "CustomerPreferences",
                           gen_customer_preferences(cust_ids))
    conn.commit()
    print(f"✓ CustomerPreferences: {len(pref_ids)} dong")

    # 5. Vehicles
    veh_ids = bulk_insert(cur, "Vehicles", gen_vehicles(ROWS))
    conn.commit()
    print(f"✓ Vehicles: {len(veh_ids)} dong")

    # 6. Orders — insert one-by-one to catch trigger errors
    ord_ids   = []
    ord_dates = {}
    skipped   = 0
    for row in gen_orders(ROWS, cust_ids, cat_ids):
        cols    = list(row.keys())
        ph      = ", ".join(["%s"] * len(cols))
        col_str = ", ".join([f"`{c}`" for c in cols])
        try:
            cur.execute(
                f"INSERT INTO `Orders` ({col_str}) VALUES ({ph})",
                [row[c] for c in cols]
            )
            new_oid = cur.lastrowid
            ord_ids.append(new_oid)
            ord_dates[new_oid] = row["OrderDate"]
        except mysql.connector.Error as e:
            skipped += 1
            print(f"    [Orders skip] {e.msg[:80]}")
    conn.commit()
    print(f"✓ Orders: {len(ord_ids)} dong (bo qua: {skipped})")

    # 7. Deliveries
    deliv_ids   = []
    deliv_info  = []
    delivs_data, di_data = gen_deliveries(ROWS, ord_ids, veh_ids, ord_dates)

    for row, info in zip(delivs_data, di_data):
        cols    = list(row.keys())
        ph      = ", ".join(["%s"] * len(cols))
        col_str = ", ".join([f"`{c}`" for c in cols])
        try:
            cur.execute(
                f"INSERT INTO `Deliveries` ({col_str}) VALUES ({ph})",
                [row[c] for c in cols]
            )
            deliv_ids.append(cur.lastrowid)
            deliv_info.append(info)
        except mysql.connector.Error as e:
            print(f"    [Deliveries skip] {e.msg[:80]}")
    conn.commit()
    print(f"✓ Deliveries: {len(deliv_ids)} dong")

    if deliv_ids:
        # 8. DeliveryAttempts
        att_ids = bulk_insert(cur, "DeliveryAttempts",
                              gen_delivery_attempts(deliv_ids, deliv_info))
        conn.commit()
        print(f"✓ DeliveryAttempts: {len(att_ids)} dong")

        # 9. OrderIssues
        issue_ids = bulk_insert(cur, "OrderIssues",
                                gen_order_issues(ord_ids, deliv_ids))
        conn.commit()
        print(f"✓ OrderIssues: {len(issue_ids)} dong")

        # 10. DeliveryRescheduled
        resch_ids = bulk_insert(cur, "DeliveryRescheduled",
                                gen_delivery_rescheduled(deliv_ids, deliv_info))
        conn.commit()
        print(f"✓ DeliveryRescheduled: {len(resch_ids)} dong")

        # 11. Expenses
        exp_ids = bulk_insert(cur, "Expenses", gen_expenses(deliv_ids))
        conn.commit()
        print(f"✓ Expenses: {len(exp_ids)} dong")

        # 12. DeliveryRatings (completed deliveries only)
        completed_ids = []
        for did in deliv_ids:
            cur.execute(
                "SELECT Status FROM Deliveries WHERE DeliveryID=%s", (did,))
            row = cur.fetchone()
            if row and row[0] == "completed":
                completed_ids.append(did)

        if completed_ids:
            for rd in gen_delivery_ratings(completed_ids):
                try:
                    cols    = list(rd.keys())
                    ph      = ", ".join(["%s"] * len(cols))
                    col_str = ", ".join([f"`{c}`" for c in cols])
                    cur.execute(
                        f"INSERT INTO `DeliveryRatings` ({col_str}) VALUES ({ph})",
                        [rd[c] for c in cols]
                    )
                except mysql.connector.IntegrityError:
                    pass  # UNIQUE constraint on DeliveryID
            conn.commit()
            print(f"✓ DeliveryRatings: sinh cho {len(completed_ids)} chuyen hoan thanh")

    # ─── Kiem tra nhanh ─────────────────────────────────
    print()
    print("─" * 62)
    print("  So dong tung bang:")
    for t in reversed(tables):
        cur.execute(f"SELECT COUNT(*) FROM `{t}`")
        cnt = cur.fetchone()[0]
        print(f"    {t:<32} {cnt:>4} dong")

    print()
    print("  Test views:")
    for view in ["vw_customer_order_summary","vw_at_risk_deliveries",
                 "vw_cost_per_order","vw_failed_attempts_summary"]:
        cur.execute(f"SELECT COUNT(*) FROM `{view}`")
        cnt = cur.fetchone()[0]
        print(f"    {view:<35} {cnt:>4} dong")

    print()
    print("  Test UDFs:")
    cur.execute("SELECT fn_avg_delivery_cost()")
    print(f"    fn_avg_delivery_cost()              = {cur.fetchone()[0]:,.0f} VND")

    if cust_ids:
        cid = cust_ids[0]
        cur.execute(f"SELECT fn_customer_success_rate({cid})")
        rate = cur.fetchone()[0]
        cur.execute(f"SELECT fn_customer_risk_level({cid})")
        risk = cur.fetchone()[0]
        print(f"    fn_customer_success_rate(cust #{cid}) = {rate}%")
        print(f"    fn_customer_risk_level(cust #{cid})   = {risk}")

    print()
    print("  Test trigger — DeadlineDate <= OrderDate (phai bi chặn):")
    try:
        cur.execute("""
            INSERT INTO Orders
                (CustomerID, CategoryID, DeclaredValueVND, WeightKg,
                 RecipientName, RecipientPhone, DeliveryAddress,
                 OrderDate, DeadlineDate)
            VALUES (%s, %s, 100000, 1.0, 'Trigger Test', '0900000000',
                    '123 Test St', NOW(), DATE_SUB(NOW(), INTERVAL 1 HOUR))
        """, (cust_ids[0], cat_ids[0]))
        conn.rollback()
        print("    ❌ Trigger KHONG hoat dong! Du lieu sai da duoc chen.")
    except mysql.connector.Error as e:
        conn.rollback()
        print(f"    ✓ Trigger da chan: {e.msg[:70]}")

    cur.close()
    conn.close()
    print()
    print("=" * 62)
    print("  Du lieu mau da duoc tao thanh cong!")
    print("=" * 62)


if __name__ == "__main__":
    main()