# Smart India Hackathon (SIH) - AI-Powered National Material Master

Unified repository for CPSE Material Harmonization, Technical Specification Extraction, and Deduplication Clustering.

---

## 📁 Repository Structure

All branches have been merged into `main` and organized into dedicated functional modules:

```
SIH/
├── Backend/        # FastAPI backend service, SQLite DB, Docker container, and ingestion APIs
├── ML/             # Machine Learning pipeline, NLP attribute extraction, clustering microservice
├── Datasets/       # Synthetic and raw CPSE material master datasets and ground truth clusters
├── .gitignore      # Root Git ignore configuration
├── LICENSE         # Repository license
└── README.md       # Unified project documentation
```

---

## 🧩 Components Overview

### 1. Backend (`/Backend`)
FastAPI application handling data ingestion, database management, and analytics APIs.
- **Port**: `8000`
- **Key Modules**:
  - `main.py`: FastAPI application exposing endpoints for uploads, clusters, and KPIs.
  - `models.py`: SQLAlchemy database models for materials and cluster mappings.
  - `database.py`: Database engine and session configuration.
  - `pdf_extractor.py`: Tabular and specification extraction from material PDFs.
  - `import_master_data.py`: Batch ingestion utility for 50,000+ item master datasets.
  - `Dockerfile` & `docker-compose.yml`: Container setup for local or staging deployment.

### 2. Machine Learning (`/ML`)
End-to-end ML harmonization pipeline and microservice.
- **Port**: `8001`
- **Key Modules**:
  - `src/preprocessor.py`: Text normalization, acronym expansion, and UOM harmonization.
  - `src/attribute_extractor.py`: Specification parsing and conflict detection.
  - `src/classifier.py`: Dual-layer taxonomy classification with embeddings.
  - `src/matcher.py`: Deduplication clustering and CNMC code assignment.
  - `src/pipeline.py`: Harmonization pipeline orchestrator.
  - `src/ml_service.py`: Microservice exposing `/api/ml/harmonize-batch` and `/api/ml/match-single`.
  - `demo.py`: Interactive CLI evaluation demo.
  - `test_pipeline_live.py`: Multi-CPSE price arbitrage verification script.
  - `Dockerfile.ml`: Container configuration for the ML microservice.

### 3. Datasets (`/Datasets`)
Centralized datasets for evaluation, training, and benchmarking:
- `cpse_material_master_all.csv`: Complete CPSE material dataset.
- `material_master_input_50000.csv`: Large-scale 50,000 records dataset.
- `material_master_input.csv`: Core development sample dataset.
- `ground_truth_clusters.csv`: Ground truth clusters for deduplication validation.
- `cpse_synthetic_material_datasets.zip`: Synthetic benchmark archive.

---

## 🚀 Quick Start

### Running Backend Locally
```bash
cd Backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation: `http://localhost:8000/docs`

### Running ML Microservice Locally
```bash
cd ML
pip install -r requirements.txt
uvicorn src.ml_service:app --host 0.0.0.0 --port 8001 --reload
```
ML Service Health: `http://localhost:8001/health`

### Running ML Tests
```bash
pytest ML/tests
```
