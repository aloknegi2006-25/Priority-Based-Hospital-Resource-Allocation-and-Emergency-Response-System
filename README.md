# Priority-Based Hospital Resource Allocation and Emergency Response System

**Team Name:** SysForge
**Academic Focus:** Database Management Systems (DBMS) & Operating Systems (OS)

---

## 1. Project Overview

Hospitals frequently face surge crises where emergency patients arrive simultaneously, competing for finite clinical resources such as ICU beds, general beds, ventilators, and ambulances.

This project implements a multi-tier web application demonstrating core concepts from Database Management Systems and Operating Systems:

- **Operating System Concepts (Application & Database Tier):**
  - **Priority-Ordered Request Processing:** Emergency cases are prioritized according to the Emergency Severity Index (ESI Tiers 1–5). Higher urgency requests are queued ahead of lower urgency requests, with deterministic First-In-First-Out (FIFO) ordering for cases of equal priority.
  - **Finite Resource Lifecycle Management:** Direct tracking and state management (`AVAILABLE`, `ALLOCATED`) of constrained hospital equipment, ensuring resources are assigned, tracked during active care, and released back to the available pool upon completion.
  - **Conflict Prevention & Mutual Exclusion:** Prevention of duplicate or conflicting allocations of the same physical resource via database-level transactional concurrency control.
  > **Technical Clarification (OS vs. DBMS Mechanisms):** Database row locking (`SELECT ... FOR UPDATE`) in MySQL InnoDB provides database-level transactional concurrency control and isolation; it is not an OS kernel-level mutex or semaphore. Similarly, SQL priority ordering simulates priority scheduling principles at the application tier rather than low-level CPU process dispatching.

- **Database Management System Concepts:**
  - **Normalized Relational Design (3NF):** Six normalized tables (`patients`, `staff`, `emergency_cases`, `resources`, `resource_allocations`, `allocation_history`) with primary keys, foreign key constraints, and cascade/restrict rules.
  - **ACID Transactions:** Atomic multi-statement transactions using a centralized context manager (`get_db_transaction()`) guaranteeing consistency and automated rollback on failure.
  - **Indexing for Query Efficiency:** Composite index (`idx_priority_triage`) on `(priority_level, admitted_at, triage_status)` to support low-latency priority queue retrieval.
  - **Parameterized Queries:** Consistent use of parameterized SQL across all endpoints to prevent SQL injection vulnerabilities.
  - **Audit Logging:** An immutable append-only history table (`allocation_history`) recording every grant and release action.

> **Safety Notice:** This system is an academic simulation and tracking tool. It does not perform automated medical diagnosis or clinical prescription. Priority tiers must be assigned or confirmed by medical staff.

---

## 2. Technology Stack

* **Frontend:** HTML5, CSS3, Vanilla JavaScript, Bootstrap 5.3 (via CDN), Jinja2 templates
* **Backend:** Python 3.9+, Flask 2.3+
* **Database:** MySQL 8.0+ (`mysql-connector-python`)
* **Environment:** `python-dotenv` for configuration management
* **Testing:** Python standard `unittest` framework with isolated SQLite test runner

---

## 3. Directory Layout

```
Second phase/
├── app.py                      # Flask application factory and entry point (default: 127.0.0.1:5001)
├── config.py                   # Configuration classes reading from .env with secure defaults
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── .gitignore                  # Git ignore rules
├── README.md                   # Project documentation and setup guide
│
├── database/
│   ├── db.py                   # Centralized connection wrapper, query executor & transaction manager
│   ├── schema.sql              # Normalized 3NF DDL schema with constraints & indexes
│   └── seed.sql                # Safely repeatable development seed script with stable identifiers
│
├── routes/
│   ├── __init__.py             # Route package exports
│   ├── main_routes.py          # Web presentation views, form handlers & operational dashboard
│   ├── patient_routes.py       # Patient intake & priority triage queue REST APIs
│   ├── resource_routes.py      # Resource inventory & status filtering REST APIs
│   └── allocation_routes.py    # Atomic resource allocation & release transactions
│
├── templates/
│   ├── base.html               # Master layout shell with Bootstrap 5 navbar & alert blocks
│   ├── index.html              # Emergency portal home & department quick-links
│   ├── dashboard.html          # Operational dashboard with live metrics & capacity gauges
│   ├── patients.html           # Patient registration form & master directory
│   ├── emergency_cases.html    # Emergency triage intake & live priority queue table
│   ├── resources.html          # Clinical asset inventory matrix with type/status filters
│   └── allocations.html        # Resource allocation form & active lock management
│
├── static/
│   ├── css/
│   │   └── style.css           # Custom styling complementing Bootstrap
│   └── js/
│       └── main.js             # Client-side helpers
│
└── tests/
    ├── __init__.py
    └── test_scaffold.py        # Automated test suite (24 unit tests covering DBMS & OS features)
```

---

## 4. How to Run the Application

### Prerequisites
* Python 3.9 or higher installed
* MySQL Server 8.0+ installed and running (recommended for full live database operation; an isolated SQLite environment is used automatically during unit tests)

### Step 1: Navigate to the Project Directory
```bash
cd "Second phase"
```

### Step 2: Set Up Python Virtual Environment
On macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```
On Windows:
```cmd
python -m venv venv
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the template configuration file:
```bash
cp .env.example .env
```
Edit `.env` with your local MySQL credentials (`DB_USER`, `DB_PASSWORD`, `DB_NAME`, etc.).

### Step 5: Initialize MySQL Schema and Seed Data
Execute the schema and repeatable seed script in MySQL:
```bash
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql
```

### Step 6: Run the Flask Web Application
```bash
python3 app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5001/
```
*(Note: Port 5001 is configured by default to avoid macOS AirPlay Receiver port 5000 conflicts. Host defaults to 127.0.0.1 for local isolation).*

The home page, operational dashboard, emergency triage queue, patient registry, and resource matrices will load live database records immediately.

---

## 5. Running Automated Verification Tests

An automated test suite validates all database operations, concurrency controls, validation constraints, and web routes in an isolated testing environment:

```bash
python3 -m unittest tests/test_scaffold.py -v
```

All 24 automated unit tests execute and confirm:
1. Web presentation routes return `200 OK`.
2. Health check probe `/api/health` returns `200 OK` when connected and `503 Service Unavailable` when disconnected.
3. Patient registration, server-side validation, duplicate National ID rejection (409), future DOB rejection, and anonymous trauma admission work correctly.
4. Emergency triage intake enqueues cases and orders them strictly by clinical urgency (1 to 5) with deterministic FIFO tie-breaking (OS Priority Scheduling).
5. Repeatable demo data seeding using stable identifiers without duplicate cases.
6. Resource inventory API returns assets and filters by type (`BED_ICU`, `VENTILATOR`, etc.) and status (`AVAILABLE`, `ALLOCATED`).
7. Concurrency-controlled resource allocation executes atomically, prevents duplicate allocation conflicts (HTTP 409 Conflict), updates triage states, and logs historical audit trails.
8. Resource release returns assets to `AVAILABLE`, rejects repeated releases (HTTP 400), and records audit history in `allocation_history`.
9. Operational dashboard renders live queue counts, registered patient totals, and dynamic resource capacity gauges.

---

## 6. Project & Academic Focus Matrix

**Team:** SysForge
**Project:** Emergency Case & Resource Allocation System

| Project Module | Primary OS Concept Demonstrated | Primary DBMS Concept Demonstrated |
| :--- | :--- | :--- |
| **Emergency Triage Queue** (`emergency_cases`) | **Priority Scheduling with FIFO Tie-Breaking:** Requests are ordered by urgency tier (1 to 5); equal-urgency cases are ordered by arrival time (FIFO). | **Composite Indexing & Sorting:** Fast index lookup on `(priority_level, admitted_at, triage_status)` for low-latency retrieval. |
| **Resource Inventory** (`resources`) | **Finite Resource Tracking:** Managing finite, reusable system resources with operational states (`AVAILABLE`, `ALLOCATED`). | **Domain Constraints & Filtering:** Schema ENUM status types, boolean flags, and parameterized conditional queries. |
| **Resource Allocation & Release** (`resource_allocations`) | **Mutual Exclusion & Conflict Prevention:** Preventing simultaneous conflicting assignments of a shared physical asset. | **ACID Transactions & Row Locking:** Atomic execution with `SELECT ... FOR UPDATE`, transaction rollback on error, and foreign key referential integrity. |
| **Allocation History** (`allocation_history`) | **Audit Trail & State History:** Logging resource grant and deallocation events for traceability. | **Referential Integrity & Cascades:** Normalized audit logging linked via foreign key constraints. |
| **Patient Registry** (`patients`) | **Intake & Identification:** Distinct intake tracking for identified versus unidentified emergency arrivals. | **Entity Integrity & Unique Constraints:** Unique National ID enforcement with nullable support for trauma cases. |

---

## 7. Phase 2 Completion Status vs. Phase 3 Roadmap

### Implemented in Phase 2 (~40–50% Verified Completion)
* **Normalized 3NF MySQL Database:** Structured DDL schema with foreign key constraints, composite indexes, and safely repeatable seed data (`database/schema.sql`, `database/seed.sql`).
* **Database Connection & Transaction Engine:** Safe connection wrapper with health check probe, parameterized query utility preventing SQL injection, and atomic `get_db_transaction()` context manager supporting transaction rollback on failure (`database/db.py`).
* **Patient Intake & Registry:** Server-side validation (2–150 chars, date parsing, gender restrictions, null national ID handling for trauma victims), duplicate National ID detection, and dynamic rendering (`routes/patient_routes.py`, `templates/patients.html`).
* **Emergency Triage Queue:** Priority 1–5 intake, priority sorting (`priority_level ASC, admitted_at ASC, case_id ASC`), and status transitions (`routes/patient_routes.py`, `templates/emergency_cases.html`).
* **Resource Inventory & Status Matrix:** Live clinical asset matrix with status and resource type filtering (`routes/resource_routes.py`, `templates/resources.html`).
* **Concurrency-Controlled Asset Allocation & Release:** Atomic transactions with row-level locks (`SELECT ... FOR UPDATE`), conflict detection preventing double allocation (HTTP 409 Conflict), case advancement (`QUEUED` $\rightarrow$ `IN_TREATMENT`), resource release, and immutable audit logging in `allocation_history` (`routes/allocation_routes.py`, `templates/allocations.html`).
* **Live Operational Dashboard:** Real-time summary cards, dynamic triage queue preview, registered patient/asset totals, and percentage-based capacity utilization bars (`routes/main_routes.py`, `templates/dashboard.html`).
* **Automated Test Suite:** 24 comprehensive unit tests verifying presentation, data integrity, security defaults, repeatable seeding, and OS/DBMS semantics (`tests/test_scaffold.py`).

### Deferred to Phase 3 (Future Roadmap)
* Dynamic aging algorithm to adjust priority scores and prevent starvation of low-urgency patients waiting past maximum thresholds.
* High-priority preemption protocol (safely revoking or reassigning non-critical resources when Level 1 resuscitation arrives).
* Staff authentication and role-based access control (RBAC).
* Real-time WebSocket or Server-Sent Events (SSE) for automated client push updates without manual page refreshes.
