# Delivery Service Management System

A database-driven system for managing end-to-end delivery operations, built as Project 10 for the Introduction to Database Systems course at the National Economics University (DATCOM Lab, NEU College of Technology).

The system covers the complete delivery lifecycle: customer management, order classification, vehicle and driver assignment, failed-attempt handling with smart rescheduling, expense tracking, and performance reporting — backed by a fully normalized MySQL 8.0 database and a Streamlit web interface.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [Default Login Credentials](#default-login-credentials)
- [Database Schema](#database-schema)
  - [Tables](#tables)
  - [Views](#views)
  - [Stored Procedures](#stored-procedures)
  - [User-Defined Functions](#user-defined-functions)
  - [Triggers](#triggers)
- [Roles and Access Control](#roles-and-access-control)
- [Backup and Restore](#backup-and-restore)
- [Project Structure](#project-structure)
- [References](#references)

---

## Architecture Overview

### Database Layer (MySQL 8.0+)

- 12 normalized tables with enforced foreign key constraints
- 7 views for dashboard panels and reporting
- 5 stored procedures wrapping critical write paths in ACID transactions
- 4 user-defined functions for aggregated analytics
- 7 triggers for data integrity, automation, and business rule enforcement
- 11 single-column indexes and 6 composite indexes targeting the most frequent query patterns
- 3 MySQL roles for database-level access control

### Application Layer (Python 3.10 / Streamlit)

- Browser-based GUI with 9 functional pages routed by sidebar navigation
- bcrypt password hashing at cost factor 12; brute-force protection via account lockout after 5 failed attempts
- `MySQLConnectionPool` with a pool size of 5 for efficient connection reuse
- Role-based permission enforcement at the UI layer via `ROLE_PERMS` in `streamlit_app.py`
- Rotating file logging separated into three streams: application events, database queries, and audit trail
- Automated database backup and restore via `mysqldump`

---

## Key Features

### Failed-Attempt Handling and Smart Rescheduling

The `DeliveryAttempts` table records every failed delivery attempt with a typed reason code (`no_answer`, `not_home`, `refused`, `wrong_address`, `damaged_on_arrival`, `other`). The stored procedure `sp_smart_reschedule` determines the next action:

- For retryable failures (`no_answer`, `not_home`, `wrong_address`, `other`): the procedure reads the recipient's `PreferredTimeSlot` from `CustomerPreferences` and schedules the next attempt at the customer's preferred hour on the following business day.
- For escalation failures (`refused`, `damaged_on_arrival`): an `OrderIssues` record is created automatically and flagged for manager review.
- After 3 attempts: the order is marked `failed`, the vehicle is freed, and a rescheduling log entry is written.

### Order Classification and Special Handling

Orders are classified across five categories defined in the `OrderCategories` table:

| Category | SLA (hours) | Signature | Insurance | Allowed Vehicles |
|---|---|---|---|---|
| `standard` | 48 | No | No | All |
| `fragile` | 36 | Yes | No | Van, Truck, Refrigerated |
| `high_value` | 24 | Yes | Yes | Van, Truck |
| `fragile_high_value` | 12 | Yes | Yes | Van, Truck |
| `refrigerated` | 12 | No | No | Refrigerated Truck only |

The `IsFragile` and `IsHighValue` flags drive validation inside `sp_assign_delivery`, which rejects vehicle assignments that violate the category's `AllowedVehicleTypes` or the vehicle's `CanCarryFragile` flag. The `IsHighValue` flag is set automatically by trigger when `DeclaredValueVND` exceeds 5,000,000 VND.

### Security Model

- Passwords are stored exclusively as bcrypt hashes. The `auth.py` module's `AuthManager` class handles login, lockout, and password change flows. Plain-text passwords are never persisted or logged.
- The Python application connects using the `app_service` MySQL account, which holds only `SELECT`, `INSERT`, `UPDATE`, `DELETE`, and `EXECUTE` privileges on `delivery_db`.
- Three additional MySQL accounts (`dm_user`, `dispatcher_user`, `accountant_user`) are granted their respective roles and can be used for direct database access with appropriate privilege segregation.
- All authentication events — successful logins, failures, lockouts, logouts, and password changes — are written to `logs/audit.log` via a dedicated `audit_logger`.

### Customer Intelligence

The `vw_customer_order_summary` view and the `fn_customer_risk_level` UDF classify customers by delivery success rate and count of unresolved issues:

| Risk Level | Condition |
|---|---|
| `critical` | Success rate < 40% OR open issues >= 3 |
| `high` | Success rate < 60% OR open issues >= 2 |
| `medium` | Success rate < 80% OR open issues >= 1 |
| `low` | All other cases |

---

## Prerequisites

| Dependency | Minimum Version | Purpose |
|---|---|---|
| MySQL Server | 8.0 | Database engine |
| Python | 3.10 | Application runtime |
| streamlit | 1.35 | Web UI framework |
| mysql-connector-python | 9.0 | Database driver and connection pooling |
| bcrypt | 4.1 | Password hashing |
| pandas | 2.2 | Data manipulation and SQL result handling |
| plotly | 5.20 | Interactive charts |
| Faker | 25.0 | Sample data generation |

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/delivery-management-system.git
cd delivery-management-system
```

### 2. Create and activate a Python virtual environment

On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

On macOS/Linux:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize the database

Connect to MySQL as root and execute the schema script. This script creates the `delivery_db` database, all 12 tables, indexes, views, stored procedures, user-defined functions, triggers, and database roles.

```bash
mysql -u root -p < database/schema.sql
```

### 5. Create MySQL application users

```bash
mysql -u root -p < database/create_mysql_users.sql
```

This creates four accounts (`dm_user`, `dispatcher_user`, `accountant_user`, `app_service`) and assigns their respective roles. The `app_service` account is used by the Python application.

### 6. Generate sample data

```bash
python scripts/generate_data.py
```

This inserts approximately 15 rows per table using realistic Vietnamese locale data generated by Faker. On completion it runs a self-test that validates all views, UDFs, and the date-validation trigger.

> **Note:** `generate_data.py` uses the MySQL `root` account because it requires `TRUNCATE` and `SET foreign_key_checks = 0` privileges that the `app_service` account does not hold. Update the `DB_PASSWORD` field in `scripts/generate_data.py` to match your local root password before running.

---

## Configuration

### Database connection — `db_config.py`

`db_config.py` exports two configuration dictionaries:

- `DB_CONFIG` — plain connection parameters used by `mysql.connector.connect()` in `auth.py`. Does not include pool keys.
- `DB_POOL_CONFIG` — extends `DB_CONFIG` with `pool_name`, `pool_size`, and `pool_reset_session` for use with `MySQLConnectionPool`.

Update the `password` field to match the `app_service` account password you set in step 5.

```python
DB_CONFIG = {
    "host":     "localhost",
    "port":     3306,
    "user":     "app_service",
    "password": "AppService_Pass@2024",   # change if you used a different password
    "database": "delivery_db",
    ...
}
```

### Application connection — `streamlit_app.py`

`streamlit_app.py` defines its own inline `DB_CONFIG` that includes `pool_name` and `pool_size` for the connection pool. Update the `password` field here as well if you changed the `app_service` password.

### Backup credentials — `scripts/backup.py`

`backup.py` connects as the `root` account to run `mysqldump`. Update `DB_PASSWORD` at the top of the file to match your MySQL root password.

### Logs

`logger.py` creates a `logs/` directory at the project root on first run. Three rotating log files are maintained:

| File | Contents |
|---|---|
| `logs/app.log` | General application events |
| `logs/db.log` | Database query execution and timing |
| `logs/audit.log` | Login, logout, failed login, and password change events |

Each file rotates at 5 MB with 5 backup copies retained.

---

## Running the Application

```bash
streamlit run streamlit_app.py
```

Open a browser at `http://localhost:8501`.

---

## Default Login Credentials

These accounts are created by `scripts/generate_data.py`. Change passwords after initial setup.

| Username | Password | Role |
|---|---|---|
| `admin` | `Admin@123` | Delivery Manager — full access |
| `dispatcher1` | `Dispatch@1` | Dispatcher |
| `dispatcher2` | `Dispatch@2` | Dispatcher |
| `accountant1` | `Account@1` | Accountant |
| `accountant2` | `Account@2` | Accountant |

---

## Database Schema

### Tables

| Table | Description |
|---|---|
| `Users` | System accounts. Passwords stored as bcrypt hashes. |
| `OrderCategories` | Classification rules: SLA hours, surcharge rate, required vehicle types, signature and insurance flags. |
| `Customers` | Customer profiles: name, phone, email, full address (ward, district, city), delivery notes. |
| `CustomerPreferences` | Per-customer delivery preferences: preferred time slot, blackout window, contact method, max daily attempts. |
| `Vehicles` | Fleet registry: type, license plate, availability status, weight capacity, max insurable value, fragile-carry flag. |
| `Orders` | Delivery orders: declared value, weight, `IsFragile`, `IsHighValue`, recipient contact, deadline. |
| `Deliveries` | Delivery assignments: vehicle, driver, scheduled and actual dates, status. |
| `DeliveryAttempts` | Per-attempt failure log: reason code, contact attempted flag, next scheduled attempt. |
| `DeliveryRescheduled` | Rescheduling history: old and new dates, time slot, whether auto-scheduled by the system. |
| `OrderIssues` | Quality and damage issue tracker: type, severity, resolution status, resolution notes. |
| `DeliveryRatings` | Post-delivery ratings across three dimensions (package condition, driver service, timeliness). Average score is a generated stored column. |
| `Expenses` | Per-delivery cost records: fuel, toll, handling, insurance, failed-attempt surcharge, other. |

### Views

| View | Purpose |
|---|---|
| `vw_current_schedule` | All deliveries in `scheduled` or `in_progress` status with full order, vehicle, and category details. |
| `vw_cost_per_order` | Total and count of expenses aggregated per order; includes `IsFragile` and `IsHighValue` flags for filtering. |
| `vw_outstanding_orders` | Orders in `pending` or `assigned` status with `HoursRemaining` computed from current time to deadline. |
| `vw_available_vehicles` | Vehicles where `Availability = 'available'`; includes weight capacity and fragile-carry capability. |
| `vw_failed_attempts_summary` | Failed deliveries with attempt count, last failure reason, and next scheduled attempt time. |
| `vw_at_risk_deliveries` | Orders flagged as at-risk if they have 2+ failed attempts, deadline within 6 hours, or both `IsFragile` and `IsHighValue` set. Risk level is `critical`, `high`, or `medium`. |
| `vw_customer_order_summary` | Per-customer aggregation of total orders, delivered count, failed count, success rate, and total declared value. |

### Stored Procedures

| Procedure | Description |
|---|---|
| `sp_assign_delivery(order_id, vehicle_id, driver_name, driver_phone, sched_date, OUT delivery_id, OUT message)` | Validates order status (`pending`), vehicle availability, and fragile-carry compatibility. Creates the `Deliveries` record, sets the order to `assigned` and the vehicle to `in_use`. All writes are in a single ACID transaction. |
| `sp_smart_reschedule(delivery_id, failure_reason, notes, OUT status, OUT message)` | Records a failed attempt, appends a `failed_attempt` expense entry, and applies decision logic: retry with customer-preferred slot, escalate to `OrderIssues`, or mark as returned after 3 attempts. |
| `sp_resolve_issue(issue_id, resolution, notes, OUT status, OUT message)` | Marks an issue resolved, optionally updates the parent order to `returned`, and inserts a compensation expense for high/critical refund resolutions. |
| `sp_resolve_issue_v2(issue_id, resolution, resolution_notes)` | Idempotent variant. Updates only when the current `Resolution` is `pending`; uses `ROW_COUNT()` to detect stale or missing records and signals a descriptive error. |
| `sp_get_delivery_cost(delivery_id, OUT total, OUT breakdown)` | Returns total expense and a pipe-delimited breakdown string (e.g. `fuel: 80,000 VND | toll: 20,000 VND`). |

### User-Defined Functions

| Function | Returns | Description |
|---|---|---|
| `fn_avg_delivery_cost()` | `DECIMAL(14,2)` | Average total expense per completed delivery across the entire system. |
| `fn_deliveries_per_vehicle(vehicle_id INT)` | `INT` | Total delivery count for a given vehicle ID. |
| `fn_customer_success_rate(customer_id INT)` | `DECIMAL(5,1)` | Percentage of orders with status `delivered` for a given customer. |
| `fn_customer_risk_level(customer_id INT)` | `VARCHAR(10)` | Returns `low`, `medium`, `high`, or `critical` based on success rate and count of pending issues. |

### Triggers

| Trigger | Table | Event | Description |
|---|---|---|---|
| `trg_order_set_high_value_insert` | `Orders` | BEFORE INSERT | Sets `IsHighValue = TRUE` when `DeclaredValueVND > 5,000,000`. |
| `trg_order_set_high_value_update` | `Orders` | BEFORE UPDATE | Updates `IsHighValue` on every value change. |
| `trg_validate_order_dates_insert` | `Orders` | BEFORE INSERT | Signals error if `DeadlineDate <= OrderDate`. |
| `trg_validate_order_dates_update` | `Orders` | BEFORE UPDATE | Signals error if `DeadlineDate <= OrderDate` on update. |
| `trg_check_delivery_date` | `Deliveries` | BEFORE INSERT | Signals error if `ScheduledDate` is earlier than the linked order's `OrderDate`. |
| `trg_delivery_completed` | `Deliveries` | AFTER UPDATE | On status change to `completed`: sets order to `delivered` and vehicle to `available`. |
| `trg_prevent_double_booking` | `Deliveries` | BEFORE INSERT | Blocks insertion if the same vehicle is already assigned to a non-terminal delivery on the same date. |

---

## Roles and Access Control

Three MySQL database roles are defined in `schema.sql` and assigned to user accounts in `create_mysql_users.sql`. The Streamlit application enforces the same boundaries at the UI layer.

| Role | Database Privileges | UI Pages |
|---|---|---|
| `delivery_manager_role` | Full `SELECT`, `INSERT`, `UPDATE`, `DELETE` on all tables; `EXECUTE` on all procedures and functions. | Dashboard, Customers, Orders, Deliveries, Vehicles, Expenses, Reports, Issues, Audit Log |
| `dispatcher_role` | `SELECT`/`INSERT`/`UPDATE` on Orders, Deliveries, Attempts, Rescheduled, Issues; `SELECT` on Vehicles, Customers, Preferences, Categories; `EXECUTE` on assign and reschedule procedures. | Customers, Orders, Deliveries, Vehicles, Issues |
| `accountant_role` | `SELECT` on Expenses, Deliveries, Orders, and `vw_cost_per_order`; `EXECUTE` on `sp_get_delivery_cost` and `fn_avg_delivery_cost`. | Expenses, Reports |

The `app_service` account holds `SELECT`, `INSERT`, `UPDATE`, `DELETE`, and `EXECUTE` on all objects in `delivery_db`. It does not use a role; its privileges are granted directly.

---

## Backup and Restore

`scripts/backup.py` wraps `mysqldump` with the `--single-transaction`, `--routines`, `--triggers`, and `--events` flags to produce a consistent, fully restorable snapshot. The output is gzip-compressed. Backups older than 7 days are purged automatically.

```bash
# Create a new backup (saved to backups/ at project root)
python scripts/backup.py

# List existing backup files
python scripts/backup.py --list

# Restore from a specific backup file
python scripts/backup.py --restore backups/delivery_db_YYYYMMDD_HHMMSS.sql.gz

# Override the retention period
python scripts/backup.py --keep-days 14
```

---

## Project Structure

```
delivery-management-system/
|
|-- README.md                        Project documentation
|-- .gitignore                       Git ignore rules
|-- requirements.txt                 Python dependency list
|-- LICENSE                          MIT License
|
|-- streamlit_app.py                 Main application entry point (run with streamlit run)
|-- auth.py                          AuthManager: bcrypt login, lockout, session, password change
|-- db_config.py                     DB_CONFIG and DB_POOL_CONFIG; Tables, Views, Procedures, Functions constants
|-- logger.py                        Rotating file log setup: app_logger, db_logger, audit_logger
|
|-- database/
|   |-- schema.sql                   Full DDL: 12 tables, indexes, 7 views, 5 SPs, 4 UDFs, 7 triggers, 3 roles
|   |-- create_mysql_users.sql       MySQL user accounts and role grants
|   `-- optimize.sql                 EXPLAIN-based query optimization analysis for all major queries
|
|-- scripts/
|   |-- generate_data.py             Faker-based sample data generator (requires MySQL root)
|   `-- backup.py                    mysqldump backup, gzip compression, retention management, restore
|
`-- docs/
    `-- ERD.png                      Entity-relationship diagram (12 entities)
    `-- ERDRelationalSchema.png      Relational schema diagram
```

---

## References

- MySQL 8.0 Reference Manual. https://dev.mysql.com/doc/refman/8.0/en/
- Streamlit Documentation. https://docs.streamlit.io/
- mysql-connector-python Developer Guide. https://dev.mysql.com/doc/connector-python/en/
- bcrypt Python library. https://pypi.org/project/bcrypt/
- Faker Documentation. https://faker.readthedocs.io/en/master/
- plotly Python Graphing Library. https://plotly.com/python/
- pandas Documentation. https://pandas.pydata.org/docs/
- Project Assignment: Project 10 — Delivery Service Management System. DATCOM Lab, NEU College of Technology, National Economics University. Email: hung.tran@neu.edu.vn
