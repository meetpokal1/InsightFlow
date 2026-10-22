"""Create the messy raw input files in data/raw/.

Examples:
    python scripts/generate_synthetic_data.py
    python scripts/generate_synthetic_data.py --customers 300 --seed 1 --out /tmp/raw
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import get_settings  # noqa: E402
from src.logging_config import setup_logging  # noqa: E402
from src.synthetic.build import build_raw_dataset  # noqa: E402
from src.synthetic.generator import SyntheticConfig  # noqa: E402


def main():
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Generate messy synthetic raw data")
    parser.add_argument("--out", type=Path, default=settings.raw_data_dir, help="output folder")
    parser.add_argument("--customers", type=int, default=800, help="number of customers")
    parser.add_argument("--seed", type=int, default=42, help="same seed gives the same data")
    args = parser.parse_args()

    setup_logging(settings.log_level)
    config = SyntheticConfig(seed=args.seed, n_customers=args.customers)
    manifest = build_raw_dataset(args.out, config)

    injected = sum(sum(counts.values()) for counts in manifest["injected_issues"].values())
    print(f"Raw files written to {args.out} ({injected} data problems injected)")
    print("Clean-data totals:", manifest["ground_truth"])


if __name__ == "__main__":
    main()
