"""
End-to-End Material Master Harmonization Pipeline Orchestrator.
National Unified Material Master Platform - ML Engine.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

from src.preprocessor import preprocessor
from src.attribute_extractor import attribute_extractor
from src.classifier import classifier, TAXONOMY
from src.matcher import matcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


ERP_TO_TAXONOMY = {
    "MRO-BEARINGS": ("BEARINGS", "Bearings & Spares"),
    "ELECTRICAL-SWITCHGEAR": ("SWITCHGEAR", "Insulators & Switchgear"),
    "GASKETS-SEALING-PRODUCTS": ("GASKETS_SEALS", "Gaskets & Seals"),
    "HARDWARE-FASTENERS": ("FASTENERS", "Fasteners & Hardware"),
    "PIPING-VALVES": ("VALVES_FLOW", "Valves & Flow Control"),
    "PIPING-TUBES": ("PIPE_FITTINGS", "Flanges & Pipe Fittings"),
    "ELECTRICAL-CABLES": ("CABLES_CONDUCTORS", "Cables & Conductors"),
    "INSTRUMENTATION-CONTROL": ("SWITCHGEAR", "Insulators & Switchgear"),
    "PUMPS-ROTATING-SPARES": ("PUMPS_ROTATING", "Pumps & Rotating Machinery"),
    "FILTERS-CONSUMABLES": ("MISC_UNCLASSIFIED", "Miscellaneous / Unclassified Spares"),
    "PIPING-FITTINGS": ("PIPE_FITTINGS", "Flanges & Pipe Fittings"),
}

TAXONOMY_TO_ERP = {
    "BEARINGS": ["MRO-BEARINGS"],
    "SWITCHGEAR": ["ELECTRICAL-SWITCHGEAR", "INSTRUMENTATION-CONTROL"],
    "GASKETS_SEALS": ["GASKETS-SEALING-PRODUCTS"],
    "FASTENERS": ["HARDWARE-FASTENERS"],
    "VALVES_FLOW": ["PIPING-VALVES"],
    "PIPE_FITTINGS": ["PIPING-FITTINGS", "PIPING-TUBES"],
    "CABLES_CONDUCTORS": ["ELECTRICAL-CABLES"],
    "PUMPS_ROTATING": ["PUMPS-ROTATING-SPARES"],
    "MISC_UNCLASSIFIED": ["FILTERS-CONSUMABLES"],
    "MOTORS_DRIVES": ["ELECTRICAL-SWITCHGEAR", "PUMPS-ROTATING-SPARES"],
}


class MaterialHarmonizationPipeline:
    """
    Unified end-to-end pipeline connecting:
    - Stage 1: Text Preprocessing & Acronym Expansion
    - Stage 2: Technical Attribute Extraction & Conflict Detection
    - Stage 3: Dual-Layer Taxonomy Classification & Vector Embeddings
    - Stage 4: Deduplication Graph Clustering & CNMC Code Generation
    """

    def __init__(self, match_threshold: Optional[float] = None, auto_load_catalog: bool = True, use_llm: Optional[bool] = None):
        self.preprocessor = preprocessor
        self.attribute_extractor = attribute_extractor
        self.classifier = classifier
        self.matcher = matcher
        if match_threshold is not None:
            self.matcher.match_threshold = match_threshold

        env_llm = os.getenv("USE_LLM", "true").lower() in ("true", "1", "yes")
        self.use_llm = use_llm if use_llm is not None else env_llm

        self.golden_clusters: List[Dict[str, Any]] = []
        self.crosswalk_records: List[Dict[str, Any]] = []
        self.processed_records: List[Dict[str, Any]] = []
        self._canonical_embeddings: Dict[str, np.ndarray] = {}
        self._catalog_embeddings: Optional[np.ndarray] = None

        if auto_load_catalog:
            self.load_existing_catalog()

    def process_dataset(self, csv_path: str) -> Dict[str, Any]:
        """
        Executes complete pipeline on input dataset.
        """
        logger.info(f"Loading raw dataset from {csv_path}")
        df = pd.read_csv(csv_path)

        # Stage 1: Preprocessing & UOM Harmonization
        logger.info("Executing Stage 1: Text Preprocessing & UOM Harmonization")
        p_df = self.preprocessor.process_dataframe(df)

        # Stage 2: Attribute Extraction
        logger.info(f"Executing Stage 2: Technical Attribute Extraction for {len(p_df)} items")
        specs_list = [
            self.attribute_extractor.extract(row["cleaned_description"], row["cleaned_spec_text"])
            for _, row in p_df.iterrows()
        ]

        # Stage 3: Dual-Layer Vector Classification & Embedding
        logger.info(f"Executing Stage 3: Vectorized Classification for {len(p_df)} items (use_llm={self.use_llm})")
        cls_results = self.classifier.classify_batch(
            p_df["cleaned_description"].tolist(),
            p_df["cleaned_spec_text"].tolist(),
            specs_list,
            batch_size=256,
            use_llm=self.use_llm
        )

        self.processed_records = []
        plant_codes = df["plant_code"].tolist() if "plant_code" in df.columns else [""] * len(p_df)
        sectors = df["sector"].tolist() if "sector" in df.columns else ["Cross-Sector"] * len(p_df)

        for idx, (row, specs, cls_result) in enumerate(zip(p_df.to_dict(orient="records"), specs_list, cls_results)):
            self.processed_records.append({
                "idx": idx,
                "source_material_code": row["source_material_code"],
                "cpse_id": row["cpse_id"],
                "plant_code": plant_codes[idx],
                "sector": sectors[idx],
                "raw_description": row["raw_description"],
                "raw_spec_text": row["raw_spec_text"],
                "cleaned_description": row["cleaned_description"],
                "cleaned_spec_text": row["cleaned_spec_text"],
                "combined_text": row.get("combined_text", f"{row['cleaned_description']} {row['cleaned_spec_text']}".strip()),
                "specs": specs,
                "category_id": cls_result["category_id"],
                "category_name": cls_result["category_name"],
                "classification_confidence": cls_result["confidence"],
                "classification_method": cls_result["method"],
                "classification_reasoning": cls_result["reasoning"],
                "embedding": np.array(cls_result["embedding"]),
                "canonical_uom": row["canonical_uom"],
                "source_uom": row["source_uom"],
                "unit_price_inr": row["unit_price_inr"],
                "current_stock_qty": row["current_stock_qty"],
                "annual_procurement_qty": row["annual_procurement_qty"],
            })

        # Stage 4: Deduplication Clustering & CNMC Generation
        logger.info("Executing Stage 4: Deduplication Clustering & CNMC Minting")
        self.golden_clusters, self.crosswalk_records = self.matcher.cluster_and_harmonize(
            self.processed_records
        )

        logger.info(
            f"Harmonization complete: {len(self.processed_records)} items -> "
            f"{len(self.golden_clusters)} Unified National Codes (CNMC)"
        )

        return {
            "total_records": len(self.processed_records),
            "golden_clusters_count": len(self.golden_clusters),
            "duplicate_clusters_count": sum(1 for c in self.golden_clusters if c["is_duplicate_cluster"]),
            "duplicates_rationalized": len(self.processed_records) - len(self.golden_clusters),
        }

    def export_results(self, output_dir: str = "data/processed") -> Dict[str, str]:
        """
        Exports processed artifacts to CSV and JSON formats for Backend/Frontend ingestion.
        """
        os.makedirs(output_dir, exist_ok=True)

        # 1. Unified Material Master (Golden Catalog)
        golden_df = pd.DataFrame([
            {
                "cnmc_code": c["cnmc_code"],
                "canonical_description": c["canonical_description"],
                "category_id": c["category_id"],
                "category_name": c["category_name"],
                "sector": c["sector"],
                "standard_uom": c["standard_uom"],
                "duplicate_count": c["duplicate_count"],
                "affected_cpses": ", ".join(c["affected_cpses"]),
                "specifications": json.dumps(c["specifications"]),
            }
            for c in self.golden_clusters
        ])
        golden_path = os.path.join(output_dir, "unified_material_master.csv")
        golden_df.to_csv(golden_path, index=False)

        # 2. Material Crosswalk Table (Traceability & Review Queue)
        crosswalk_df = pd.DataFrame(self.crosswalk_records)
        crosswalk_path = os.path.join(output_dir, "material_crosswalk.csv")
        crosswalk_df.to_csv(crosswalk_path, index=False)

        # 3. High-Level KPI Summary (for Dashboard)
        total_items = len(self.crosswalk_records)
        unique_cnmcs = len(self.golden_clusters)
        duplicates = total_items - unique_cnmcs
        total_spend = sum(r["unit_price_inr"] * r["annual_procurement_qty"] for r in self.crosswalk_records)
        savings_pct = float(os.getenv("SAVINGS_PERCENTAGE", "0.08"))
        est_savings = round(total_spend * savings_pct, 2)

        kpis = {
            "total_materials_ingested": total_items,
            "unique_national_materials": unique_cnmcs,
            "duplicates_rationalized": duplicates,
            "rationalization_percentage": f"{(duplicates / total_items * 100):.1f}%" if total_items > 0 else "0.0%",
            "savings_percentage_applied": f"{savings_pct * 100:.1f}%",
            "total_annual_spend_inr": total_spend,
            "estimated_procurement_savings_inr": f"₹{est_savings:,.2f}",
        }
        kpi_path = os.path.join(output_dir, "dashboard_kpis.json")
        with open(kpi_path, "w") as f:
            json.dump(kpis, f, indent=2)

        return {
            "golden_master": golden_path,
            "crosswalk": crosswalk_path,
            "kpis": kpi_path,
        }

    def load_existing_catalog(self, output_dir: Optional[str] = None) -> bool:
        """Loads pre-processed golden clusters and vector embeddings index into memory."""
        import csv
        data_dir = output_dir or os.getenv("PROCESSED_DATA_DIR", "data/processed")
        master_path = os.path.join(data_dir, "unified_material_master.csv")
        npy_path = os.path.join(data_dir, "canonical_embeddings.npy")
        if not os.path.exists(master_path):
            return False
        try:
            clusters = []
            with open(master_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    specs = {}
                    raw_specs = row.get("specifications")
                    if raw_specs and raw_specs.strip():
                        try:
                            specs = json.loads(raw_specs)
                        except Exception:
                            specs = {}
                    raw_cpses = row.get("affected_cpses", "")
                    affected = [c.strip() for c in raw_cpses.split(",") if c.strip()]

                    cat_id = str(row.get("category_id", "MISC_UNCLASSIFIED")).strip()
                    cat_name = str(row.get("category_name", "Unclassified")).strip()
                    if cat_id in ERP_TO_TAXONOMY:
                        cat_id, cat_name = ERP_TO_TAXONOMY[cat_id]

                    clusters.append({
                        "cnmc_code": str(row["cnmc_code"]),
                        "canonical_description": str(row["canonical_description"]),
                        "category_id": cat_id,
                        "category_name": cat_name,
                        "sector": str(row.get("sector", "Cross-Sector")),
                        "standard_uom": str(row.get("standard_uom", "NOS")),
                        "duplicate_count": int(row.get("duplicate_count", 1) or 1),
                        "affected_cpses": affected,
                        "specifications": specs,
                    })
            self.golden_clusters = clusters

            # Hydrate or load precomputed embeddings matrix
            if os.path.exists(npy_path):
                self._catalog_embeddings = np.load(npy_path)
                logger.info(f"Loaded vector index from {npy_path} (shape: {self._catalog_embeddings.shape})")
            else:
                logger.info(f"Precomputing vector index for {len(clusters)} catalog items...")
                descs = [c["canonical_description"] for c in clusters]
                self._catalog_embeddings = self.classifier.encode_batch(descs, batch_size=128)
                try:
                    np.save(npy_path, self._catalog_embeddings)
                except Exception as ex:
                    logger.warning(f"Could not persist embeddings to {npy_path}: {ex}")

            self._canonical_embeddings = {
                c["cnmc_code"]: self._catalog_embeddings[i]
                for i, c in enumerate(clusters)
            }

            logger.info(f"Loaded {len(clusters)} existing golden clusters with vector index from {master_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to auto-load existing catalog from {master_path}: {e}")
            return False

    def match_single_query(
        self,
        query_description: str = "",
        query_spec_text: str = "",
        query_uom: str = "NOS",
        top_k: int = 5,
        query_text: Optional[str] = None,
        use_llm: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Interactive search matching for AIMatching.jsx:
        Takes raw material description, optional specs and UOM, normalizes, extracts
        attributes, classifies taxonomy, and returns top matching golden records in < 20ms.
        """
        active_use_llm = self.use_llm if use_llm is None else use_llm

        # Backwards compatibility for single string argument
        if query_text and not query_description:
            query_description = query_text

        clean_desc = self.preprocessor.normalize_text(query_description)
        clean_spec = self.preprocessor.normalize_text(query_spec_text)
        query_specs = self.attribute_extractor.extract(clean_desc, clean_spec)
        cls_result = self.classifier.classify(clean_desc, clean_spec, query_specs, use_llm=active_use_llm)
        query_emb = np.array(cls_result["embedding"])

        canonical_uom, _ = self.preprocessor.uom_harmonizer.canonicalize(query_uom) if query_uom else ("NOS", "Default")

        query_item = {
            "cleaned_description": clean_desc,
            "cleaned_spec_text": clean_spec,
            "specs": query_specs,
            "embedding": query_emb,
            "canonical_uom": canonical_uom,
            "source_uom": query_uom,
        }

        # If golden clusters or vector index not in memory, attempt hydration
        if not self.golden_clusters or self._catalog_embeddings is None:
            self.load_existing_catalog()

        if not self.golden_clusters or self._catalog_embeddings is None:
            return {
                "query": query_description,
                "query_spec_text": query_spec_text,
                "cleaned_query": clean_desc,
                "canonical_uom": canonical_uom,
                "predicted_category": cls_result["category_name"],
                "category_id": cls_result["category_id"],
                "extracted_attributes": query_specs,
                "top_matches": []
            }

        # Vectorized BLAS Dot-Product Search (sub-millisecond across full catalog)
        sims = np.dot(self._catalog_embeddings, query_emb)

        # Build comprehensive category search candidate set
        pred_cat = cls_result["category_id"]
        target_cats = set([pred_cat])
        for cat_cand, _ in cls_result.get("top_candidates", [])[:3]:
            target_cats.add(cat_cand)

        expanded_cats = set(target_cats)
        for tc in list(target_cats):
            for erp in TAXONOMY_TO_ERP.get(tc, []):
                expanded_cats.add(erp)

        # Candidate selection
        candidate_indices = []
        # 1. First get top matches from the predicted/candidate categories
        cat_indices = [
            i for i, c in enumerate(self.golden_clusters)
            if c.get("category_id") in expanded_cats
        ]
        if cat_indices:
            cat_sims = sims[cat_indices]
            top_in_cat = np.array(cat_indices)[np.argsort(cat_sims)[::-1][:40]]
            candidate_indices.extend(top_in_cat.tolist())

        # 2. Add top global semantic neighbors to guarantee coverage even for edge cases
        top_global = np.argsort(sims)[::-1][:30].tolist()
        for idx in top_global:
            if idx not in candidate_indices:
                candidate_indices.append(idx)

        # Fine-grained Pairwise Refinement on selected candidates
        candidates = []
        for idx in candidate_indices:
            cluster = self.golden_clusters[idx]
            c_emb = self._catalog_embeddings[idx]

            cluster_specs = cluster.get("specifications", {})
            cluster_item = {
                "cleaned_description": cluster["canonical_description"].lower(),
                "specs": cluster_specs,
                "embedding": c_emb,
                "canonical_uom": cluster.get("standard_uom", "NOS"),
            }

            score, matches, conflicts = self.matcher.calculate_pairwise_similarity(query_item, cluster_item)

            # In interactive query mode, distinguish hard technical attribute conflicts from UOM mismatches
            hard_conflicts = [c for c in conflicts if not c.startswith("UOM Conflict")]
            uom_notes = [c for c in conflicts if c.startswith("UOM Conflict")]

            if not hard_conflicts:
                # If high semantic vector similarity, ensure score reflects it
                raw_sim = float(sims[idx])
                effective_score = max(score, round(raw_sim * 0.90, 3)) if raw_sim >= 0.50 else score

                if effective_score >= 0.45:
                    relationship = (
                        "Exact Duplicate" if effective_score >= 0.85
                        else ("Near Duplicate" if effective_score >= 0.70 else "Functionally Equivalent")
                    )

                    reasoning_parts = list(matches[:2]) if matches else [f"Semantic cosine similarity: {raw_sim:.2f}"]
                    if uom_notes:
                        reasoning_parts.append(f"UOM discrepancy ({canonical_uom} vs {cluster.get('standard_uom')})")

                    candidates.append({
                        "cnmc_code": cluster["cnmc_code"],
                        "canonical_description": cluster["canonical_description"],
                        "category": cluster.get("category_name", cls_result["category_name"]),
                        "match_confidence": int(min(1.0, effective_score) * 100),
                        "relationship": relationship,
                        "reasoning": "; ".join(reasoning_parts),
                        "affected_cpses": cluster.get("affected_cpses", []),
                        "score": effective_score
                    })

        # Fallback: if hard attribute conflicts filtered out all candidates (e.g. query has different specs),
        # return top semantic candidates with informative reasoning rather than an empty result
        if not candidates:
            for idx in top_global[:top_k]:
                cluster = self.golden_clusters[idx]
                raw_sim = float(sims[idx])
                if raw_sim >= 0.25:
                    conf = int(min(0.65, max(0.30, raw_sim)) * 100)
                    candidates.append({
                        "cnmc_code": cluster["cnmc_code"],
                        "canonical_description": cluster["canonical_description"],
                        "category": cluster.get("category_name", cls_result["category_name"]),
                        "match_confidence": conf,
                        "relationship": "Functionally Equivalent",
                        "reasoning": f"Nearest semantic catalog match ({int(raw_sim*100)}% embedding similarity; specifications differ)",
                        "affected_cpses": cluster.get("affected_cpses", []),
                        "score": raw_sim * 0.7
                    })

        # Sort by score descending
        candidates.sort(key=lambda x: x["score"], reverse=True)

        return {
            "query": query_description,
            "query_spec_text": query_spec_text,
            "cleaned_query": clean_desc,
            "canonical_uom": canonical_uom,
            "predicted_category": cls_result["category_name"],
            "category_id": cls_result["category_id"],
            "extracted_attributes": query_specs,
            "top_matches": candidates[:top_k]
        }


# Global singleton instance
pipeline = MaterialHarmonizationPipeline()


if __name__ == "__main__":
    summary = pipeline.process_dataset("material_master_input.csv")
    paths = pipeline.export_results("data/processed")
    print("\nPipeline Execution Successful!")
    print(f"Summary: {summary}")
    print(f"Exported files: {paths}")
