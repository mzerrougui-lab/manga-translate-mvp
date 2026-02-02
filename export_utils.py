"""
Export utilities: JSON and CSV generation
"""
import json
import pandas as pd
from typing import List, Dict


def export_json(items: List[Dict]) -> str:
    """Export results to JSON string"""
    data = {"items": items}
    return json.dumps(data, ensure_ascii=False, indent=2)


def export_csv(items: List[Dict]) -> str:
    """Export results to CSV string"""
    # Flatten the data for CSV
    rows = []
    for item in items:
        rows.append({
            "index": item.get("index", 0),
            "text": item.get("text", ""),
            "translation": item.get("translation", ""),
            "conf": item.get("conf", 0.0),
            "box": str(item.get("box", []))
        })
    
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def save_json(items: List[Dict], filepath: str) -> None:
    """Save results to JSON file"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(export_json(items))


def save_csv(items: List[Dict], filepath: str) -> None:
    """Save results to CSV file"""
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(export_csv(items))
