"""
Generates an Excalidraw diagram from AgentState.

The diagram is a horizontal swimlane showing the value chain stages as columns,
with company boxes colour-coded by enabler status and Lynch score.

Output: a list of Excalidraw element dicts (pass to create_view or save as .excalidraw).
"""

from __future__ import annotations
import json
import pathlib

from proxy_agent.state import AgentState, LynchScore

# ── Layout constants ──────────────────────────────────────────────────────────
_COL_W = 185        # column width
_COL_GAP = 60       # gap between columns (flow arrow lives here)
_COL_X0 = 10        # x of first column
_HEADER_Y = 58      # top of stage header
_HEADER_H = 46      # stage header height
_ROW_Y0 = 114       # y of first company row
_ROW_H = 38         # company box height
_ROW_GAP = 8        # vertical gap between company boxes
_ROW_STEP = _ROW_H + _ROW_GAP   # 46 px per row
_BOX_PAD = 5        # horizontal padding inside column for company boxes

# Stage header colours (fill, stroke)
_STAGE_COLORS: dict[str, tuple[str, str]] = {
    "Raw Material":             ("#ffd8a8", "#f59e0b"),
    "Manufacturer":             ("#a5d8ff", "#4a9eed"),
    "Component Supplier":       ("#d0bfff", "#8b5cf6"),
    "Distributor / Infrastructure": ("#c3fae8", "#06b6d4"),
    "Service Provider":         ("#b2f2bb", "#22c55e"),
}
# Fallback colours for dynamically generated stage names
_FALLBACK_COLORS = [
    ("#ffd8a8", "#f59e0b"),
    ("#a5d8ff", "#4a9eed"),
    ("#d0bfff", "#8b5cf6"),
    ("#c3fae8", "#06b6d4"),
    ("#b2f2bb", "#22c55e"),
    ("#eebefa", "#ec4899"),
]

# Company box colours
_CLR_ENABLER  = ("#b2f2bb", "#22c55e", 2)   # green
_CLR_STRONG   = ("#fff3bf", "#f59e0b", 2)   # yellow
_CLR_NORMAL   = ("transparent", "#ccc", 1)  # plain


def _col_x(stage_idx: int) -> int:
    return _COL_X0 + stage_idx * (_COL_W + _COL_GAP)


def _company_label(ticker: str, score: LynchScore | None, is_enabler: bool) -> str:
    prefix = "* " if is_enabler else ""
    score_str = f"{score.total}/10" if score else "N/A"
    return f"{prefix}{ticker}  {score_str}"


def _box_colors(is_enabler: bool, score: LynchScore | None) -> tuple[str, str, int]:
    if is_enabler:
        return _CLR_ENABLER
    if score and score.total >= 7:
        return _CLR_STRONG
    return _CLR_NORMAL


def build_elements(state: AgentState) -> list[dict]:
    """Return Excalidraw element list for the given agent state."""
    value_chain = state.get("value_chain", {})
    lynch_scores = state.get("lynch_scores", {})
    enabler_set = set(state.get("enablers", []))
    trend = state.get("trend", "Value Chain")

    stages = list(value_chain.keys())
    n_stages = len(stages)
    if n_stages == 0:
        return []

    # Determine max companies (for background height)
    max_companies = max(len(v) for v in value_chain.values()) if value_chain else 0
    bg_height = _HEADER_H + max_companies * _ROW_STEP + 20

    # Camera: fit all columns + padding
    total_width = _COL_X0 + n_stages * _COL_W + (n_stages - 1) * _COL_GAP + 20
    cam_w = max(800, min(1600, total_width + 40))
    # Snap to 4:3
    cam_h = int(cam_w * 3 / 4)
    cam_x = _COL_X0 - 20

    elements: list[dict] = []
    uid = [0]

    def _id(prefix: str = "e") -> str:
        uid[0] += 1
        return f"{prefix}{uid[0]}"

    # ── Camera & Title ────────────────────────────────────────────────────────
    elements.append({"type": "cameraUpdate", "width": cam_w, "height": cam_h,
                     "x": cam_x, "y": 0})

    title_text = f"{trend} Value Chain — Proxy Investment"
    title_x = cam_x + (cam_w // 2) - len(title_text) * 7
    elements.append({"type": "text", "id": _id("title"), "x": title_x, "y": 8,
                     "text": title_text, "fontSize": 24, "strokeColor": "#1e1e1e"})
    sub_text = "* = Proxy Enabler     Yellow = Lynch Score 7+"
    sub_x = cam_x + (cam_w // 2) - len(sub_text) * 5
    elements.append({"type": "text", "id": _id("sub"), "x": sub_x, "y": 36,
                     "text": sub_text, "fontSize": 17, "strokeColor": "#757575"})

    # ── Stage backgrounds ─────────────────────────────────────────────────────
    for i, stage in enumerate(stages):
        fill, stroke = _STAGE_COLORS.get(stage, _FALLBACK_COLORS[i % len(_FALLBACK_COLORS)])
        cx = _col_x(i)
        elements.append({
            "type": "rectangle", "id": _id("bg"),
            "x": cx, "y": _HEADER_Y, "width": _COL_W, "height": bg_height,
            "backgroundColor": fill, "fillStyle": "solid",
            "strokeColor": stroke, "strokeWidth": 1, "opacity": 30,
        })

    # ── Stage headers ─────────────────────────────────────────────────────────
    for i, stage in enumerate(stages):
        fill, stroke = _STAGE_COLORS.get(stage, _FALLBACK_COLORS[i % len(_FALLBACK_COLORS)])
        cx = _col_x(i)
        fs = 16 if len(stage) > 14 else 18
        elements.append({
            "type": "rectangle", "id": _id("h"),
            "x": cx, "y": _HEADER_Y, "width": _COL_W, "height": _HEADER_H,
            "backgroundColor": fill, "fillStyle": "solid",
            "strokeColor": stroke, "strokeWidth": 2,
            "roundness": {"type": 3},
            "label": {"text": stage, "fontSize": fs},
        })

    # ── Company boxes (drawn left→right, camera follows) ─────────────────────
    # Zoom into left half first, then right
    mid = n_stages // 2
    left_cam_w = (_col_x(mid - 1) + _COL_W + 40) - (cam_x)
    left_cam_w = max(600, min(cam_w, left_cam_w))
    left_cam_h = int(left_cam_w * 3 / 4)
    elements.append({"type": "cameraUpdate", "width": left_cam_w,
                     "height": left_cam_h, "x": cam_x, "y": 0})

    for i, stage in enumerate(stages):
        if i == mid:
            # Pan to right half
            right_x = _col_x(mid) - 30
            right_cam_w = total_width - right_x + 20
            right_cam_w = max(600, min(cam_w, right_cam_w))
            right_cam_h = int(right_cam_w * 3 / 4)
            elements.append({"type": "cameraUpdate", "width": right_cam_w,
                             "height": right_cam_h, "x": right_x, "y": 0})

        cx = _col_x(i)
        companies = value_chain.get(stage, [])
        for j, company in enumerate(companies):
            ticker = company.get("ticker", "").upper()
            is_enabler = ticker in enabler_set or company.get("is_enabler", False)
            score = lynch_scores.get(ticker)
            bg, stroke, sw = _box_colors(is_enabler, score)
            label = _company_label(ticker, score, is_enabler)
            elements.append({
                "type": "rectangle", "id": _id("c"),
                "x": cx + _BOX_PAD, "y": _ROW_Y0 + j * _ROW_STEP,
                "width": _COL_W - _BOX_PAD * 2, "height": _ROW_H,
                "fillStyle": "solid", "backgroundColor": bg,
                "strokeColor": stroke, "strokeWidth": sw,
                "roundness": {"type": 3},
                "label": {"text": label, "fontSize": 15},
            })

    # ── Flow arrows & legend (full view) ─────────────────────────────────────
    elements.append({"type": "cameraUpdate", "width": cam_w, "height": cam_h,
                     "x": cam_x, "y": 0})

    arrow_y = _ROW_Y0 + (max_companies // 2) * _ROW_STEP + _ROW_H // 2
    for i in range(n_stages - 1):
        ax = _col_x(i) + _COL_W + 2
        aw = _COL_GAP - 4
        elements.append({
            "type": "arrow", "id": _id("fa"),
            "x": ax, "y": arrow_y, "width": aw, "height": 0,
            "points": [[0, 0], [aw, 0]],
            "strokeColor": "#aaa", "strokeWidth": 2, "endArrowhead": "arrow",
        })

    # Legend
    legend_y = _HEADER_Y + bg_height + 16
    elements += [
        {"type": "rectangle", "id": _id("legbg"),
         "x": _COL_X0, "y": legend_y, "width": 640, "height": 66,
         "backgroundColor": "#f8f9fa", "fillStyle": "solid",
         "strokeColor": "#dee2e6", "strokeWidth": 1, "roundness": {"type": 3}},
        {"type": "text", "id": _id("lt"), "x": _COL_X0 + 12, "y": legend_y + 6,
         "text": "Legend:", "fontSize": 16, "strokeColor": "#495057"},
        {"type": "rectangle", "id": _id("lb1"),
         "x": _COL_X0 + 72, "y": legend_y + 9, "width": 18, "height": 18,
         "backgroundColor": "#b2f2bb", "fillStyle": "solid",
         "strokeColor": "#22c55e", "strokeWidth": 2},
        {"type": "text", "id": _id("lt1"),
         "x": _COL_X0 + 96, "y": legend_y + 6,
         "text": "* Proxy Enabler — benefits regardless of which brand wins",
         "fontSize": 15, "strokeColor": "#495057"},
        {"type": "rectangle", "id": _id("lb2"),
         "x": _COL_X0 + 72, "y": legend_y + 35, "width": 18, "height": 18,
         "backgroundColor": "#fff3bf", "fillStyle": "solid",
         "strokeColor": "#f59e0b", "strokeWidth": 2},
        {"type": "text", "id": _id("lt2"),
         "x": _COL_X0 + 96, "y": legend_y + 34,
         "text": "Lynch Score 7+ — Strong fundamentals",
         "fontSize": 15, "strokeColor": "#495057"},
    ]

    return elements


def _to_file_format(elements: list[dict]) -> list[dict]:
    """Convert MCP shorthand elements to proper Excalidraw file format.

    The MCP `label` shorthand on shapes is not part of the Excalidraw file spec.
    Each labeled shape must be split into a container element + a bound text element
    with all required fields populated.
    """
    import random

    _seed = random.randint

    def _base(el: dict) -> dict:
        return {
            "angle": 0,
            "strokeColor": el.get("strokeColor", "#1e1e1e"),
            "backgroundColor": el.get("backgroundColor", "transparent"),
            "fillStyle": el.get("fillStyle", "solid"),
            "strokeWidth": el.get("strokeWidth", 2),
            "strokeStyle": el.get("strokeStyle", "solid"),
            "roughness": el.get("roughness", 1),
            "opacity": el.get("opacity", 100),
            "seed": _seed(1, 9_999_999),
            "versionNonce": _seed(1, 9_999_999),
            "isDeleted": False,
            "groupIds": [],
            "frameId": None,
            "updated": 1_700_000_000_000,
            "link": None,
            "locked": False,
        }

    def _bound_text(container_id: str, container: dict, label: dict) -> dict:
        text = label.get("text", "")
        fs = label.get("fontSize", 16)
        w = container["width"] - 8
        h = fs * 1.4
        return {
            "type": "text",
            "id": f"{container_id}_lbl",
            "x": container["x"] + 4,
            "y": container["y"] + (container["height"] - h) / 2,
            "width": w,
            "height": h,
            "angle": 0,
            "strokeColor": label.get("strokeColor", "#1e1e1e"),
            "backgroundColor": "transparent",
            "fillStyle": "solid",
            "strokeWidth": 1,
            "strokeStyle": "solid",
            "roughness": 1,
            "opacity": 100,
            "seed": _seed(1, 9_999_999),
            "versionNonce": _seed(1, 9_999_999),
            "isDeleted": False,
            "groupIds": [],
            "frameId": None,
            "updated": 1_700_000_000_000,
            "link": None,
            "locked": False,
            "text": text,
            "fontSize": fs,
            "fontFamily": 1,
            "textAlign": "center",
            "verticalAlign": "middle",
            "containerId": container_id,
            "originalText": text,
            "lineHeight": 1.25,
            "autoResize": True,
        }

    result: list[dict] = []

    for el in elements:
        el_type = el.get("type")
        if el_type == "cameraUpdate" or el_type == "delete":
            continue

        el_id = el.get("id", f"e{_seed(10000, 99999)}")
        label = el.get("label")

        if el_type in ("rectangle", "ellipse", "diamond"):
            shape = {
                "type": el_type,
                "id": el_id,
                "x": el["x"],
                "y": el["y"],
                "width": el["width"],
                "height": el["height"],
                **_base(el),
            }
            if el.get("roundness"):
                shape["roundness"] = el["roundness"]
            if label:
                shape["boundElements"] = [{"type": "text", "id": f"{el_id}_lbl"}]
                result.append(shape)
                result.append(_bound_text(el_id, el, label))
            else:
                shape["boundElements"] = []
                result.append(shape)

        elif el_type == "text":
            text = el.get("text", "")
            fs = el.get("fontSize", 16)
            result.append({
                "type": "text",
                "id": el_id,
                "x": el["x"],
                "y": el["y"],
                "width": max(10, len(text) * fs * 0.52),
                "height": fs * 1.4,
                **_base(el),
                "text": text,
                "fontSize": fs,
                "fontFamily": 1,
                "textAlign": "left",
                "verticalAlign": "top",
                "containerId": None,
                "originalText": text,
                "lineHeight": 1.25,
                "autoResize": True,
            })

        elif el_type == "arrow":
            points = el.get("points", [[0, 0], [el.get("width", 100), 0]])
            result.append({
                "type": "arrow",
                "id": el_id,
                "x": el["x"],
                "y": el["y"],
                "width": el.get("width", 100),
                "height": el.get("height", 0),
                **_base(el),
                "points": points,
                "lastCommittedPoint": None,
                "startBinding": el.get("startBinding"),
                "endBinding": el.get("endBinding"),
                "startArrowhead": el.get("startArrowhead", None),
                "endArrowhead": el.get("endArrowhead", "arrow"),
                "boundElements": [],
            })

        else:
            result.append({**el, **_base(el)})

    return result


def save_excalidraw(state: AgentState, path: str | pathlib.Path = "output.excalidraw") -> None:
    """Save diagram as an .excalidraw file (importable at excalidraw.com)."""
    elements = _to_file_format(build_elements(state))
    excalidraw_json = {
        "type": "excalidraw",
        "version": 2,
        "source": "https://excalidraw.com",
        "elements": elements,
        "appState": {"viewBackgroundColor": "#ffffff"},
        "files": {},
    }
    pathlib.Path(path).write_text(
        json.dumps(excalidraw_json, indent=2), encoding="utf-8"
    )
