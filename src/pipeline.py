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

    def __init__(self, match_threshold: float = 0.82):
        self.preprocessor = preprocessor
        self.attribute_extractor = attribute_extractor
        self.classifier = classifier
        self.matcher = matcher
        self.matcher.match_threshold = match_threshold

        self.golden_clusters: List[Dict[str, Any]] = []
        self.crosswalk_records: List[Dict[str, Any]] = []
        self.processed_records: List[Dict[str, Any]] = []

    def process_dataset(self, csv_path: str) -> Dict[str, Any]:
        """
        Executes complete pipeline on input dataset.
        """
        logger.info(f"Loading raw dataset from {csv_path}")
        df = pd.read_csv(csv_path)

        # Stage 1: Preprocessing & UOM Harmonization
        logger.info("Executing Stage 1: Text Preprocessing & UOM Harmonization")
        p_df = self.preprocessor.process_dataframe(df)

        # Stage 2 & 3: Attribute Extraction & Dual-Layer Classification
        logger.info("Executing Stages 2 & 3: Attribute Extraction & Classification")
        self.processed_records = []
        for idx, row in p_df.iterrows():
            specs = self.attribute_extractor.extract(
                row["cleaned_description"],
                row["cleaned_spec_text"]
            )
            cls_result = self.classifier.classify(
                row["cleaned_description"],
                row["cleaned_spec_text"],
                specs
            )
            self.processed_records.append({
                "idx": idx,
                "source_material_code": row["source_material_code"],
                "cpse_id": row["cpse_id"],
                "plant_code": df.iloc[idx].get("plant_code", ""),
                "raw_description": row["raw_description"],
                "raw_spec_text": row["raw_spec_text"],
                "cleaned_description": row["cleaned_description"],
                "cleaned_spec_text": row["cleaned_spec_text"],
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
        est_savings = round(total_spend * 0.08, 2)

        kpis = {
            "total_materials_ingested": total_items,
            "unique_national_materials": unique_cnmcs,
            "duplicates_rationalized": duplicates,
            "rationalization_percentage": f"{(duplicates / total_items * 100):.1f}%",
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

    def match_single_query(self, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Interactive search matching for AIMatching.jsx:
        Takes raw material string, cleans it, extracts specs, classifies, and returns
        top matching golden records with explainability reasoning.
        """
        clean_query = self.preprocessor.normalize_text(query_text)
        query_specs = self.attribute_extractor.extract(clean_query)
        cls_result = self.classifier.classify(clean_query, "", query_specs)
        query_emb = np.array(cls_result["embedding"])

        query_item = {
            "cleaned_description": clean_query,
            "specs": query_specs,
            "embedding": query_emb,
            "canonical_uom": "NOS",
        }

        candidates = []
        for cluster in self.golden_clusters:
            # Check cluster specifications
            cluster_specs = cluster.get("specifications", {})
            cluster_item = {
                "cleaned_description": cluster["canonical_description"].lower(),
                "specs": cluster_specs,
                "embedding": self.classifier.encode_text(cluster["canonical_description"]),
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
            "query": query_text,
            "cleaned_query": clean_query,
            "predicted_category": cls_result["category_name"],
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
