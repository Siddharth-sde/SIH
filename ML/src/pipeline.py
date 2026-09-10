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


class MaterialHarmonizationPipeline:
    """
    Unified end-to-end pipeline connecting:
    - Stage 1: Text Preprocessing & Acronym Expansion
    - Stage 2: Technical Attribute Extraction & Conflict Detection
    - Stage 3: Dual-Layer Taxonomy Classification & Vector Embeddings
    - Stage 4: Deduplication Graph Clustering & CNMC Code Generation
    """

    def __init__(self, match_threshold: Optional[float] = None, auto_load_catalog: bool = True):
        self.preprocessor = preprocessor
        self.attribute_extractor = attribute_extractor
        self.classifier = classifier
        self.matcher = matcher
        if match_threshold is not None:
            self.matcher.match_threshold = match_threshold

        self.golden_clusters: List[Dict[str, Any]] = []
        self.crosswalk_records: List[Dict[str, Any]] = []
        self.processed_records: List[Dict[str, Any]] = []
        self._canonical_embeddings: Dict[str, np.ndarray] = {}

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
        logger.info(f"Executing Stage 3: Vectorized Classification for {len(p_df)} items")
        cls_results = self.classifier.classify_batch(
            p_df["cleaned_description"].tolist(),
            p_df["cleaned_spec_text"].tolist(),
            specs_list,
            batch_size=256
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
        """Loads pre-processed golden clusters into memory if available."""
        import csv
        data_dir = output_dir or os.getenv("PROCESSED_DATA_DIR", "data/processed")
        master_path = os.path.join(data_dir, "unified_material_master.csv")
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
                    clusters.append({
                        "cnmc_code": str(row["cnmc_code"]),
                        "canonical_description": str(row["canonical_description"]),
                        "category_id": str(row.get("category_id", "MISC_UNCLASSIFIED")),
                        "category_name": str(row.get("category_name", "Unclassified")),
                        "sector": str(row.get("sector", "Cross-Sector")),
                        "standard_uom": str(row.get("standard_uom", "NOS")),
                        "duplicate_count": int(row.get("duplicate_count", 1) or 1),
                        "affected_cpses": affected,
                        "specifications": specs,
                    })
            self.golden_clusters = clusters
            logger.info(f"Loaded {len(clusters)} existing golden clusters from {master_path}")
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
        query_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Interactive search matching for AIMatching.jsx:
        Takes raw material description, optional specs and UOM, normalizes, extracts
        attributes, classifies taxonomy, and returns top matching golden records.
        """
        # Backwards compatibility for single string argument
        if query_text and not query_description:
            query_description = query_text

        clean_desc = self.preprocessor.normalize_text(query_description)
        clean_spec = self.preprocessor.normalize_text(query_spec_text)
        query_specs = self.attribute_extractor.extract(clean_desc, clean_spec)
        cls_result = self.classifier.classify(clean_desc, clean_spec, query_specs)
        query_emb = np.array(cls_result["embedding"])

        canonical_uom, _ = self.preprocessor.uom_harmonizer.canonicalize(query_uom)

        query_item = {
            "cleaned_description": clean_desc,
            "cleaned_spec_text": clean_spec,
            "specs": query_specs,
            "embedding": query_emb,
            "canonical_uom": canonical_uom,
            "source_uom": query_uom,
        }

        # If golden clusters not in memory, attempt hydration
        if not self.golden_clusters:
            self.load_existing_catalog()

        target_cats = set([cls_result["category_id"]])
        for cat_cand, _ in cls_result.get("top_candidates", [])[:2]:
            target_cats.add(cat_cand)

        candidates = []
        for cluster in self.golden_clusters:
            # Category-aware candidate pre-filtering to eliminate O(N) full linear scans
            c_cat = cluster.get("category_id", "MISC_UNCLASSIFIED")
            if cls_result["category_id"] != "MISC_UNCLASSIFIED" and c_cat not in target_cats:
                continue

            cnmc = cluster["cnmc_code"]
            if cnmc in self._canonical_embeddings:
                c_emb = self._canonical_embeddings[cnmc]
            else:
                c_emb = self.classifier.encode_text(cluster["canonical_description"])
                self._canonical_embeddings[cnmc] = c_emb

            cluster_specs = cluster.get("specifications", {})
            cluster_item = {
                "cleaned_description": cluster["canonical_description"].lower(),
                "specs": cluster_specs,
                "embedding": c_emb,
                "canonical_uom": cluster.get("standard_uom", "NOS"),
            }

            score, matches, conflicts = self.matcher.calculate_pairwise_similarity(query_item, cluster_item)

            if not conflicts and score >= 0.50:
                relationship = "Exact Duplicate" if score >= 0.85 else ("Near Duplicate" if score >= 0.70 else "Functionally Equivalent")
                candidates.append({
                    "cnmc_code": cluster["cnmc_code"],
                    "canonical_description": cluster["canonical_description"],
                    "category": cluster["category_name"],
                    "match_confidence": int(score * 100),
                    "relationship": relationship,
                    "reasoning": "; ".join(matches[:3]) if matches else "Semantic similarity match",
                    "affected_cpses": cluster["affected_cpses"],
                    "score": score
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
