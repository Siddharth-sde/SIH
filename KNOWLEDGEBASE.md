# National Unified Material Master Platform — Master Knowledgebase

> **Smart India Hackathon (SIH 2026)**  
> **Topic:** AI-Driven Material Catalog Harmonization, Deduplication & Common National Material Code (CNMC) Generation for Indian Central Public Sector Enterprises (CPSEs).  
> **Repository:** `https://github.com/Siddharth-sde/SIH.git`  
> **Target Host:** Fedora Linux (`klassje@revachol`) with Podman Rootless & NVIDIA RTX 3050.

---

## 1. Executive Summary & Problem Statement

### 1.1 The Challenge
Indian CPSEs (such as **BHEL, CIL, CPCL, NTPC, SAIL**) procure hundreds of thousands of industrial items annually. Historically, each enterprise created its own fragmented, proprietary catalog systems:
- An identical SKF bearing or ASME flange is coded under 5 different part numbers, inconsistent acronyms (`CS`, `C.S.`, `Carbon Steel`), and conflicting units of measure (`NOS`, `PCS`, `SET`).
- Redundant inventory builds up across plants while procurement teams miss massive bulk volume discounts.
- Previous attempts at catalog cleanup failed due to manual overhead, inconsistent data entry, and ambiguous supplier descriptions.

### 1.2 The Solution
The **National Unified Material Master Platform** is an end-to-end AI-powered system that:
1. **Normalizes** messy industrial text (UOM canonicalization, acronym expansion, dimension parsing).
2. **Extracts structured engineering attributes** (materials, pressure ratings, bore sizes, electrical specs).
3. **Classifies** items into a 10-category national industrial taxonomy using high-dimensional embeddings + LLM verification.
4. **Deduplicates & Mints CNMC (Common National Material Code)** identifiers with hard attribute conflict defense.
5. **Provides financial governance** dashboards, demand aggregation savings analytics, and human-in-the-loop review workflows.

### 1.3 Key Benchmark Numbers (Current Dataset: 50,000 Items)
- **Total Materials Processed:** 50,000 items across 5 CPSEs.
- **Unique CNMC Clusters Minted:** 1,517 golden national codes.
- **Duplicates Rationalized:** 48,483 items (**96.97% catalog rationalization rate**).
- **Annual Procurement Spend:** ₹258,998 Crore (~₹259.0K Cr).
- **Demand Aggregation Savings (10% bulk procurement):** **₹25,899.88 Crore**.
- **Locked Inventory Value:** ₹80,642 Crore (~₹80.6K Cr).
- **Inventory Holding Cost Reduction (15% rationalization):** **₹12,096.30 Crore**.
- **Total Combined Fiscal Value:** **₹37,996+ Crore**.

---

## 2. Architecture & Data Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│               FRONTEND UI (React 19 + Vite 8 + Recharts)               │
│  Dashboard | Batch Upload | Material Master | Clusters | AI Match      │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │ :8000                          │ :8001
                    ▼                                ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────┐
│        BACKEND API GATEWAY           │  │   ML HARMONIZATION SERVICE   │
│  - FastAPI Gateway                   │  │  - FastAPI Microservice      │
│  - SQLite (materials, audit_logs)    │  │  - 4-Stage AI Pipeline       │
│  - Cold-Start Dataset Seeding        │  │  - 1,517 Golden Index Cache  │
│  - Governance Action Handlers        │  │  - PyTest Automated Suite    │
│  - ML Proxy Bridge                   │  │    (44/44 passing)           │
└───────────────────┬──────────────────┘  └──────────────┬───────────────┘
                    │                                    │ :11434
                    │ HTTP Proxy                         ▼
                    └───────────────────────────► ┌──────────────────────┐
                                                  │   OLLAMA CONTAINER   │
                                                  │   qwen2.5:3b         │
                                                  │   (NVIDIA GPU)       │
                                                  └──────────────────────┘
```

---

## 3. Component Deep Dive

### 3.1 ML Harmonization Microservice (`ML/`)
Built with FastAPI, NumPy, Pandas, Scikit-learn, Sentence-Transformers, and Ollama. Runs on port `8001`.

#### Stage 1: Preprocessor (`src/preprocessor.py`)
- **Cleaning & Lowercasing:** Removes noise, null bytes, special formatting characters, and redundant punctuation.
- **Acronym Expansion:** 50+ domain expansions (`CS` → `carbon steel`, `SS316` → `stainless steel 316`, `WNRF` → `weld neck raised face`, `DGBB` → `deep groove ball bearing`).
- **UOM Canonicalization:** Normalizes units into standard uppercase (`NOS`, `MTR`, `KG`, `LTR`, `SET`, `PAIR`, `PKT`, `ROLL`).
- **UOM Conflict Detection:** Rejects matches across incompatible physical dimensions (e.g. Length `MTR` vs Count `NOS`).
- **Dimension Normalization:** Identifies 3D dimensions (`25x52x15 mm`), 2D dimensions (`100x50 mm`), and thread diameters (`M16x50`).

#### Stage 2: Attribute Extractor (`src/attribute_extractor.py`)
Extracts engineering parameters from unstructured text:
- **Mechanical:** Nominal bore (`50 NB`, `2 inch`), Pressure class (`150#`, `300#`, `600#`, `PN16`), End connection (`flanged`, `threaded`, `socket weld`).
- **Bearings:** Part numbers (`6205`, `22220`), Clearance (`C3`, `C4`), Seal types (`2RS`, `ZZ`), ISO dimensions (`ID x OD x Width`).
- **Electrical:** Voltage (`1.1 kV`, `11 kV`, `415 V`), Power (`15 kW`, `20 HP`), Core configuration (`3.5C x 120 sqmm`, `4C x 16 sqmm`), Conductor (`copper`, `aluminium`).

#### Stage 3: Dual-Layer Taxonomy Classifier (`src/classifier.py`)
Classifies materials into 10 industrial categories:
1. `Bearings & Spares`
2. `Pipes, Tubes & Fittings`
3. `Valves & Actuators`
4. `Electrical Equipment & Switchgear`
5. `Fasteners, Gaskets & Seals`
6. `Structural Steel & Raw Materials`
7. `Pumps, Compressors & Turbines`
8. `Instrumentation & Automation`
9. `Tools, Hardware & Consumables`
10. `Safety, PPE & General Spares`

- **Layer 1 (Vector Similarity):** Computes normalized cosine similarity of the item's text against a matrix of 67+ high-signal anchor exemplars using `all-MiniLM-L6-v2` (384-dimensional embeddings).
- **Layer 2 (LLM Fallback):** For items with confidence < 0.70 or borderline multi-class scores, invokes `qwen2.5:3b` via Ollama to determine taxonomy with strict JSON output.

#### Stage 4: Deduplication Matcher (`src/matcher.py`)
- **Hard Attribute Rejection:** Immediately rejects candidate pairs if critical attributes conflict:
  * Incompatible pressure class (`150#` vs `300#`).
  * Incompatible material metallurgy (`carbon steel` vs `stainless steel`).
  * Incompatible conductor (`copper` vs `aluminium`).
- **ISO Bearing Crosswalk:** Maps generic dimension descriptions (e.g. `25x52x15 mm`) directly to standard OEM models (e.g. `6205-2RSH`), allowing OEM-to-generic rationalization.
- **Scoring Engine:** Blends token token_set_ratio, character n-gram similarity, and embedding similarity. Pairs above threshold (0.82) are clustered into common CNMC pools.
- **CNMC Identifier Minting:** Format: `NMC-{SECTOR_CODE}-{CATEGORY_CODE}-{CLUSTER_ID}` (e.g., `NMC-OG-BRG-0001`, `NMC-MN-VLV-0004`).

---

### 3.2 Backend Gateway (`Backend/main.py` & `main.py`)
Built with FastAPI and SQLAlchemy. Runs on port `8000`.

- **Dual Schema Support:** Tables `materials` and `material_master` are fully aligned.
- **Audit Logging:** Every administrative action (`APPROVE`, `REJECT`) creates an immutable row in `audit_logs`.
- **Dynamic File Ingestion:** Supports CSV, XLSX, and PDF (via `pdfplumber`).
- **Universal Column Mapping:** Heuristic `ALIASES` dictionary maps diverse CPSE column names (`item_code`, `mat_no`, `desc`, `short_text`, `price`, `rate`, `stock_qty`, etc.) into canonical fields.
- **Cold-Start Auto-Seeding:** Discovers candidate dataset files on first startup (`cpse_material_master_all.csv`, `material_master_input_50000(1).csv`, etc.) and hydrates SQLite automatically.
- **ML Proxy Gateway:** Proxies `/api/ml/match-single` with full parameter forwarding and graceful local fallback.
- **High-Throughput Batch Processing:** Uses `bulk_insert_mappings` in batches of 5,000 for rapid data ingestion.

---

### 3.3 Frontend Application (`Frontend/`)
Built with React 19, Vite 8, Lucide Icons, and Recharts. Runs on port `5173`.

- **Dashboard:** Real-time KPI counters (Materials, CNMCs, Rationalization %, Spend, Savings), Category Breakdown Chart, and Financial Impact Comparisons.
- **Batch Upload (`Upload.jsx`):** Drag-and-drop file upload with a dual-mode switch:
  * **✦ Ingest & AI Harmonize:** Forwards file to ML microservice for real-time 4-stage processing and stores golden records.
  * **📁 Raw Ingest Only:** Ingests raw data directly into the database for manual review.
- **Material Master Browser (`Materials.jsx`):** Paginated table supporting search, sector filtering, CPSE filtering, and inline APPROVE/REJECT actions.
- **Duplicate Clusters (`Clusters.jsx`):** Visualizes variants grouped by minted CNMC, displaying price spread variance across CPSEs.
- **AI Semantic Matcher (`AIMatch.jsx`):** Interactive query console to test semantic matches against the 1,517 pre-indexed golden clusters in ~15ms.
- **Financial Analytics (`Analytics.jsx`):** Visualizes demand consolidation opportunities and holding cost reduction targets.
- **Network Resilience:** Dynamically resolves API endpoints using `window.location.hostname`, allowing seamless access across local WiFi/LAN during presentations.

---

## 4. History of Audits, Gaps Found & How They Were Fixed

| Subsystem | Initial Audit Gap | Permanent Architectural Fix |
|:---|:---|:---|
| **Frontend Integration** | Initial frontend branch was 100% static HTML/mockup with zero `fetch()` or `axios` calls. | Completely replaced with modern `Frontend/` application using a modular `src/api/api.js` client. |
| **Microservice Bridge** | Backend (`:8000`) and ML (`:8001`) were two isolated apps with no communication. | Created `/api/upload-and-harmonize` bridge and `/api/ml/match-single` proxy gateway. |
| **API Parameter Mismatch** | `ml_service.py` expected 4 parameters while `pipeline.py` accepted 2. | Standardized parameter names across `match_single_query(query_description, query_spec_text, query_uom, top_k)`. |
| **Heavy Import Overhead** | SentenceTransformers (78M params) loaded globally on module import. | Converted to lazy `@property` pattern; model loads only when first inference is requested. |
| **Single SKU Bearing Hack** | Bearing deduplication was hardcoded to only one SKU (`6205`). | Generalized to universal ISO dimension lookup table covering deep groove, spherical, and roller bearings. |
| **Cluster Response Shape** | Frontend expected an array with `total_duplicates`; backend sent `{ count, clusters }` with `material_count`. | Backend updated to supply both fields; `api.js` defensively unwraps `{ count, clusters }` to guarantee an array. |
| **KPI Schema Mismatch** | Frontend expected nested `summary` and `financial_impact_crores`; backend sent flat keys. | Backend updated to return both nested and flat keys; frontend given fallback chains (`summary?.x \|\| kpis?.x`). |
| **Non-Functional Tests** | Test suite crashed with missing imports and hardcoded length assertions. | Re-architected test suite into 44 independent pytest test cases with 100% pass rate. |
| **Local Network Presentation** | Vite bound to `localhost`; API URLs hardcoded to `localhost`, breaking LAN demos. | Vite configured with `host: 0.0.0.0`; `api.js` dynamic hostname resolution via `window.location.hostname`. |

---

## 5. Database Schema Reference

### Table: `materials` (SQLAlchemy `MaterialMaster`)
```sql
CREATE TABLE materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_code VARCHAR(100) NOT NULL,
    description VARCHAR(500) NOT NULL,
    cpse_name VARCHAR(100) DEFAULT 'CPSE_GENERAL',
    sector VARCHAR(100) DEFAULT 'General',
    uom VARCHAR(50) DEFAULT 'NOS',
    unit_price FLOAT DEFAULT 0.0,
    stock_qty INTEGER DEFAULT 0,
    annual_qty INTEGER DEFAULT 0,
    cnmc_code VARCHAR(100) DEFAULT 'PENDING_HARMONIZATION',
    standardized_description VARCHAR(500) DEFAULT '',
    status VARCHAR(50) DEFAULT 'ACTIVE',
    extra_data TEXT DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Table: `audit_logs` (SQLAlchemy `AuditLog`)
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_code VARCHAR(100) NOT NULL,
    action VARCHAR(50) NOT NULL,
    performed_by VARCHAR(100) DEFAULT 'dashboard_user',
    notes TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 6. Complete API Endpoint Specification

### Backend Gateway (`:8000`)
- `GET /` — Health check (`{"service": "National Unified Material Master Platform", "status": "online"}`).
- `GET /api/materials?q=&sector=&cpse=&limit=50&offset=0` — Paginated material catalog.
- `GET /api/analytics/kpis` — Aggregate inventory, spend, duplicate counts, and savings estimates.
- `GET /api/analytics/opportunities?top_n=10` — Top CNMC clusters ranked by demand aggregation savings.
- `GET /api/duplicates/clusters?limit=25` — Variant clusters grouped under minted CNMCs.
- `POST /api/materials/{id}/action?action=APPROVE|REJECT` — Human-in-the-loop catalog governance.
- `GET /api/audit?limit=50` — Immutable audit trail of governance actions.
- `POST /api/upload` — Multipart file upload (CSV, XLSX, PDF) storing raw records.
- `POST /api/upload-and-harmonize` — Multipart upload piping file to ML microservice and persisting harmonized results.
- `POST /api/ml/match-single` — Gateway proxy forwarding semantic match queries to ML engine.

### ML Microservice (`:8001`)
- `GET /health` — Microservice health, engine version, and number of indexed golden clusters.
- `GET /api/ml/kpis` — Returns processing metrics from `data/processed/dashboard_kpis.json`.
- `POST /api/ml/match-single` — Fast semantic match returning top-K matches with confidence and reasoning.
  * Body: `{"query_description": "...", "query_spec_text": "...", "query_uom": "NOS", "top_k": 5}`
- `POST /api/ml/harmonize-batch` — Multipart CSV upload running full 4-stage pipeline; returns crosswalk and KPIs.
- `POST /api/ml/harmonize-batch-json` — Direct JSON payload batch harmonization.

---

## 7. Migration Playbook for Fedora (`klassje@revachol`)

### 7.1 Target Environment Profile
- **Host:** `revachol` (Fedora Linux)
- **User:** `klassje` (unprivileged account)
- **GPU:** NVIDIA GeForce RTX 3050 Laptop GPU (4GB VRAM, CUDA 13.3)
- **Ollama Status:** Already deployed and running on host via rootless Podman on port `11434` (`qwen2.5:3b` pulled).

---

### 7.2 Systemwide Prerequisites (USER SUDO REQUIRED)
Because you are logged in as the unprivileged user `klassje`, please run the following one-time system setup commands using `sudo`:

```bash
# 1. Install development tools and rootless Podman compose
sudo dnf install -y git podman podman-compose nodejs npm python3 python3-pip

# 2. Open presentation ports in the Fedora firewall for LAN / Wi-Fi access
sudo firewall-cmd --permanent --add-port={5173,8000,8001}/tcp
sudo firewall-cmd --reload

# 3. (Optional) Enable lingering so user containers and systemd services persist
loginctl enable-linger klassje
```

---

### 7.3 Deployment Option A: Containerized via Podman Rootless (Recommended)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Siddharth-sde/SIH.git
   cd SIH
   ```

2. **Configure Environment:**
   Ensure `Frontend/.env` exists:
   ```bash
   cp Frontend/.env.example Frontend/.env
   ```

3. **Launch Stack:**
   ```bash
   ./run-containers.sh
   # Or directly:
   podman compose up -d --build
   ```

4. **Verify Container Health:**
   ```bash
   podman ps
   curl -s http://localhost:8000/
   curl -s http://localhost:8001/health
   ```

---

### 7.4 Deployment Option B: Local Native Processes (Alternative)

1. **Setup Python Virtual Environment:**
   ```bash
   cd SIH
   python3 -m venv .venv
   .venv/bin/pip install --upgrade pip
   .venv/bin/pip install -r Backend/requirements.txt -r ML/requirements.txt pytest
   ```

2. **Setup Frontend:**
   ```bash
   cd Frontend
   npm ci
   cd ..
   ```

3. **Run All Services via Single Command:**
   ```bash
   ./run-local.sh
   ```

---

### 7.5 Systemd Rootless User Services (Autostart on Fedora)

To manage the application using Fedora's user-level systemd daemon (`systemctl --user`), create user service units:

1. **Directory:**
   ```bash
   mkdir -p ~/.config/systemd/user
   ```

2. **ML Service (`~/.config/systemd/user/sih-ml.service`):**
   ```ini
   [Unit]
   Description=SIH26 ML Harmonization Microservice
   After=network.target

   [Service]
   Type=simple
   WorkingDirectory=%h/SIH
   Environment=PYTHONPATH=%h/SIH/ML:%h/SIH
   Environment=ML_PORT=8001
   ExecStart=%h/SIH/.venv/bin/uvicorn ML.src.ml_service:app --host 0.0.0.0 --port 8001
   Restart=always

   [Install]
   WantedBy=default.target
   ```

3. **Backend Service (`~/.config/systemd/user/sih-backend.service`):**
   ```ini
   [Unit]
   Description=SIH26 Backend API Gateway
   After=network.target sih-ml.service

   [Service]
   Type=simple
   WorkingDirectory=%h/SIH
   Environment=PYTHONPATH=%h/SIH
   ExecStart=%h/SIH/.venv/bin/uvicorn Backend.main:app --host 0.0.0.0 --port 8000
   Restart=always

   [Install]
   WantedBy=default.target
   ```

4. **Enable & Start:**
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now sih-ml.service sih-backend.service
   ```

---

## 8. Presentation & Live Demo Playbook

### 8.1 5-Minute Pitch Narrative
1. **The Hook (1 min):** Highlight that the 5 major CPSEs currently waste over ₹37,000 Crore across fragmented, redundant spare parts catalogs with zero cross-enterprise visibility.
2. **The Platform (1.5 min):** Showcase the live **Dashboard**: 50,000 materials harmonized down to 1,517 CNMC codes with an aggregate 96.97% catalog reduction.
3. **The AI Engine (1.5 min):** Open **AI Matching** and demonstrate live resolution of ambiguous industrial queries against the 1,517 golden catalog in 15ms.
4. **Governance & Procurement (1 min):** Show **Duplicate Clusters** highlighting price variances across BHEL, CIL, CPCL, NTPC, and SAIL, and execute a live catalog approval audit action.

### 8.2 Live Demo Showcase Examples

#### Example 1: Bearing OEM vs Generic Standard Match
- **Input Query:** `Deep Groove Ball Bearing 25x52x15 mm rubber seals`
- **Output:** Matches OEM `SKF 6205-2RSH` under cluster `NMC-OG-BRG-0001`.
- **Judges Talking Point:** "Our ISO dimension crosswalk identifies that standard 25x52x15mm bearings match expensive OEM part numbers, eliminating brand monopoly markups."

#### Example 2: Gate Valve Pressure Class Conflict Defense
- **Input Query:** `Gate Valve 50 NB Class 300# Flanged WNRF Carbon Steel`
- **Candidate Pair:** `Gate Valve 2 inch 150# CS Flanged`
- **Output:** **REJECTED** with attribute reason: `"Pressure Class Conflict: 300# != 150#"`.
- **Judges Talking Point:** "AI cannot blindly cluster by name. Our Stage 4 hard attribute validator prevents catastrophic safety failures by rejecting pressure rating mismatches."

#### Example 3: Power Cable Conductor Metallurgy Defense
- **Input Query:** `1.1 kV XLPE 3.5C x 120 sqmm Aluminium Armoured Cable`
- **Candidate Pair:** `1.1 kV XLPE 3.5C x 120 sqmm Copper Armoured Cable`
- **Output:** **REJECTED** with attribute reason: `"Conductor Material Conflict: aluminium != copper"`.

---

## 9. Verification & Health Check Commands

```bash
# 1. Run Automated Test Suite
PYTHONPATH=ML .venv/bin/pytest ML/tests/ -v --tb=short

# 2. Check Backend Gateway
curl -s http://127.0.0.1:8000/ | grep -q "online" && echo "Backend: OK"

# 3. Check ML Microservice
curl -s http://127.0.0.1:8001/health | grep -q "healthy" && echo "ML Engine: OK"

# 4. Check Golden Clusters Index
curl -s http://127.0.0.1:8001/health | grep -o '"loaded_golden_clusters":[0-9]*'

# 5. Check Financial KPIs
curl -s http://127.0.0.1:8000/api/analytics/kpis | grep -o '"duplicates_eliminated":[0-9]*'
```
