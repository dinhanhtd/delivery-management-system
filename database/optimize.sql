-- ============================================================
-- admin/optimize.sql
-- Query Optimization Analysis — delivery_db
--
-- Mục đích:
--   1. Kiểm tra các index đã tạo trong schema.sql có được dùng không
--   2. Phát hiện full table scan (type = ALL → nguy hiểm)
--   3. Gợi ý composite index nếu cần
--
-- Nhất quán với schema: tên bảng/cột/index từ schema.sql
-- Cách dùng: Paste từng EXPLAIN vào MySQL Workbench và đọc output
-- ============================================================

USE delivery_db;

-- ============================================================
-- PHẦN 1: KIỂM TRA INDEX HIỆN TẠI
-- ============================================================

-- Xem toàn bộ index đã tạo
SELECT
    TABLE_NAME,
    INDEX_NAME,
    COLUMN_NAME,
    SEQ_IN_INDEX,
    NON_UNIQUE,
    CARDINALITY
FROM   information_schema.STATISTICS
WHERE  TABLE_SCHEMA = 'delivery_db'
ORDER  BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;


-- ============================================================
-- PHẦN 2: EXPLAIN CÁC QUERY THƯỜNG DÙNG
-- Cột quan trọng cần xem:
--   type       : 'ref' hoặc 'range' = tốt | 'ALL' = full scan = xấu
--   key        : tên index được dùng (NULL = không dùng index nào)
--   rows       : số dòng MySQL phải quét (càng nhỏ càng tốt)
--   Extra      : 'Using index' = rất tốt | 'Using filesort' = cần tối ưu
-- ============================================================

-- ── Q1: Tìm đơn hàng theo trạng thái ─────────────────────
-- Dùng index: idx_orders_status
EXPLAIN
SELECT OrderID, RecipientName, RecipientPhone, DeliveryAddress, Status
FROM   Orders
WHERE  Status = 'pending'
ORDER  BY OrderDate DESC;
-- Mong đợi: key = idx_orders_status, type = ref

-- ── Q2: Tìm đơn của một khách hàng ──────────────────────
-- Dùng index: idx_orders_customer
EXPLAIN
SELECT o.OrderID, o.Status, o.DeclaredValueVND, o.IsFragile, o.IsHighValue
FROM   Orders o
WHERE  o.CustomerID = 1;
-- Mong đợi: key = idx_orders_customer, type = ref

-- ── Q3: Lịch giao hôm nay ────────────────────────────────
-- Dùng index: idx_deliveries_scheduled
EXPLAIN
SELECT d.DeliveryID, d.DriverName, d.DriverPhone, d.Status,
       o.RecipientName, o.DeliveryAddress
FROM   Deliveries d
JOIN   Orders     o ON d.OrderID = o.OrderID
WHERE  d.ScheduledDate = CURDATE()
  AND  d.Status IN ('scheduled', 'in_progress');
-- Mong đợi: key = idx_deliveries_scheduled trên Deliveries

-- ── Q4: Xe đang rảnh ─────────────────────────────────────
-- Dùng index: idx_vehicles_availability
EXPLAIN
SELECT VehicleID, VehicleType, LicensePlate, MaxWeightKg, CanCarryFragile
FROM   Vehicles
WHERE  Availability = 'available';
-- Mong đợi: key = idx_vehicles_availability, type = ref

-- ── Q5: Lịch sử thất bại của một chuyến giao ─────────────
-- Dùng index: idx_attempts_delivery
EXPLAIN
SELECT AttemptNumber, AttemptTime, FailureReason, NextAttemptScheduled
FROM   DeliveryAttempts
WHERE  DeliveryID = 1
ORDER  BY AttemptNumber ASC;
-- Mong đợi: key = idx_attempts_delivery hoặc uq_delivery_attempt