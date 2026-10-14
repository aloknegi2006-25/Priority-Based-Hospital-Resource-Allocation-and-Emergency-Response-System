# Priority-Based Hospital Resource Allocation and Emergency Response System

**Team Name:** SysForge  
**Academic Focus:** Database Management Systems (DBMS) & Operating Systems (OS)  
**Milestone:** PBL Phase 2 (Scaffolding & Architectural Foundation)  

---

## 1. Project Overview

Hospitals frequently face surge crises where critical emergency patients arrive simultaneously, competing for finite clinical resources such as ICU beds, ventilators, trauma specialists, and ambulances. 

This project implements a multi-tier **web application** that connects:
- **Operating System Concepts:** Priority-based preemptive scheduling, aging algorithms to prevent patient starvation, critical section mutual exclusion on finite medical resources, and deadlock prevention using strict resource acquisition ordering.
- **Database Management System Concepts:** Third Normal Form (3NF) relational design, entity integrity, referential constraints, indexing for low-latency triage queues, and atomic ACID transactions with row-level locking (`SELECT ... FOR UPDATE`).

> **Safety Notice:** This system is an academic simulation and tracking tool. It does not perform automated medical diagnosis or clinical prescription. Priority tiers must be assigned or confirmed by medical staff.

---

## 2. Technology Stack

* **Frontend:** HTML5, CSS3, Vanilla JavaScript, Bootstrap 5.3 (via CDN)
* **Backend:** Python 3.9+, Flask 2.3+
* **Database:** MySQL 8.0+ (`mysql-connector-python`)
* **Environment:** `python-dotenv` for configuration management

---

## 3. Directory Layout

```
Second phase/
├── app.py                      # Flask application factory and entry point
├── config.py                   # Configuration classes reading from .env
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── .gitignore                  # Git ignore rules
├── README.md                   # Project documentation and setup guide
│
├── database/
│   ├── db.py                   # Safe MySQL connection wrapper & health check
│   ├── schema.sql              # Normalized 3NF DDL schema with constraints & indexes
│   └── seed.sql                # Development sample data (resources, staff, test cases)
│
├── routes/
│   ├── __init__.py             # Route package exports
│   ├── main_routes.py          # Web presentation views (serves HTML templates)
│   ├── patient_routes.py       # Patient and emergency case API stubs (HTTP 501)
│   ├── resource_routes.py      # Resource inventory API stubs (HTTP 501)
│   └── allocation_routes.py    # Resource allocation and release API stubs (HTTP 501)
│
├── templates/
│   ├── base.html               # Master layout shell with Bootstrap 5 navbar
│   ├── index.html              # Project overview, theory concepts, and team roles
│   ├── dashboard.html          # Operational dashboard placeholder
│   ├── patients.html           # Patient intake form & master directory placeholder
│   ├── emergency_cases.html    # Emergency priority queue & triage intake placeholder
│   ├── resources.html          # Clinical asset inventory matrix placeholder
│   └── allocations.html        # Active allocations & mutual exclusion lock placeholder
│
├── static/
│   ├── css/
│   │   └── style.css           # Custom styling complementing Bootstrap
│   └── js/
│       └── main.js             # Client-side helpers
│
└── tests/
    ├── __init__.py
    └── test_scaffold.py        # Automated scaffold integrity and route verification tests
```

---

## 4. How to Run the Application

### Prerequisites
* Python 3.9 or higher installed
* MySQL Server 8.0+ installed and running (optional for initial offline template review; required for Phase 3 database queries)

### Step 1: Clone / Navigate to the Directory
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

### Step 3: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the template configuration file:
```bash
cp .env.example .env
```
*(Optional for Phase 2: If MySQL is installed locally, edit `.env` with your MySQL `root` username and password).*

### Step 5: (Optional) Initialize MySQL Schema
If you have MySQL running locally and wish to inspect tables:
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
http://127.0.0.1:5000/
```
The home page, dashboard, emergency triage queue, patient registry, and resource matrices will load immediately.

---

## 5. Running Automated Verification Tests

To verify that all template routes and API stubs are functioning properly:
```bash
python3 -m unittest tests/test_scaffold.py
```
All tests will execute and confirm:
1. Web pages return `200 OK`.
2. Health check probe `/api/health` returns `200 OK`.
3. Unimplemented API endpoints return `501 Not Implemented` with explicit scaffold status.

---

## 6. Team Roles & Academic Defense Matrix

| Team Member | Official Title | Primary OS Concept | Primary DBMS Concept |
| :--- | :--- | :--- | :--- |
| **Apoorv Barthwal** *(Lead)* | System Lead & Priority Scheduling Architect | **Priority Scheduling & Aging:** Multi-level priority queues with preemption; aging algorithm preventing starvation of low-urgency patients. | **Composite Indexing:** Fast index lookup on `(priority_level, admitted_at)` for real-time queue ordering. |
| **Alok Negi** | Concurrency, Deadlock & Data Layer Architect | **Critical Section & Deadlocks:** Mutual exclusion on shared resources (`SELECT ... FOR UPDATE`), race condition elimination, and deadlock avoidance via resource ordering. | **Relational 3NF & ACID Transactions:** Normalization, referential integrity constraints, and isolated transactional operations. |
| **Akshit Chauhan** | Resource Allocation & Lifecycle Engine | **Resource Allocation Graph (RAG) & Safe States:** Dynamic state transitions (`AVAILABLE`, `ALLOCATED`, `RELEASED`) and capacity reservation. | **Referential Integrity & Audit Logging:** Foreign key cascades and immutable history tracking in `allocation_history`. |
| **Ishan Mathpal** | UI & Process Dispatcher Lead | **Process State Transitions & Dispatch Latency:** Visualizing patients through process states (`READY` $\rightarrow$ `RUNNING` $\rightarrow$ `TERMINATED/DISCHARGED`). | **Relational Form Mapping:** Client data validation ensuring compliance with database column types and constraints. |

---

## 7. Current Scaffold Status vs. Phase 3 Roadmap

### Scaffolded in Phase 2 (Completed Foundation)
* Complete directory architecture and configuration setup.
* Normalized 3NF MySQL schema with foreign keys, constraints, and indexes.
* Comprehensive seed script with realistic hospital assets and triage records.
* Responsive multi-page web application UI using HTML5, CSS3, Vanilla JS, and Bootstrap 5.
* Clean Flask application factory with modular route blueprints.
* Explicit API route stubs returning HTTP 501 (Not Implemented).
* Automated unit test suite verifying scaffold integrity.

### Deferred to Phase 3 (Business Logic & Integration)
* Live MySQL database connection pool and CRUD queries.
* Algorithmic priority triage scoring and preemption engine.
* Concurrency-safe atomic resource allocation transactions with row-level locks.
* Dynamic starvation-prevention aging scheduler.
* Real-time WebSocket or polling updates for live queue refreshes.
