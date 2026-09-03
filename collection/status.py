import os
import glob
import json
import pandas as pd

DATA_DIR = "/Users/scrape/data/raw"

def get_status():
    files = glob.glob(os.path.join(DATA_DIR, "attempts_*.jsonl"))
    if not files:
        print("[-] No attempt logs found yet. Run collector.py first.")
        return

    records = []
    for f in files:
        with open(f, "r") as fp:
            for line in fp:
                if line.strip():
                    records.append(json.loads(line))
                    
    df = pd.DataFrame(records)
    total_cells = len(df)
    success = len(df[df["outcome_code"] == "SUCCESS"])
    coverage = (success / total_cells * 100) if total_cells > 0 else 0
    
    print("\n" + "=" * 50)
    print("           COLLECTOR STATUS REPORT")
    print("=" * 50)
    print(f"Total Cells Attempted : {total_cells}")
    print(f"Successful Collections: {success}")
    print(f"Coverage Rate         : {coverage:.2f}%")
    print("\nOutcome Breakdown:")
    print(df["outcome_code"].value_counts().to_string())
    print("=" * 50)

if __name__ == "__main__":
    get_status()