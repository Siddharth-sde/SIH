# National Unified Material Master Platform — Master Knowledgebase

> **Smart India Hackathon (SIH 2026)**  
> **Topic:** AI-Driven Material Catalog Harmonization, Deduplication & Common National Material Code (CNMC) Generation for Indian Central Public Sector Enterprises (CPSEs).  
> **Repository:** `https://github.com/Siddharth-sde/SIH.git`  
> **Target OS:** Fedora Linux (`klassje@revachol`)  
> **Target Architecture:** 3 Podman Containers (Ollama + ML Engine + Backend/Frontend Host)  
> **Access Model:** Unprivileged user `klassje` with direct SDDM graphical login, fully isolated from admin `louise`.

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
- **Total Locked Inventory Value:** ₹80,642 Crore (~₹80.6K Cr).
- **Inventory Holding Cost Reduction (15% rationalization):** **₹12,096.30 Crore**.
- **Total Combined Fiscal Value:** **₹37,996+ Crore**.

---

## 2. Final 3-Container Podman Architecture

The production and demo deployment is strictly encapsulated into **three rootless Podman containers** running under the unprivileged user `klassje`:

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             CONTAINER 3: sih_app_host                            │
│                 Unified Backend Gateway + Frontend Web Server                    │
│                                                                                  │
│   ┌────────────────────────────────┐         ┌───────────────────────────────┐   │
│   │     Nginx Web Server (:5173)   │         │     FastAPI Gateway (:8000)   │   │
│   │  - Serves React 19 + Vite SPA  │ ──────► │  - Material Master CRUD       │   │
│   │  - Proxies /api/ to port 8000  │  Proxy  │  - SQLite (materials, audit)  │   │
│   └────────────────────────────────┘         │  - Cold-Start Data Seeding    │   │
│                                              │  - Governance Action Handlers │   │
│                                              └───────────────┬───────────────┘   │
└──────────────────────────────────────────────────────────────┼───────────────────┘
                                                               │ HTTP Proxy Bridge
                                                               ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           CONTAINER 2: sih_ml_service                            │
│                         ML Harmonization Microservice                            │
│                                                                                  │
│   - FastAPI Microservice running on Port 8001                                    │
│   - 4-Stage AI Pipeline: Preprocessor → Extractor → Classifier → Matcher         │
│   - 1,517 Golden Cluster Vector Index in RAM (SentenceTransformer MiniLM)        │
│   - Automated Test Suite: 44/44 passing                                          │
└──────────────────────────────────────┬───────────────────────────────────────────┘
                                       │ HTTP (:11434)
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            CONTAINER 1: sih_ollama                               │
│                         Local LLM Engine (GPU-Accelerated)                       │
│                                                                                  │
│   - Docker Image: docker.io/ollama/ollama:latest                                │
│   - Hardware Passthrough: NVIDIA GeForce RTX 3050 via CDI (nvidia.com/gpu=all)   │
│   - Serving: qwen2.5:3b on Port 11434                                            │
│   - Persistent Volume: ollama-storage                                            │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Container Topology Summary:
1. **Container 1 (`sih_ollama`)**: Hardware-accelerated LLM engine running `qwen2.5:3b`. Listens on port `11434`.
2. **Container 2 (`sih_ml_service`)**: Deterministic and vector harmonization engine built from `ML/Dockerfile.ml`. Listens on port `8001`. Connects to Container 1 for ambiguous taxonomy verification.
3. **Container 3 (`sih_app_host`)**: Multi-stage unified container built from `Dockerfile.app`. Runs internal Uvicorn on port `8000` (FastAPI backend + SQLite) and Nginx on port `5173` (serving production React bundle and reverse-proxying `/api/` to port 8000).

---

## 3. Security & Privilege Isolation Playbook (`louise` vs `klassje`)

To prevent the demo/agent user (`klassje`) from accessing the admin user's files (`louise`) or modifying the system, execute this least-privilege lockdown.

### 3.1 Commands to run as `louise` (using `sudo`):

```bash
# ---------------------------------------------------------
# 1. HARDEN ADMIN HOME DIRECTORY (ZERO VISIBILITY FOR KLASSJE)
# ---------------------------------------------------------
# Set louise's home directory to 0700 so no other user can read or enter it
sudo chmod 700 /home/louise

# Remove any lingering POSIX ACLs that might grant read access
sudo setfacl -b /home/louise

# ---------------------------------------------------------
# 2. STRIP ADMINISTRATIVE PRIVILEGES FROM KLASSJE
# ---------------------------------------------------------
# Ensure klassje is NOT in wheel, adm, or systemd-journal
sudo gpasswd -d klassje wheel 2>/dev/null || true
sudo gpasswd -d klassje adm 2>/dev/null || true
sudo gpasswd -d klassje systemd-journal 2>/dev/null || true

# Verify no sudoers entries grant privileges to klassje
sudo grep -rn "klassje" /etc/sudoers /etc/sudoers.d/ || true

# ---------------------------------------------------------
# 3. CONFIGURE MINIMUM PRIVILEGES REQUIRED FOR FUNCTIONALITY
# ---------------------------------------------------------
# Grant access to GPU devices for rootless container hardware acceleration
sudo usermod -aG video,render klassje

# Ensure rootless Podman subuid/subgid ranges are mapped
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 klassje 2>/dev/null || true

# Allow user background services to run without an active session
sudo loginctl enable-linger klassje

# Open presentation ports in the Fedora firewall for LAN / Wi-Fi access
sudo firewall-cmd --permanent --add-port={5173,8000,8001}/tcp
sudo firewall-cmd --reload
```

### 3.2 Audit Verification Checklist:
Run these quick tests to guarantee isolation before starting the session:
```bash
# Check group memberships (MUST NOT contain wheel or adm):
groups klassje
# Expected output: klassje : klassje video render

# Test access to louise from klassje (MUST FAIL):
sudo -u klassje ls -la /home/louise
# Expected output: ls: cannot open directory '/home/louise': Permission denied

# Test GPU device access from klassje (MUST SUCCEED):
sudo -u klassje ls -la /dev/nvidia* /dev/dri/renderD128
# Expected output: crw-rw----+ 1 root video ...
```

---

## 4. Component Deep Dive

### 4.1 ML Harmonization Microservice (`ML/`)
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

### 4.2 Backend Gateway & Frontend Host (`sih_app_host`)
Runs inside Container 3 on ports `8000` and `5173`.

- **FastAPI Gateway (:8000):**
  * **Dual Schema Support:** Tables `materials` and `material_master` are fully aligned.
  * **Audit Logging:** Every administrative action (`APPROVE`, `REJECT`) creates an immutable row in `audit_logs`.
  * **Dynamic File Ingestion:** Supports CSV, XLSX, and PDF (via `pdfplumber`).
  * **Universal Column Mapping:** Heuristic `ALIASES` dictionary maps diverse CPSE column names (`item_code`, `mat_no`, `desc`, `short_text`, `price`, `rate`, `stock_qty`, etc.) into canonical fields.
  * **Cold-Start Auto-Seeding:** Discovers candidate dataset files on first startup (`cpse_material_master_all.csv`, `material_master_input_50000(1).csv`, etc.) and hydrates SQLite automatically.
  * **ML Proxy Gateway:** Proxies `/api/ml/match-single` with full parameter forwarding and graceful local fallback.
  * **High-Throughput Batch Processing:** Uses `bulk_insert_mappings` in batches of 5,000 for rapid data ingestion.
- **Nginx Web Server (:5173):**
  * Serves optimized production build of the React 19 + Vite 8 SPA.
  * Internal reverse proxy routing: `/api/*` requests arriving on port 5173 are passed directly to `127.0.0.1:8000/api/*`, completely eliminating CORS issues.
  * Dynamic host evaluation: resolves endpoints using `window.location.hostname`, ensuring seamless operation when accessed via external laptops/tablets across Wi-Fi.

---

## 5. History of Audits, Gaps Found & How They Were Fixed

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
| **Multi-Container Sprawl** | Separate containers for frontend, backend, and proxies increased failure points. | Unified into a 3-container topology: Ollama, ML Service, and App Host (Backend + Frontend). |

---

## 6. Database Schema & API Reference

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

### Key API Endpoints
- **Frontend / Unified Web UI:** `http://localhost:5173/`
- **Backend API Gateway:** `http://localhost:8000/docs`
  * `GET /api/materials` — Search, filter, and paginate through materials.
  * `GET /api/analytics/kpis` — Aggregate financial impact and rationalization statistics.
  * `GET /api/duplicates/clusters` — Grouped variants sharing minted CNMC codes.
  * `POST /api/materials/{id}/action` — Approve/Reject material governance actions.
  * `POST /api/upload-and-harmonize` — Stream CSV to ML microservice and store harmonized master records.
  * `POST /api/ml/match-single` — Proxy gateway for single-item semantic queries.
- **ML Harmonization Engine:** `http://localhost:8001/docs`
  * `GET /health` — Health status and count of indexed golden clusters (1,517).
  * `POST /api/ml/match-single` — Direct semantic matching endpoint.
  * `POST /api/ml/harmonize-batch` — Batch CSV ingestion pipeline.
- **Ollama Engine:** `http://localhost:11434/`
  * `POST /api/generate` & `POST /api/chat` — `qwen2.5:3b` inference.

---

## 7. Fedora Target Host Deployment (`klassje@revachol`)

### 7.1 Direct Login Workflow
1. At the **SDDM login screen**, select user **`klassje`**.
2. Log in directly to the graphical desktop session (KDE Wayland/X11).

### 7.2 Launching the 3 Containers
Open a terminal as `klassje`:

```bash
# 1. Clone or pull the repository
git clone https://github.com/Siddharth-sde/SIH.git
cd SIH

# 2. Deploy the 3-container stack
./run-containers.sh
```

The script automatically detects if your existing Ollama container is already running on port 11434 and brings up the ML microservice and Unified App Host:
* **Container 1 (`sih_ollama`):** Port `11434`
* **Container 2 (`sih_ml_service`):** Port `8001`
* **Container 3 (`sih_app_host`):** Ports `8000` & `5173`

### 7.3 Health Check & Verification
```bash
# Check running containers:
podman ps

# Verify Backend:
curl -s http://127.0.0.1:8000/

# Verify ML Engine:
curl -s http://127.0.0.1:8001/health

# Verify Ollama tags:
curl -s http://127.0.0.1:11434/api/tags
```
