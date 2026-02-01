"""
OCR utilities: reading order sorting and text box merging
"""
from typing import List, Dict, Tuple


def box_to_rect(box: List[List[float]]) -> Tuple[float, float, float, float]:
    """Convert 4-point box to rectangle (x1, y1, x2, y2)"""
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return min(xs), min(ys), max(xs), max(ys)


def rect_center(rect: Tuple[float, float, float, float]) -> Tuple[float, float]:
    """Get center point of rectangle"""
    x1, y1, x2, y2 = rect
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def sort_reading_order(items: List[Dict]) -> List[Dict]:
    """
    Sort OCR results in reading order (top-to-bottom, left-to-right within rows).
    Uses a simple bucket-based approach.
    """
    if not items:
        return items
    
    # Get centers
    centers = [((rect_center(box_to_rect(it["box"]))), it) for it in items]
    
    # Calculate row bucket size
    ys = [c[0][1] for c in centers]
    y_span = max(ys) - min(ys) if ys else 1.0
    row_bucket = max(12.0, y_span / 20.0)
    
    def row_key(y):
        return int(y // row_bucket)
    
    # Group into rows
    buckets = {}
    for (cx, cy), it in centers:
        buckets.setdefault(row_key(cy), []).append(((cx, cy), it))
    
    # Sort each row by x-coordinate
    ordered = []
    for rk in sorted(buckets.keys()):
        row_sorted = sorted(buckets[rk], key=lambda t: t[0][0])
        ordered.extend([it for _, it in row_sorted])
    
    return ordered


def merge_nearby_boxes(items: List[Dict], threshold: float = 50.0) -> List[Dict]:
    """
    Optionally merge OCR boxes that are very close together.
    Simple heuristic: if two boxes are within threshold pixels horizontally and
    on the same row, merge them.
    """
    if not items or len(items) <= 1:
        return items
    
    merged = []
    skip = set()
    
    for i, item in enumerate(items):
        if i in skip:
            continue
        
        rect_i = box_to_rect(item["box"])
        cx_i, cy_i = rect_center(rect_i)
        
        # Look for mergeable boxes
        to_merge = [item]
        
        for j in range(i + 1, len(items)):
            if j in skip:
                continue
            
            rect_j = box_to_rect(items[j]["box"])
            cx_j, cy_j = rect_center(rect_j)
            
            # Same row and close horizontally?
            if abs(cy_i - cy_j) < threshold / 2 and abs(cx_i - cx_j) < threshold * 2:
                to_merge.append(items[j])
                skip.add(j)
        
        if len(to_merge) == 1:
            merged.append(item)
        else:
            # Merge text and boxes
            merged_text = " ".join([it["text"] for it in to_merge])
            all_boxes = [box_to_rect(it["box"]) for it in to_merge]
            
            x1 = min([b[0] for b in all_boxes])
            y1 = min([b[1] for b in all_boxes])
            x2 = max([b[2] for b in all_boxes])
            y2 = max([b[3] for b in all_boxes])
            
            merged_box = [
                [x1, y1],
                [x2, y1],
                [x2, y2],
                [x1, y2]
            ]
            
            avg_conf = sum([it["conf"] for it in to_merge]) / len(to_merge)
            
            merged.append({
                "text": merged_text,
                "box": merged_box,
                "conf": avg_conf
            })
    
    return merged
