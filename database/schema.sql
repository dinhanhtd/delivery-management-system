-- ============================================================
-- DELIVERY SERVICE MANAGEMENT SYSTEM
-- Database Schema
-- Project 10 - DATCOM Lab, NEU College of Technology
-- ============================================================

DROP DATABASE IF EXISTS delivery_db;
CREATE DATABASE delivery_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE delivery_db;

-- ============================================================
-- TABLE 1: Users
-- Advanced feature: bcrypt authentication, role-based access
-- ============================================================
CREATE TABLE Users (
    UserID        INT             AUTO_INCREMENT PRIMARY KEY,
    Username      VARCHAR(50)     NOT NULL UNIQUE,
    PasswordHash  VARCHAR(255)    NOT NULL COMMENT 'bcrypt hash — never store plain-text',
    Role          ENUM('delivery_manager','dispatcher','accountant') NOT NULL,
    FullName      VARCHAR(100)    NOT NULL,
    Email         VARCHAR(100)    UNIQUE,
    IsActive      BOOLEAN         NOT NULL DEFAULT TRUE,
    CreatedAt     TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UpdatedAt     TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP
);

-- ============================================================
-- TABLE 2: OrderCategories
-- Advanced feature: SLA hours, surcharge rate, vehicle rules
-- ============================================================
CREATE TABLE OrderCategories (
    CategoryID          INT             AUTO_INCREMENT PRIMARY KEY,
    CategoryName        VARCHAR(50)     NOT NULL UNIQUE,
    Description         TEXT,
    MaxDeliveryHours    INT             NOT NULL DEFAULT 48
                                        COMMENT 'SLA: max hours from order to delivery',
    RequiresSignature   BOOLEAN         NOT NULL DEFAULT FALSE,
    RequiresInsurance   BOOLEAN         NOT NULL DEFAULT FALSE,
    SurchargeRate       DECIMAL(5,2)    NOT NULL DEFAULT 0.00
                                        COMMENT 'Extra cost multiplier (%)',
    AllowedVehicleTypes SET('motorbike','van','truck','refrigerated_truck')
                                        NOT NULL DEFAULT 'motorbike,van,truck,refrigerated_truck'
);

-- ============================================================
-- TABLE 3: Customers
-- ============================================================
CREATE TABLE Customers (
    CustomerID      INT             AUTO_INCREMENT PRIMARY KEY,
    CustomerName    VARCHAR(100)    NOT NULL,
    PhoneNumber     VARCHAR(15)     NOT NULL,
    Email           VARCHAR(100),
    Address         TEXT            NOT NULL,
    Ward            VARCHAR(100)    COMMENT 'Phường/Xã',
    District        VARCHAR(100)    COMMENT 'Quận/Huyện',
    City            VARCHAR(50)     COMMENT 'Tỉnh/Thành phố',
    CreatedAt       TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Notes           TEXT            COMMENT 'Special delivery notes for this customer'
);

-- ============================================================
-- TABLE 4: CustomerPreferences
-- Advanced feature: Customer Intelligence — store preferred
-- delivery time slots and contact methods per customer
-- ============================================================
CREATE TABLE CustomerPreferences (
    PreferenceID        INT         AUTO_INCREMENT PRIMARY KEY,
    CustomerID          INT         NOT NULL UNIQUE,
    PreferredTimeSlot   ENUM('morning','afternoon','evening','anytime')
                                    NOT NULL DEFAULT 'anytime'
                                    COMMENT 'morning=7-12h, afternoon=12-17h, evening=17-21h',
    BlackoutStart       TIME        COMMENT 'Do-not-disturb window start',
    BlackoutEnd         TIME        COMMENT 'Do-not-disturb window end',
    ContactMethod       ENUM('call','sms','email','any') NOT NULL DEFAULT 'any',
    MaxDailyAttempts    TINYINT     NOT NULL DEFAULT 3,
    SpecialNotes        TEXT,
    UpdatedAt           TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID) ON DELETE CASCADE
);

-- ============================================================
-- TABLE 5: Vehicles
-- ============================================================
CREATE TABLE Vehicles (
    VehicleID       INT             AUTO_INCREMENT PRIMARY KEY,
    VehicleType     ENUM('motorbike','van','truck','refrigerated_truck') NOT NULL,
    LicensePlate    VARCHAR(20)     NOT NULL UNIQUE,
    Availability    ENUM('available','in_use','maintenance') NOT NULL DEFAULT 'available',
    MaxWeightKg     DECIMAL(8,2)    NOT NULL DEFAULT 0.00,
    MaxValueVND     BIGINT          COMMENT 'Max insurable order value this vehicle can carry',
    CanCarryFragile BOOLEAN         NOT NULL DEFAULT TRUE,
    Notes           TEXT
);

-- ============================================================
-- TABLE 6: Orders
-- Advanced feature: IsFragile / IsHighValue drive special handling
-- TRIGGER trg_validate_order_dates enforces DeadlineDate > OrderDate
-- ============================================================
CREATE TABLE Orders (
    OrderID                 INT             AUTO_INCREMENT PRIMARY KEY,
    CustomerID              INT             NOT NULL,
    CategoryID              INT             NOT NULL,
    OrderDate               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Status                  ENUM('pending','assigned','in_transit',
                                 'delivered','failed','returned')
                                            NOT NULL DEFAULT 'pending',
    DeclaredValueVND        BIGINT          NOT NULL DEFAULT 0
                                            COMMENT 'Declared value of goods in VND',
    WeightKg                DECIMAL(8,2)    NOT NULL DEFAULT 0.00,
    IsFragile               BOOLEAN         NOT NULL DEFAULT FALSE,
    IsHighValue             BOOLEAN         NOT NULL DEFAULT FALSE
                                            COMMENT 'Auto-set by trigger if DeclaredValueVND > 5,000,000',
    RecipientName           VARCHAR(100)    NOT NULL,
    RecipientPhone          VARCHAR(15)     NOT NULL,
    DeliveryAddress         TEXT            NOT NULL,
    SpecialInstructions     TEXT,
    DeadlineDate            DATETIME        COMMENT 'Must be AFTER OrderDate — enforced by trigger [F1]',
    CreatedAt               TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (CustomerID)  REFERENCES Customers(CustomerID) ON DELETE RESTRICT,
    FOREIGN KEY (CategoryID)  REFERENCES OrderCategories(CategoryID) ON DELETE RESTRICT
);

-- ============================================================
-- TABLE 7: Deliveries
-- TRIGGER trg_validate_delivery_date enforces
--      ScheduledDate >= OrderDate of linked order
-- ============================================================
CREATE TABLE Deliveries (
    DeliveryID          INT             AUTO_INCREMENT PRIMARY KEY,
    OrderID             INT             NOT NULL,
    VehicleID           INT             NOT NULL,
    DriverName          VARCHAR(100)    NOT NULL,
    DriverPhone         VARCHAR(15),
    ScheduledDate       DATE            NOT NULL,
    DeliveryDate        DATE,
    Status              ENUM('scheduled','in_progress','completed','failed','returned')
                                        NOT NULL DEFAULT 'scheduled',
    ActualDeliveryTime  DATETIME,
    Notes               TEXT,
    CreatedAt           TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (OrderID)   REFERENCES Orders(OrderID)   ON DELETE RESTRICT,
    FOREIGN KEY (VehicleID) REFERENCES Vehicles(VehicleID) ON DELETE RESTRICT
);

-- ============================================================
-- TABLE 8: DeliveryAttempts
-- Advanced feature: track failed attempts, schedule retries
-- Solution for: recipient not home / not answering / refused
-- ============================================================
CREATE TABLE DeliveryAttempts (
    AttemptID               INT         AUTO_INCREMENT PRIMARY KEY,
    DeliveryID              INT         NOT NULL,
    AttemptNumber           TINYINT     NOT NULL DEFAULT 1
                                        COMMENT 'Max 3 attempts before returning to sender',
    AttemptTime             DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FailureReason           ENUM('no_answer','not_home','refused',
                                 'wrong_address','damaged_on_arrival','other')
                                        NOT NULL,
    ContactAttempted        BOOLEAN     NOT NULL DEFAULT FALSE
                                        COMMENT 'Did driver call the recipient?',
    Notes                   TEXT,
    NextAttemptScheduled    DATETIME    COMMENT 'Auto-calculated by sp_smart_reschedule',
    ResolvedAt              DATETIME,
    FOREIGN KEY (DeliveryID) REFERENCES Deliveries(DeliveryID) ON DELETE CASCADE,
    UNIQUE KEY uq_delivery_attempt (DeliveryID, AttemptNumber)
);

-- ============================================================
-- TABLE 9: DeliveryRescheduled  
-- Advanced feature: Customer Intelligence — track every
-- rescheduling event for SLA analysis and pattern detection
-- ============================================================
CREATE TABLE DeliveryRescheduled (
    RescheduleID        INT         AUTO_INCREMENT PRIMARY KEY,
    OriginalDeliveryID  INT         NOT NULL,
    Reason              ENUM('customer_busy','package_issue','driver_issue',
                             'weather','traffic','other')
                                    NOT NULL,
    OldScheduledDate    DATE        NOT NULL,
    NewScheduledDate    DATE        NOT NULL,
    NewTimeSlot         ENUM('morning','afternoon','evening','anytime')
                                    NOT NULL DEFAULT 'anytime',
    AutoScheduled       BOOLEAN     NOT NULL DEFAULT FALSE
                                    COMMENT 'TRUE = system auto-rescheduled',
    Notes               TEXT,
    CreatedAt           TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (OriginalDeliveryID) REFERENCES Deliveries(DeliveryID) ON DELETE CASCADE
);

-- ============================================================
-- TABLE 10: OrderIssues
-- Advanced feature: Customer Intelligence — track quality
-- issues (damaged, wrong item, refused) for accountability
-- ============================================================
CREATE TABLE OrderIssues (
    IssueID         INT         AUTO_INCREMENT PRIMARY KEY,
    OrderID         INT         NOT NULL,
    DeliveryID      INT,
    IssueType       ENUM('damaged','wrong_item','missing_item',
                         'refused_quality','address_mismatch','other')
                                NOT NULL,
    ReportedBy      ENUM('driver','customer','manager') NOT NULL,
    Severity        ENUM('low','medium','high','critical') NOT NULL DEFAULT 'medium',
    Description     TEXT,
    Resolution      ENUM('resend','refund','partial_refund','reinspect',
                         'dismissed','pending')
                                NOT NULL DEFAULT 'pending',
    ResolutionNotes TEXT,
    ReportedAt      DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ResolvedAt      DATETIME,
    FOREIGN KEY (OrderID)    REFERENCES Orders(OrderID)    ON DELETE RESTRICT,
    FOREIGN KEY (DeliveryID) REFERENCES Deliveries(DeliveryID) ON DELETE SET NULL
);

-- ============================================================
-- TABLE 11: DeliveryRatings
-- Advanced feature: collect post-delivery ratings per
-- delivery (package condition, driver service, timeliness)
-- ============================================================
CREATE TABLE DeliveryRatings (
    RatingID        INT             AUTO_INCREMENT PRIMARY KEY,
    DeliveryID      INT             NOT NULL UNIQUE,
    OrderCondition  TINYINT         NOT NULL DEFAULT 5
                                    COMMENT '1-5 stars: condition of package on arrival',
    DriverService   TINYINT         NOT NULL DEFAULT 5
                                    COMMENT '1-5 stars: driver attitude and professionalism',
    DeliveryTime    TINYINT         NOT NULL DEFAULT 5
                                    COMMENT '1-5 stars: on-time performance',
    AverageScore    DECIMAL(3,2)    GENERATED ALWAYS AS
                                    ((OrderCondition + DriverService + DeliveryTime) / 3.0)
                                    STORED,
    Comment         TEXT,
    RatedAt         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (DeliveryID) REFERENCES Deliveries(DeliveryID) ON DELETE CASCADE,
    CONSTRAINT chk_rating_range
        CHECK (OrderCondition BETWEEN 1 AND 5
           AND DriverService  BETWEEN 1 AND 5
           AND DeliveryTime   BETWEEN 1 AND 5)
);

-- ============================================================
-- TABLE 12: Expenses
-- ============================================================
CREATE TABLE Expenses (
    ExpenseID       INT             AUTO_INCREMENT PRIMARY KEY,
    DeliveryID      INT             NOT NULL,
    ExpenseType     ENUM('fuel','toll','handling','insurance',
                         'failed_attempt','other')
                                    NOT NULL,
    Amount          DECIMAL(12,2)   NOT NULL DEFAULT 0.00,
    Description     TEXT,
    ExpenseDate     DATE            NOT NULL DEFAULT (CURRENT_DATE),
    CreatedAt       TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (DeliveryID) REFERENCES Deliveries(DeliveryID) ON DELETE RESTRICT
);


-- ============================================================
-- INDEXES — BASIC (speed up single-column lookups)
-- ============================================================
CREATE INDEX idx_orders_status          ON Orders(Status);
CREATE INDEX idx_orders_customer        ON Orders(CustomerID);
CREATE INDEX idx_orders_deadline        ON Orders(DeadlineDate);
CREATE INDEX idx_deliveries_status      ON Deliveries(Status);
CREATE INDEX idx_deliveries_scheduled   ON Deliveries(ScheduledDate);
CREATE INDEX idx_deliveries_vehicle     ON Deliveries(VehicleID);
CREATE INDEX idx_vehicles_availability  ON Vehicles(Availability);
CREATE INDEX idx_attempts_delivery      ON DeliveryAttempts(DeliveryID);
CREATE INDEX idx_expenses_delivery      ON Expenses(DeliveryID);
CREATE INDEX idx_customers_phone        ON Customers(PhoneNumber);
CREATE INDEX idx_issues_order           ON OrderIssues(OrderID);

-- Task 2 / Req 1: Chống Full Table Scan cho tab Issues
-- Index đơn trên Resolution — tăng tốc WHERE Resolution = 'pending'
CREATE INDEX idx_issues_resolution      ON OrderIssues(Resolution);

-- Composite Index trên (Severity DESC, ReportedAt DESC) —
-- phục vụ ORDER BY FIELD(Severity,'critical','high','medium','low'), ReportedAt DESC
-- trong page_issues() mà không cần filesort
CREATE INDEX idx_issues_severity_reported
    ON OrderIssues(Severity, ReportedAt DESC);

-- ============================================================
-- COMPOSITE INDEXES  
-- Purpose: eliminate "Using filesort" on JOIN+ORDER BY queries
-- These serve the multi-table JOINs in Reports, Issues tabs
-- ============================================================

-- CI-1: Supports sp_assign_delivery + trg_prevent_double_booking
--       Query: WHERE VehicleID=? AND ScheduledDate=? AND Status NOT IN (...)
CREATE INDEX idx_deliveries_vehicle_date
    ON Deliveries(VehicleID, ScheduledDate);

-- CI-2: Supports vw_outstanding_orders + Q8 in optimize.sql
--       Query: WHERE Status IN (...) ORDER BY DeadlineDate ASC
CREATE INDEX idx_orders_status_deadline
    ON Orders(Status, DeadlineDate);

-- CI-3: Supports vw_cost_per_order + sp_get_delivery_cost
--       Query: GROUP BY DeliveryID, ExpenseType
CREATE INDEX idx_expenses_delivery_type
    ON Expenses(DeliveryID, ExpenseType);

-- CI-4: Supports page_issues() — WHERE Resolution='pending' ORDER BY Severity
--       (đã khai báo ở trên với DESC, không tạo lại ở đây)

-- CI-5: Supports JOIN Deliveries d → OrderIssues in customer detail tab
CREATE INDEX idx_issues_order_resolution
    ON OrderIssues(OrderID, Resolution);

-- CI-6: Supports JOIN Orders→Deliveries→Attempts in customer detail
CREATE INDEX idx_deliveries_order_status
    ON Deliveries(OrderID, Status);


-- ============================================================
-- VIEWS
-- ============================================================

-- View 1: Current delivery schedule
CREATE OR REPLACE VIEW vw_current_schedule AS
SELECT
    d.DeliveryID,
    d.ScheduledDate,
    d.DriverName,
    d.DriverPhone,
    d.Status            AS DeliveryStatus,
    o.OrderID,
    o.RecipientName,
    o.RecipientPhone,
    o.DeliveryAddress,
    o.IsFragile,
    o.IsHighValue,
    v.LicensePlate,
    v.VehicleType,
    c.CategoryName
FROM Deliveries d
JOIN Orders          o ON d.OrderID    = o.OrderID
JOIN Vehicles        v ON d.VehicleID  = v.VehicleID
JOIN OrderCategories c ON o.CategoryID = c.CategoryID
WHERE d.Status IN ('scheduled','in_progress')
ORDER BY d.ScheduledDate ASC;

-- View 2: Total cost per order
CREATE OR REPLACE VIEW vw_cost_per_order AS
SELECT
    o.OrderID,
    o.RecipientName,
    o.Status          AS OrderStatus,
    o.DeclaredValueVND,
    o.IsFragile,
    o.IsHighValue,
    COALESCE(SUM(e.Amount), 0) AS TotalExpenseVND,
    COUNT(e.ExpenseID)         AS ExpenseCount
FROM Orders o
LEFT JOIN Deliveries d ON o.OrderID     = d.OrderID
LEFT JOIN Expenses   e ON d.DeliveryID  = e.DeliveryID
GROUP BY o.OrderID, o.RecipientName, o.Status,
         o.DeclaredValueVND, o.IsFragile, o.IsHighValue;

-- View 3: Outstanding orders (pending/assigned, past or near deadline)
CREATE OR REPLACE VIEW vw_outstanding_orders AS
SELECT
    o.OrderID,
    o.OrderDate,
    o.DeadlineDate,
    o.Status,
    o.RecipientName,
    o.RecipientPhone,
    o.DeliveryAddress,
    o.IsFragile,
    o.IsHighValue,
    cu.CustomerName,
    cu.PhoneNumber AS CustomerPhone,
    TIMESTAMPDIFF(HOUR, NOW(), o.DeadlineDate) AS HoursRemaining
FROM Orders o
JOIN Customers cu ON o.CustomerID = cu.CustomerID
WHERE o.Status IN ('pending','assigned')
ORDER BY o.DeadlineDate ASC;

-- View 4: Vehicles currently available
CREATE OR REPLACE VIEW vw_available_vehicles AS
SELECT
    v.VehicleID,
    v.VehicleType,
    v.LicensePlate,
    v.MaxWeightKg,
    v.MaxValueVND,
    v.CanCarryFragile
FROM Vehicles v
WHERE v.Availability = 'available'
ORDER BY v.VehicleType;

-- View 5: Failed delivery attempts summary
CREATE OR REPLACE VIEW vw_failed_attempts_summary AS
SELECT
    d.DeliveryID,
    o.OrderID,
    o.RecipientName,
    o.RecipientPhone,
    o.DeliveryAddress,
    COUNT(da.AttemptID)          AS TotalAttempts,
    MAX(da.AttemptNumber)        AS LastAttemptNumber,
    MAX(da.AttemptTime)          AS LastAttemptTime,
    MAX(da.NextAttemptScheduled) AS NextScheduled,
    da.FailureReason             AS LastFailureReason
FROM Deliveries d
JOIN Orders           o  ON d.OrderID    = o.OrderID
JOIN DeliveryAttempts da ON d.DeliveryID = da.DeliveryID
WHERE d.Status = 'failed'
GROUP BY d.DeliveryID, o.OrderID, o.RecipientName,
         o.RecipientPhone, o.DeliveryAddress, da.FailureReason;

-- ============================================================
-- View 6: At-risk deliveries  
-- Dashboard card "Đơn rủi ro cao" in streamlit_app.py
-- An order is "at-risk" if ANY of these hold:
--   • Has ≥2 failed attempts
--   • Deadline within next 6 hours
--   • IsFragile=1 AND IsHighValue=1
-- ============================================================
CREATE OR REPLACE VIEW vw_at_risk_deliveries AS
SELECT DISTINCT
    o.OrderID,
    o.RecipientName,
    o.RecipientPhone,
    o.DeliveryAddress,
    o.DeadlineDate,
    o.IsFragile,
    o.IsHighValue,
    o.Status                                        AS OrderStatus,
    COALESCE(att.TotalAttempts, 0)                  AS FailedAttempts,
    CASE 
        WHEN o.Status IN ('delivered', 'failed', 'returned') THEN 0
        ELSE TIMESTAMPDIFF(HOUR, NOW(), o.DeadlineDate)
    END                                             AS HoursUntilDeadline,
    CASE
        WHEN COALESCE(att.TotalAttempts, 0) >= 2        THEN 'critical'
        WHEN o.IsFragile = 1 AND o.IsHighValue = 1      THEN 'high'
        WHEN TIMESTAMPDIFF(HOUR, NOW(), o.DeadlineDate) <= 6
             AND o.Status NOT IN ('delivered','returned') THEN 'high'
        ELSE 'medium'
    END                                             AS RiskLevel
FROM Orders o
LEFT JOIN (
    SELECT d.OrderID, COUNT(da.AttemptID) AS TotalAttempts
    FROM   Deliveries      d
    JOIN   DeliveryAttempts da ON d.DeliveryID = da.DeliveryID
    GROUP  BY d.OrderID
) att ON o.OrderID = att.OrderID
WHERE o.Status NOT IN ('delivered','returned','failed')
  AND (
      COALESCE(att.TotalAttempts, 0) >= 2
   OR (o.IsFragile = 1 AND o.IsHighValue = 1)
   OR (o.DeadlineDate IS NOT NULL
       AND TIMESTAMPDIFF(HOUR, NOW(), o.DeadlineDate) BETWEEN 0 AND 6)
  )
ORDER BY RiskLevel DESC, o.DeadlineDate ASC;

-- ============================================================
-- View 7: Customer order summary  
-- Used in Customer Intelligence tab of streamlit_app.py
-- fn_customer_success_rate, fn_customer_risk_level are UDFs
-- (defined below — forward-ref is OK in MySQL when view is
--  queried at runtime, not at CREATE VIEW time)
-- ============================================================
CREATE OR REPLACE VIEW vw_customer_order_summary AS
SELECT
    c.CustomerID,
    c.CustomerName,
    c.PhoneNumber,
    c.City,
    COUNT(o.OrderID)                                            AS TotalOrders,
    SUM(o.Status = 'delivered')                                 AS DeliveredCount,
    SUM(o.Status = 'failed')                                    AS FailedCount,
    SUM(o.Status = 'returned')                                  AS ReturnedCount,
    SUM(o.Status IN ('pending','assigned','in_transit'))        AS ActiveCount,
    ROUND(
        SUM(o.Status = 'delivered') * 100.0
        / NULLIF(COUNT(o.OrderID),0)
    , 1)                                                        AS SuccessRatePct,
    FORMAT(COALESCE(SUM(o.DeclaredValueVND),0), 0)              AS TotalValueVND
FROM Customers c
LEFT JOIN Orders o ON c.CustomerID = o.CustomerID
GROUP BY c.CustomerID, c.CustomerName, c.PhoneNumber, c.City
ORDER BY SuccessRatePct ASC;


-- ============================================================
-- USER-DEFINED FUNCTIONS
-- ============================================================

DELIMITER $$

-- UDF 1: Average delivery cost across all completed deliveries
CREATE FUNCTION fn_avg_delivery_cost()
RETURNS DECIMAL(14,2)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE avg_cost DECIMAL(14,2);
    SELECT COALESCE(AVG(sub.total_cost), 0)
    INTO   avg_cost
    FROM (
        SELECT SUM(e.Amount) AS total_cost
        FROM   Deliveries d
        JOIN   Expenses   e ON d.DeliveryID = e.DeliveryID
        WHERE  d.Status = 'completed'
        GROUP  BY d.DeliveryID
    ) sub;
    RETURN avg_cost;
END$$

-- UDF 2: Number of deliveries per vehicle
CREATE FUNCTION fn_deliveries_per_vehicle(p_vehicle_id INT)
RETURNS INT
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE cnt INT;
    SELECT COUNT(*)
    INTO   cnt
    FROM   Deliveries
    WHERE  VehicleID = p_vehicle_id;
    RETURN cnt;
END$$

-- ============================================================
-- UDF 3: Customer delivery success rate (%)
-- Used by vw_customer_order_summary and Customer Intelligence tab
-- ============================================================
CREATE FUNCTION fn_customer_success_rate(p_customer_id INT)
RETURNS DECIMAL(5,1)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE total_orders   INT     DEFAULT 0;
    DECLARE delivered_cnt  INT     DEFAULT 0;
    DECLARE success_rate   DECIMAL(5,1) DEFAULT 0.0;

    SELECT COUNT(*),
           SUM(Status = 'delivered')
    INTO   total_orders, delivered_cnt
    FROM   Orders
    WHERE  CustomerID = p_customer_id;

    IF total_orders = 0 THEN
        RETURN 0.0;
    END IF;

    SET success_rate = ROUND(delivered_cnt * 100.0 / total_orders, 1);
    RETURN success_rate;
END$$

-- ============================================================
-- UDF 4: Customer risk level
-- Returns: 'low' | 'medium' | 'high' | 'critical'
-- Based on: success rate + number of open issues
-- Used by Customer Intelligence tab in streamlit_app.py
-- ============================================================
CREATE FUNCTION fn_customer_risk_level(p_customer_id INT)
RETURNS VARCHAR(10)
DETERMINISTIC
READS SQL DATA
BEGIN
    DECLARE success_rate  DECIMAL(5,1);
    DECLARE open_issues   INT DEFAULT 0;
    DECLARE risk_label    VARCHAR(10) DEFAULT 'low';

    SET success_rate = fn_customer_success_rate(p_customer_id);

    SELECT COUNT(*)
    INTO   open_issues
    FROM   OrderIssues oi
    JOIN   Orders      o  ON oi.OrderID = o.OrderID
    WHERE  o.CustomerID = p_customer_id
      AND  oi.Resolution = 'pending';

    IF    success_rate < 40 OR open_issues >= 3 THEN
        SET risk_label = 'critical';
    ELSEIF success_rate < 60 OR open_issues >= 2 THEN
        SET risk_label = 'high';
    ELSEIF success_rate < 80 OR open_issues >= 1 THEN
        SET risk_label = 'medium';
    ELSE
        SET risk_label = 'low';
    END IF;

    RETURN risk_label;
END$$

DELIMITER ;


-- ============================================================
-- STORED PROCEDURES
-- ============================================================

DELIMITER $$

-- ============================================================
-- SP 1: Assign vehicle to order — create delivery record
-- Wrapped in transaction; uses ROLLBACK on error
-- ============================================================
CREATE PROCEDURE sp_assign_delivery(
    IN  p_order_id      INT,
    IN  p_vehicle_id    INT,
    IN  p_driver_name   VARCHAR(100),
    IN  p_driver_phone  VARCHAR(15),
    IN  p_sched_date    DATE,
    OUT p_delivery_id   INT,
    OUT p_message       VARCHAR(255)
)
sp_assign_delivery: BEGIN
    DECLARE v_order_status  VARCHAR(20);
    DECLARE v_veh_avail     VARCHAR(20);
    DECLARE v_is_fragile    BOOLEAN;
    DECLARE v_can_fragile   BOOLEAN;
    DECLARE v_declared_val  BIGINT;
    DECLARE v_max_value     BIGINT;
    DECLARE v_vehicle_type  VARCHAR(30);
    DECLARE v_allowed_types VARCHAR(100);

    -- All validation BEFORE starting transaction (read-only checks)
    SELECT Status, IsFragile, DeclaredValueVND
    INTO   v_order_status, v_is_fragile, v_declared_val
    FROM   Orders WHERE OrderID = p_order_id;

    IF v_order_status IS NULL THEN
        SET p_message = 'ERROR: OrderID not found';
        SET p_delivery_id = -1;
        LEAVE sp_assign_delivery;
    END IF;

    IF v_order_status != 'pending' THEN
        SET p_message = CONCAT('ERROR: Order status is "', v_order_status, '", must be pending');
        SET p_delivery_id = -1;
        LEAVE sp_assign_delivery;
    END IF;

    SELECT Availability, CanCarryFragile, VehicleType, MaxValueVND
    INTO   v_veh_avail, v_can_fragile, v_vehicle_type, v_max_value
    FROM   Vehicles WHERE VehicleID = p_vehicle_id;

    IF v_veh_avail IS NULL THEN
        SET p_message = 'ERROR: VehicleID not found';
        SET p_delivery_id = -1;
        LEAVE sp_assign_delivery;
    END IF;

    IF v_veh_avail != 'available' THEN
        SET p_message = CONCAT('ERROR: Vehicle is "', v_veh_avail, '", not available');
        SET p_delivery_id = -1;
        LEAVE sp_assign_delivery;
    END IF;

    IF v_is_fragile = TRUE AND v_can_fragile = FALSE THEN
        SET p_message = 'ERROR: This vehicle cannot carry fragile items';
        SET p_delivery_id = -1;
        LEAVE sp_assign_delivery;
    END IF;

    -- [NEW] Check MaxValueVND: vehicle insurance cap must cover declared value
    IF v_max_value IS NOT NULL AND v_declared_val > v_max_value THEN
        SET p_message = CONCAT('ERROR: Order value (',
                               FORMAT(v_declared_val, 0),
                               ' VND) exceeds vehicle max insurable value (',
                               FORMAT(v_max_value, 0), ' VND)');
        SET p_delivery_id = -1;
        LEAVE sp_assign_delivery;
    END IF;

    -- [NEW] Check AllowedVehicleTypes from OrderCategories
    SELECT oc.AllowedVehicleTypes
    INTO   v_allowed_types
    FROM   Orders o
    JOIN   OrderCategories oc ON o.CategoryID = oc.CategoryID
    WHERE  o.OrderID = p_order_id;

    IF v_allowed_types IS NOT NULL
       AND FIND_IN_SET(v_vehicle_type, v_allowed_types) = 0 THEN
        SET p_message = CONCAT('ERROR: Vehicle type "', v_vehicle_type,
                               '" not allowed for this category. Allowed: ',
                               v_allowed_types);
        SET p_delivery_id = -1;
        LEAVE sp_assign_delivery;
    END IF;

    -- All writes wrapped in one ACID transaction
    START TRANSACTION;

        INSERT INTO Deliveries (OrderID, VehicleID, DriverName, DriverPhone, ScheduledDate, Status)
        VALUES (p_order_id, p_vehicle_id, p_driver_name, p_driver_phone, p_sched_date, 'scheduled');

        SET p_delivery_id = LAST_INSERT_ID();

        UPDATE Orders   SET Status       = 'assigned'  WHERE OrderID   = p_order_id;
        UPDATE Vehicles SET Availability = 'in_use'    WHERE VehicleID = p_vehicle_id;

    COMMIT;

    SET p_message = CONCAT('OK: DeliveryID ', p_delivery_id, ' created');
END$$

-- ============================================================
-- SP 2: Record a failed attempt — smart reschedule 
-- Logic:
--   • no_answer / not_home / wrong_address / other → retry
--     (respect CustomerPreferences.PreferredTimeSlot)
--   • refused / damaged_on_arrival               → escalate
--   • attempt >= 3                               → auto-return
-- Uses TRANSACTION to ensure all writes are atomic
-- ============================================================
CREATE PROCEDURE sp_smart_reschedule(
    IN  p_delivery_id      INT,
    IN  p_failure_reason   VARCHAR(50),
    IN  p_notes            TEXT,
    OUT p_status           VARCHAR(20),
    OUT p_message          VARCHAR(255)
)
BEGIN
    DECLARE v_attempt_no    INT     DEFAULT 0;
    DECLARE v_next_attempt  DATETIME;
    DECLARE v_max_attempts  INT     DEFAULT 3;
    DECLARE v_order_id      INT;
    DECLARE v_customer_id   INT;
    DECLARE v_pref_slot     VARCHAR(15) DEFAULT 'anytime';
    DECLARE v_slot_hour     INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_status  = 'ERROR';
        SET p_message = 'Transaction rolled back — database error during reschedule';
    END;

    -- Read current state
    SELECT d.OrderID, o.CustomerID
    INTO   v_order_id, v_customer_id
    FROM   Deliveries d
    JOIN   Orders     o ON d.OrderID = o.OrderID
    WHERE  d.DeliveryID = p_delivery_id;

    SELECT COALESCE(MAX(AttemptNumber), 0)
    INTO   v_attempt_no
    FROM   DeliveryAttempts
    WHERE  DeliveryID = p_delivery_id;
    SET v_attempt_no = v_attempt_no + 1;

    -- Read customer preferred time slot for smart scheduling
    SELECT COALESCE(PreferredTimeSlot, 'anytime')
    INTO   v_pref_slot
    FROM   CustomerPreferences
    WHERE  CustomerID = v_customer_id;

    -- Map slot to starting hour
    SET v_slot_hour = CASE v_pref_slot
        WHEN 'morning'   THEN 8
        WHEN 'afternoon' THEN 13
        WHEN 'evening'   THEN 17
        ELSE                  9   -- anytime → default morning-ish
    END;

    START TRANSACTION;

    -- Insert attempt record
    IF v_attempt_no < v_max_attempts
       AND p_failure_reason NOT IN ('refused','damaged_on_arrival') THEN
        -- Next attempt: next business day at customer's preferred slot
        SET v_next_attempt = DATE_ADD(
            DATE_ADD(CURDATE(), INTERVAL 1 DAY),
            INTERVAL v_slot_hour HOUR
        );
    ELSE
        SET v_next_attempt = NULL;
    END IF;

    INSERT INTO DeliveryAttempts
        (DeliveryID, AttemptNumber, AttemptTime, FailureReason,
         ContactAttempted, Notes, NextAttemptScheduled)
    VALUES
        (p_delivery_id, v_attempt_no, NOW(), p_failure_reason,
         TRUE, p_notes, v_next_attempt);

    -- Add failed-attempt expense
    INSERT INTO Expenses (DeliveryID, ExpenseType, Amount, Description, ExpenseDate)
    VALUES (p_delivery_id, 'failed_attempt', 15000.00,
            CONCAT('Attempt #', v_attempt_no, ': ', p_failure_reason), CURRENT_DATE);

    -- Decision logic
    IF p_failure_reason IN ('refused','damaged_on_arrival') THEN
        -- Escalate immediately — create an issue record
        INSERT INTO OrderIssues (OrderID, DeliveryID, IssueType, ReportedBy, Severity, Description)
        VALUES (v_order_id, p_delivery_id,
                IF(p_failure_reason='damaged_on_arrival','damaged','refused_quality'),
                'driver', 'high',
                CONCAT('Auto-escalated on attempt #', v_attempt_no, ': ', p_failure_reason));

        SET p_status  = 'ESCALATED';
        SET p_message = CONCAT('Issue created — requires manager action. Attempt #', v_attempt_no);

    ELSEIF v_attempt_no >= v_max_attempts THEN
        -- Max attempts reached → mark failed, free vehicle
        UPDATE Deliveries SET Status = 'failed'    WHERE DeliveryID = p_delivery_id;
        UPDATE Orders     SET Status = 'failed'
        WHERE  OrderID = v_order_id;

        -- Free the vehicle (trigger also does this on 'completed', but not 'failed')
        UPDATE Vehicles v
        JOIN   Deliveries d ON v.VehicleID = d.VehicleID
        SET    v.Availability = 'available'
        WHERE  d.DeliveryID = p_delivery_id;

        -- Log rescheduled record showing final failure
        INSERT INTO DeliveryRescheduled
            (OriginalDeliveryID, Reason, OldScheduledDate, NewScheduledDate,
             NewTimeSlot, AutoScheduled, Notes)
        SELECT p_delivery_id, 'other',
               ScheduledDate, CURDATE(), 'anytime', TRUE,
               CONCAT('Max attempts (', v_max_attempts, ') reached — order returned')
        FROM   Deliveries WHERE DeliveryID = p_delivery_id;

        SET p_status  = 'RETURNED';
        SET p_message = CONCAT('Max ', v_max_attempts,
                               ' attempts reached — order marked failed/returned');
    ELSE
        -- Normal retry with smart scheduling
        INSERT INTO DeliveryRescheduled
            (OriginalDeliveryID, Reason, OldScheduledDate, NewScheduledDate,
             NewTimeSlot, AutoScheduled, Notes)
        SELECT p_delivery_id,
               IF(p_failure_reason='not_home','customer_busy','other'),
               ScheduledDate, DATE(v_next_attempt), v_pref_slot, TRUE,
               CONCAT('Auto-rescheduled. Reason: ', p_failure_reason,
                      '. Preferred slot: ', v_pref_slot)
        FROM   Deliveries WHERE DeliveryID = p_delivery_id;

        SET p_status  = 'RESCHEDULED';
        SET p_message = CONCAT('Attempt #', v_attempt_no,
                               ' logged. Next delivery: ',
                               DATE_FORMAT(v_next_attempt, '%d/%m/%Y %H:%i'),
                               ' (', v_pref_slot, ' slot)');
    END IF;

    COMMIT;
END$$

-- ============================================================
-- SP 3: Resolve an order issue — ACID-compliant 
-- are wrapped in one transaction — any failure triggers ROLLBACK
-- ============================================================
CREATE PROCEDURE sp_resolve_issue(
    IN  p_issue_id      INT,
    IN  p_resolution    VARCHAR(50),
    IN  p_notes         TEXT,
    OUT p_status        VARCHAR(20),
    OUT p_message       VARCHAR(255)
)
sp_resolve: BEGIN
    DECLARE v_order_id   INT;
    DECLARE v_severity   VARCHAR(20);
    DECLARE v_deliv_id   INT;

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        SET p_status  = 'ERROR';
        SET p_message = 'Transaction rolled back — issue resolution failed';
    END;

    -- Validate issue exists
    SELECT OrderID, Severity, DeliveryID
    INTO   v_order_id, v_severity, v_deliv_id
    FROM   OrderIssues
    WHERE  IssueID = p_issue_id;

    IF v_order_id IS NULL THEN
        SET p_status  = 'ERROR';
        SET p_message = CONCAT('IssueID ', p_issue_id, ' not found');
        LEAVE sp_resolve;
    END IF;

    START TRANSACTION;

    -- Step 1: Mark issue as resolved
    UPDATE OrderIssues
    SET    Resolution      = p_resolution,
           ResolutionNotes = p_notes,
           ResolvedAt      = NOW()
    WHERE  IssueID = p_issue_id;

    -- Step 2: Update order status based on resolution type
    IF p_resolution IN ('refund', 'resend') THEN
        UPDATE Orders
        SET    Status = 'returned'
        WHERE  OrderID = v_order_id
          AND  Status NOT IN ('delivered','returned');
    END IF;

    -- Step 3: Record compensation expense for high/critical issues
    IF p_resolution = 'refund'
       AND v_severity IN ('high','critical')
       AND v_deliv_id IS NOT NULL THEN
        INSERT INTO Expenses
            (DeliveryID, ExpenseType, Amount, Description, ExpenseDate)
        VALUES
            (v_deliv_id, 'other', 50000.00,
             CONCAT('Boi thuong Issue #', p_issue_id, ' — ', p_resolution),
             CURRENT_DATE);
    END IF;

    COMMIT;

    SET p_status  = 'OK';
    SET p_message = CONCAT('Issue #', p_issue_id,
                           ' resolved as "', p_resolution, '"');
END$$

-- ============================================================
-- SP 4 (NEW): sp_resolve_issue_v2 — ACID-compliant
--   • CHỈ update khi Resolution đang là 'pending' (WHERE lọc cứng).
--   • Dùng ROW_COUNT() để kiểm tra: nếu 0 dòng bị ảnh hưởng
--     (Issue không tồn tại HOẶC đã được giải quyết rồi) → ROLLBACK + lỗi.
--   • EXIT HANDLER FOR SQLEXCEPTION: bất kỳ lỗi hệ thống nào
--     (deadlock, FK violation...) đều tự động ROLLBACK.
-- Tham số IN: p_issue_id, p_resolution, p_resolution_notes
-- ============================================================
CREATE PROCEDURE sp_resolve_issue_v2(
    IN p_issue_id          INT,
    IN p_resolution        VARCHAR(50),
    IN p_resolution_notes  TEXT
)
sp_v2: BEGIN
    -- Khai báo biến cờ để EXIT HANDLER biết có lỗi xảy ra
    DECLARE v_rows_affected INT DEFAULT 0;
    DECLARE v_error_occurred BOOLEAN DEFAULT FALSE;

    -- EXIT HANDLER: bắt mọi lỗi SQL, đặt cờ, rollback
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        SET v_error_occurred = TRUE;
        ROLLBACK;
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'sp_resolve_issue_v2: Transaction rolled back due to a system error.';
    END;

    -- Kiểm tra đầu vào cơ bản trước khi mở transaction
    IF p_resolution NOT IN ('resend','refund','partial_refund',
                            'reinspect','dismissed') THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'sp_resolve_issue_v2: Invalid resolution value.';
        LEAVE sp_v2;
    END IF;

    -- Mở transaction — tất cả write phía dưới là một đơn vị nguyên tử
    START TRANSACTION;

        -- UPDATE chỉ khi Resolution đang là 'pending'
        -- Nếu issue không tồn tại hoặc đã resolve → 0 dòng bị ảnh hưởng
        UPDATE OrderIssues
        SET    Resolution      = p_resolution,
               ResolutionNotes = p_resolution_notes,
               ResolvedAt      = NOW()
        WHERE  IssueID     = p_issue_id
          AND  Resolution  = 'pending';   -- điều kiện bảo vệ idempotency

        -- Kiểm tra kết quả bằng ROW_COUNT()
        SET v_rows_affected = ROW_COUNT();

        IF v_rows_affected = 0 THEN
            -- Không có dòng nào được cập nhật:
            -- Issue không tồn tại, hoặc đã ở trạng thái khác 'pending'
            ROLLBACK;
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT =
                    'sp_resolve_issue_v2: No rows updated. '
                    'IssueID not found or already resolved (not pending).';
            LEAVE sp_v2;
        END IF;

    -- Tất cả thành công → commit vĩnh viễn
    COMMIT;
END$$

-- ============================================================
-- SP 5: Calculate total expenses for a delivery
-- ============================================================
CREATE PROCEDURE sp_get_delivery_cost(
    IN  p_delivery_id   INT,
    OUT p_total         DECIMAL(14,2),
    OUT p_breakdown     TEXT
)
BEGIN
    SELECT COALESCE(SUM(Amount), 0)
    INTO   p_total
    FROM   Expenses
    WHERE  DeliveryID = p_delivery_id;

    SELECT GROUP_CONCAT(
               CONCAT(ExpenseType, ': ', FORMAT(Amount,0), ' VND')
               ORDER BY ExpenseType SEPARATOR ' | '
           )
    INTO   p_breakdown
    FROM   Expenses
    WHERE  DeliveryID = p_delivery_id;
END$$

DELIMITER ;


-- ============================================================
-- TRIGGERS
-- ============================================================

DELIMITER $$

-- ============================================================
-- Trigger set A: IsHighValue auto-flag
-- ============================================================

CREATE TRIGGER trg_order_set_high_value_insert
BEFORE INSERT ON Orders
FOR EACH ROW
BEGIN
    IF NEW.DeclaredValueVND > 5000000 THEN
        SET NEW.IsHighValue = TRUE;
    END IF;
END$$

CREATE TRIGGER trg_order_set_high_value_update
BEFORE UPDATE ON Orders
FOR EACH ROW
BEGIN
    IF NEW.DeclaredValueVND > 5000000 THEN
        SET NEW.IsHighValue = TRUE;
    ELSE
        SET NEW.IsHighValue = FALSE;
    END IF;
END$$

-- ============================================================
-- Trigger set B: Time-constraint validation  
-- Enforces: DeadlineDate must be AFTER OrderDate
-- Without this, Python random could silently insert invalid dates
-- ============================================================

CREATE TRIGGER trg_validate_order_dates_insert
BEFORE INSERT ON Orders
FOR EACH ROW
BEGIN
    IF NEW.DeadlineDate IS NOT NULL
       AND NEW.DeadlineDate <= NEW.OrderDate THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'ERROR: DeadlineDate must be strictly after OrderDate';
    END IF;
END$$

CREATE TRIGGER trg_validate_order_dates_update
BEFORE UPDATE ON Orders
FOR EACH ROW
BEGIN
    IF NEW.DeadlineDate IS NOT NULL
       AND NEW.DeadlineDate <= NEW.OrderDate THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'ERROR: DeadlineDate must be strictly after OrderDate';
    END IF;
END$$

-- ============================================================
-- Trigger set C: ScheduledDate cannot be before OrderDate
-- Tên chính xác: trg_check_delivery_date
-- Logic: Lấy OrderDate từ Orders theo NEW.OrderID,
--        nếu NEW.ScheduledDate < DATE(OrderDate) → SIGNAL lỗi,
--        chặn INSERT để bảo toàn tính toàn vẹn thời gian.
-- ============================================================

CREATE TRIGGER trg_check_delivery_date
BEFORE INSERT ON Deliveries
FOR EACH ROW
BEGIN
    DECLARE v_order_date DATETIME;

    SELECT OrderDate
    INTO   v_order_date
    FROM   Orders
    WHERE  OrderID = NEW.OrderID;

    IF v_order_date IS NOT NULL
       AND NEW.ScheduledDate < DATE(v_order_date) THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT =
                'ERROR: ScheduledDate cannot be before the linked OrderDate';
    END IF;
END$$

-- ============================================================
-- Trigger set D: Delivery completed → update order + free vehicle
-- ============================================================

CREATE TRIGGER trg_delivery_completed
AFTER UPDATE ON Deliveries
FOR EACH ROW
BEGIN
    IF NEW.Status = 'completed' AND OLD.Status != 'completed' THEN
        UPDATE Orders   SET Status       = 'delivered'  WHERE OrderID   = NEW.OrderID;
        UPDATE Vehicles SET Availability = 'available'  WHERE VehicleID = NEW.VehicleID;
    END IF;
END$$

-- ============================================================
-- Trigger set E: Prevent booking same vehicle twice on same date
-- ============================================================

CREATE TRIGGER trg_prevent_double_booking
BEFORE INSERT ON Deliveries
FOR EACH ROW
BEGIN
    DECLARE conflict_count INT;
    SELECT COUNT(*)
    INTO   conflict_count
    FROM   Deliveries
    WHERE  VehicleID     = NEW.VehicleID
      AND  ScheduledDate = NEW.ScheduledDate
      AND  Status NOT IN ('completed','failed','returned');

    IF conflict_count > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'ERROR: Vehicle already assigned on this date';
    END IF;
END$$

DELIMITER ;


-- ============================================================
-- DATABASE ROLES & SECURITY
-- ============================================================

CREATE ROLE IF NOT EXISTS 'delivery_manager_role';
CREATE ROLE IF NOT EXISTS 'dispatcher_role';
CREATE ROLE IF NOT EXISTS 'accountant_role';

-- delivery_manager: full access
GRANT SELECT, INSERT, UPDATE, DELETE ON delivery_db.* TO 'delivery_manager_role';
GRANT EXECUTE ON delivery_db.*                         TO 'delivery_manager_role';

-- dispatcher: manage orders/deliveries/attempts, view customers/vehicles
GRANT SELECT, INSERT, UPDATE ON delivery_db.Orders             TO 'dispatcher_role';
GRANT SELECT, INSERT, UPDATE ON delivery_db.Deliveries         TO 'dispatcher_role';
GRANT SELECT, INSERT, UPDATE ON delivery_db.DeliveryAttempts   TO 'dispatcher_role';
GRANT SELECT, INSERT, UPDATE ON delivery_db.DeliveryRescheduled TO 'dispatcher_role';
GRANT SELECT, INSERT, UPDATE ON delivery_db.OrderIssues        TO 'dispatcher_role';
GRANT SELECT                 ON delivery_db.Vehicles           TO 'dispatcher_role';
GRANT SELECT                 ON delivery_db.Customers          TO 'dispatcher_role';
GRANT SELECT                 ON delivery_db.CustomerPreferences TO 'dispatcher_role';
GRANT SELECT                 ON delivery_db.OrderCategories    TO 'dispatcher_role';
GRANT EXECUTE ON PROCEDURE delivery_db.sp_assign_delivery      TO 'dispatcher_role';
GRANT EXECUTE ON PROCEDURE delivery_db.sp_smart_reschedule     TO 'dispatcher_role';

-- accountant: read expenses and cost views only
GRANT SELECT ON delivery_db.Expenses        TO 'accountant_role';
GRANT SELECT ON delivery_db.Deliveries      TO 'accountant_role';
GRANT SELECT ON delivery_db.Orders          TO 'accountant_role';
GRANT SELECT ON delivery_db.vw_cost_per_order TO 'accountant_role';
GRANT EXECUTE ON PROCEDURE delivery_db.sp_get_delivery_cost TO 'accountant_role';
GRANT EXECUTE ON FUNCTION  delivery_db.fn_avg_delivery_cost TO 'accountant_role';

-- ============================================================
-- END OF SCHEMA
-- ============================================================