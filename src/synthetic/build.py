"""Create the raw input files: generate clean data, damage it, write CSV and Excel."""

import json
import logging

from src.synthetic.corrupt import corrupt_dataset
from src.synthetic.generator import SyntheticConfig, generate_clean_dataset

logger = logging.getLogger(__name__)

# real exports come in mixed formats, so a few tables are Excel and the rest CSV
EXCEL_TABLES = {"customers", "products", "inventory"}
MANIFEST_NAME = "_generation_manifest.json"


def ground_truth(clean):
    """Numbers from the clean data, to compare the pipeline output against."""
    items = clean.order_items.merge(clean.orders[["order_id", "order_status"]], on="order_id")
    completed = items[items["order_status"] == "Completed"]
    net_revenue = (
        completed["quantity"] * completed["unit_price"] * (1 - completed["discount_pct"] / 100)
    )
    return {
        "customers": len(clean.customers),
        "orders_total": len(clean.orders),
        "orders_completed": int((clean.orders["order_status"] == "Completed").sum()),
        "order_items_total": len(clean.order_items),
        "completed_net_revenue": round(float(net_revenue.sum()), 2),
    }


def write_raw_files(tables, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        if name in EXCEL_TABLES:
            path = out_dir / f"{name}.xlsx"
            df.to_excel(path, index=False, sheet_name=name)
        else:
            path = out_dir / f"{name}.csv"
            df.to_csv(path, index=False)
        logger.info("Wrote %s (%d rows)", path.name, len(df))


def build_raw_dataset(out_dir, config=None, corruption_seed=7):
    """Write the messy raw files to out_dir and return the manifest."""
    config = config or SyntheticConfig()
    clean = generate_clean_dataset(config)
    messy, injected = corrupt_dataset(clean, seed=corruption_seed)
    write_raw_files(messy, out_dir)

    manifest = {
        "seed": config.seed,
        "n_customers": config.n_customers,
        "ground_truth": ground_truth(clean),
        "injected_issues": injected,
    }
    (out_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2))
    return manifest
