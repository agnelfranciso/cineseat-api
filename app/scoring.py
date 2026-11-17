import math
from typing import List, Dict, Any, Tuple, Optional

DEFAULTS = {
    "seatW": 0.56,       # seat centre-to-centre, meters
    "rowPitch": 1.05,    # row front-to-back pitch, meters
    "rise": 0.3,         # stadium tier rise per row, meters
    "eye": 1.15,         # seated eye height above row floor, meters
    "firstRow": 0,       # front row to screen, meters (0 = auto from screen width)
    "aspect": 2.39,      # cinema screen aspect ratio (Scope 2.39:1)
    "screenFrac": 0.85,  # screen width as fraction of seating width
}

HEADER_PX = 64
SCREEN_BOTTOM = 1.4
SIDE_AISLE = 1.2
STATUS = {1: 'available', 2: 'sold', 4: 'best', 9: 'picked'}

def deg(r: float) -> float:
    return (r * 180.0) / math.pi

def clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))

def mode(values: List[float]) -> float:
    counts: Dict[float, int] = {}
    best = None
    best_n = 0
    for v in values:
        counts[v] = counts.get(v, 0) + 1
        if counts[v] > best_n:
            best_n = counts[v]
            best = v
    return best if best is not None else 28.0

def build_model(layout: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if cfg is None:
        cfg = DEFAULTS

    row_map: Dict[str, Dict[str, Any]] = {}
    for s in layout.get("seats", []):
        k = f"{s.get('row', '')}@{s.get('y', 0)}"
        if k not in row_map:
            row_map[k] = {"label": s.get("row", ""), "y": s.get("y", 0), "seats": []}
        row_map[k]["seats"].append(s)

    rows = list(row_map.values())
    for r in rows:
        r["seats"].sort(key=lambda a: a.get("x", 0))

    dxs = []
    for r in rows:
        for i in range(1, len(r["seats"])):
            dxs.append(r["seats"][i]["x"] - r["seats"][i - 1]["x"])
    filtered_dxs = [d for d in dxs if d > 2]
    seat_px = mode(filtered_dxs) if filtered_dxs else 28.0

    ys = sorted(list(set(r["y"] for r in rows)))
    dys = []
    for i in range(1, len(ys)):
        dys.append(ys[i] - ys[i - 1])
    filtered_dys = [d for d in dys if d > 4]
    row_px = min(filtered_dys) if filtered_dys else 27.0

    all_x = [s["x"] for s in layout.get("seats", [])]
    min_px = min(all_x) if all_x else 0.0
    max_px = max(all_x) if all_x else 100.0
    mid_y = (ys[0] + ys[-1]) / 2.0 if ys else 0.0
    screen = layout.get("screen")
    screen_below = screen["y"] > mid_y if screen else True
    cx = screen["x"] if screen else (min_px + max_px) / 2.0

    # Front row first
    rows.sort(key=lambda r: -r["y"] if screen_below else r["y"])

    headers = layout.get("headers", [])
    units = 0
    for i, r in enumerate(rows):
        if i > 0:
            p = rows[i - 1]
            lo = min(p["y"], r["y"])
            hi = max(p["y"], r["y"])
            head_px = sum(h.get("h", HEADER_PX) for h in headers if lo < h.get("y", 0) < hi)
            units += max(1, round((hi - lo - head_px) / row_px))
        r["units"] = units
        r["index"] = i

    sign = -1.0 if screen_below else 1.0
    to_x = lambda px: (sign * (px - cx)) / seat_px * cfg["seatW"]
    xa, xb = to_x(min_px), to_x(max_px)
    min_x, max_x = min(xa, xb), max(xa, xb)
    wall_l = min_x - cfg["seatW"] / 2.0 - SIDE_AISLE
    wall_r = max_x + cfg["seatW"] / 2.0 + SIDE_AISLE

    screen_w = cfg["screenFrac"] * (max_x - min_x + cfg["seatW"])
    screen_w = max(4.0, min(screen_w, 2.0 * min(-wall_l, wall_r) - 0.6))
    screen_h = screen_w / cfg["aspect"]
    first_row = cfg["firstRow"] if cfg["firstRow"] > 0 else max(3.5, 0.45 * screen_w)

    seats = []
    by_id = {}
    for r in rows:
        r["z"] = first_row + r["units"] * cfg["rowPitch"]
        r["floor"] = 0.15 + r["units"] * cfg["rise"]
        raw = sorted(r["seats"], key=lambda s: to_x(s["x"]))
        r["seats"] = []
        for i, s in enumerate(raw):
            seat = {
                "id": s["id"],
                "row": r["label"],
                "num": s.get("num", ""),
                "price": s.get("price", 250),
                "type": s.get("type", "Prime"),
                "status": "available" if s.get("status", 1) == 1 else "sold",
                "X": to_x(s["x"]),
                "Z": r["z"],
                "floor": r["floor"],
                "rowRef": r,
                "col": i + 1,
                "index": len(seats),
            }
            r["seats"].append(seat)
            seats.append(seat)
            by_id[seat["id"]] = seat

    last = rows[-1] if rows else {"z": 0.0, "floor": 0.0, "units": 0}
    return {
        "cfg": cfg,
        "rows": rows,
        "seats": seats,
        "byId": by_id,
        "seatPx": seat_px,
        "rowPx": row_px,
        "wallL": wall_l,
        "wallR": wall_r,
        "backZ": last.get("z", 0.0) + 1.6,
        "topFloor": last.get("floor", 0.0),
        "maxUnits": last.get("units", 0),
        "firstRow": first_row,
        "screen": {
            "w": screen_w,
            "h": screen_h,
            "bottom": SCREEN_BOTTOM,
            "cy": SCREEN_BOTTOM + screen_h / 2.0,
        },
        "title": layout.get("title", ""),
        "sub": layout.get("sub", ""),
        "site": layout.get("site", ""),
        "qty": max(1, layout.get("qty", 1)),
        "qtyFixed": bool(layout.get("qtyFixed", False)),
    }

def eye_of(model: Dict[str, Any], seat: Dict[str, Any]) -> Dict[str, float]:
    return {
        "x": seat["X"],
        "y": seat["floor"] + model["cfg"]["eye"],
        "z": seat["Z"]
    }

def seat_metrics(model: Dict[str, Any], seat: Dict[str, Any]) -> Dict[str, Any]:
    screen = model["screen"]
    cfg = model["cfg"]
    e = eye_of(model, seat)
    dy = screen["cy"] - e["y"]
    dist = math.hypot(e["x"], dy, e["z"])

    a1 = math.atan2(-screen["w"] / 2.0 - e["x"], e["z"])
    a2 = math.atan2(screen["w"] / 2.0 - e["x"], e["z"])
    h_angle = deg(a2 - a1)

    ground = math.hypot(e["x"], e["z"])
    look_up = deg(math.atan2(dy, ground))
    look_top = deg(math.atan2(screen["bottom"] + screen["h"] - e["y"], e["z"]))
    off_axis = deg(math.atan2(abs(e["x"]), e["z"]))

    offset = e["x"]
    offset_seats = round(abs(offset) / cfg["seatW"])
    viewing_ratio = dist / screen["w"] if screen["w"] > 0 else 1.0

    # Scoring formulation based on SMPTE 196M & THX cinema standards:
    # 1. Field of View (SMPTE recommends >= 30 deg, optimal 45 deg)
    if h_angle < 30.0:
        s_fill = clamp01((h_angle - 15.0) / 15.0)
    elif h_angle <= 52.0:
        s_fill = 1.0
    else:
        s_fill = clamp01(1.0 - (h_angle - 52.0) / 30.0)

    # 2. Off-Axis displacement (SMPTE/THX recommends < 15 deg from center)
    s_axis = clamp01(1.0 - (off_axis / 32.0) ** 1.2)

    # 3. Vertical Neck Tilt (THX specifies <= 15 deg upward tilt)
    s_neck = 1.0 if look_up <= 6.0 else clamp01(1.0 - (look_up - 6.0) / 24.0)

    # Weighted composite score (0 - 100)
    score = round(100.0 * (0.42 * s_fill + 0.38 * s_axis + 0.20 * s_neck))
    
    if score >= 88:
        verdict = "Best in auditorium — THX reference sweet spot"
        band = "Exceptional"
    elif score >= 75:
        verdict = "Great view — ideal eye-level FOV and alignment"
        band = "Great"
    elif score >= 60:
        verdict = "Good view — comfortable screen perspective"
        band = "Good"
    elif score >= 45:
        verdict = "Fair view — slightly off-center or high angle"
        band = "Fair"
    else:
        verdict = "Poor view — sharp viewing angle or too close"
        band = "Poor"

    return {
        "dist": round(dist, 2),
        "distance": round(dist, 2),
        "hAngle": round(h_angle, 1),
        "screenFOV": round(h_angle, 1),
        "lookUp": round(look_up, 1),
        "lookTop": round(look_top, 1),
        "neckTilt": round(look_top, 1),
        "offAxis": round(off_axis, 1),
        "viewingRatio": round(viewing_ratio, 2),
        "offset": round(offset, 2),
        "offsetSeats": offset_seats,
        "score": score,
        "band": band,
        "verdict": verdict,
    }

def best_block(model: Dict[str, Any], n: int = 1, centre_only: bool = False, not_close: bool = False) -> Tuple[Optional[List[Dict[str, Any]]], float]:
    ranked = rank_all_blocks(model, n=n, centre_only=centre_only, not_close=not_close, top_k=1)
    if ranked:
        return ranked[0]["seats"], ranked[0]["avg_score"]
    return None, 0.0

def rank_all_blocks(
    model: Dict[str, Any],
    n: int = 1,
    centre_only: bool = False,
    not_close: bool = False,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    gap = model["cfg"]["seatW"] * 1.5
    candidates = []

    for row in model["rows"]:
        scores = []
        metrics_list = []
        for s in row["seats"]:
            if s["status"] == "sold":
                scores.append(-1)
                metrics_list.append(None)
            else:
                m = seat_metrics(model, s)
                if centre_only and m["offAxis"] > 14.0:
                    scores.append(-1)
                    metrics_list.append(None)
                elif not_close and m["hAngle"] > 54.0:
                    scores.append(-1)
                    metrics_list.append(None)
                else:
                    scores.append(m["score"])
                    metrics_list.append(m)

        for i in range(len(row["seats"]) - n + 1):
            ok = True
            sum_s = 0
            min_s = 101
            for j in range(i, i + n):
                if scores[j] < 0:
                    ok = False
                    break
                if j > i and (row["seats"][j]["X"] - row["seats"][j - 1]["X"]) > gap:
                    ok = False
                    break
                sum_s += scores[j]
                min_s = min(min_s, scores[j])

            if not ok:
                continue

            avg = sum_s / float(n)
            block_seats = row["seats"][i:i + n]
            center_metric = metrics_list[i + n // 2]
            candidates.append({
                "seats": block_seats,
                "avg_score": round(avg),
                "min_score": min_s,
                "row": row["label"],
                "metric": center_metric
            })

    candidates.sort(key=lambda c: (c["avg_score"], c["min_score"]), reverse=True)
    return candidates[:top_k]
