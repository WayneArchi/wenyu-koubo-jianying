#!/usr/bin/env python3
"""Validate source-timed packaging and stage additive native Jianying text JSON.

v2 creates packaging text only. Ordinary captions must be recognized and batch
edited inside Jianying; existing subtitle/text materials are preserved intact.

Never opens or saves a live project. --out must be a new staged file. clip_index
is zero-based; all times are integer source microseconds, on constant 1x cuts.
rough-plan additionally requires canvas: {width, height}. Color is RGB in [0,1],
size is Jianying's native text size, x/y are half-canvas units (positive y up).
The helper checks supplied evidence lexically, not the truth of an Agent's claim.
"""
import argparse
import copy
import hashlib
import json
import math
import sys
import uuid
from pathlib import Path

from audit_plan import audit


MANAGED_KEY = "_wenyu_native_packaging_v2"
LEGACY_KEY = "_wenyu_native_packaging_v1"
TRACK_NAMES = ("Wenyu · 字幕", "Wenyu · 重点花字")
ROLES = {"chapter": 0, "step": 10, "explanation": 20, "comparison": 30, "quote": 40, "emphasis": 50}
PROPERTIES = {"scale": "KFTypeScaleX", "x": "KFTypePositionX", "y": "KFTypePositionY", "rotation": "KFTypeRotation"}
LIMITATIONS = [
    "Evidence matching is lexical; emphasis meaning, importance and reasons were not judged.",
    "No source audio was heard and no phoneme boundaries or subtitle readability were certified.",
    "v2 chapter spans, typography and generic keyframes are candidates; v1 native text/pop smoke tests do not verify v2.",
    "Normal subtitles must be recognized and batch-edited inside Jianying; this helper neither creates nor verifies that recognition.",
    "Native text size is not a proven conversion from the UI 13-point control; shadow is SDK-derived and needs native verification.",
    "A trusted current plaintext draft is required; duration/canvas checks do not prove snapshot identity.",
    "Matching duration/canvas does not prove clip/source mapping; independently cross-check native source/target ranges before registration.",
    "Only a new staged JSON is written; live registration, timeline/meta synchronization and UI save are separate.",
]


class PackagingError(ValueError):
    """An input is unsafe, ambiguous, unsupported or inconsistent."""


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def load_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise PackagingError("Duplicate JSON key: " + key)
            result[key] = value
        return result

    def constant(value):
        raise PackagingError("Non-finite JSON number: " + value)

    try:
        value = json.loads(Path(path).expanduser().read_text(encoding="utf-8"),
                           object_pairs_hook=pairs, parse_constant=constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PackagingError("Cannot read trusted plaintext JSON (encrypted drafts are unsupported): " + str(exc)) from exc
    if not isinstance(value, dict):
        raise PackagingError("Expected a plaintext JSON object; encrypted or encoded drafts are unsupported.")
    try:
        canonical(value)
    except (TypeError, ValueError) as exc:
        raise PackagingError("JSON contains unsupported or non-finite values.") from exc
    return value


def integer(value):
    return type(value) is int


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def lexical(text):
    """Ignore whitespace/punctuation only, retaining letters, digits and CJK."""
    return "".join(char for char in text if char.isalnum())


def check_keys(value, allowed, label):
    unknown = set(value) - set(allowed)
    if unknown:
        raise PackagingError(label + " has unsupported fields: " + ", ".join(sorted(unknown)))


def color(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 3 or not all(
            number(v) and 0 <= v <= 1 for v in value):
        raise PackagingError(label + " must be three finite RGB numbers in [0,1].")
    return list(value)


def style_for(value, role):
    if not isinstance(value, dict):
        raise PackagingError("style must be an object.")
    check_keys(value, ("size", "color", "bold", "x", "y", "border", "shadow", "font"), "style")
    if "size" not in value:
        raise PackagingError("style.size is required; there is no small-font default. Calibrate native size in Jianying: ordinary subtitles UI 12-13, emphasis visibly larger. JSON/UI conversion is not assumed.")
    result = {"color": [1.0, 1.0, 1.0], "bold": role in ("chapter", "emphasis", "step"),
              "x": 0.0, "y": 0.55, "border": None, "shadow": None, "font": "system"}
    result.update(copy.deepcopy(value))
    if not number(result["size"]) or not 1 <= result["size"] <= 100:
        raise PackagingError("style.size must be a finite native size in [1,100]; UI point size is not converted.")
    result["color"] = color(result["color"], "style.color")
    if type(result["bold"]) is not bool:
        raise PackagingError("style.bold must be boolean.")
    if not all(number(result[k]) and -1 <= result[k] <= 1 for k in ("x", "y")):
        raise PackagingError("style.x/y must be finite half-canvas units in [-1,1].")
    border = result["border"]
    if border is not None:
        if not isinstance(border, dict):
            raise PackagingError("style.border is null (no outline) or an object.")
        check_keys(border, ("color", "width", "alpha"), "border")
        border = dict({"color": [0, 0, 0], "width": 0.08, "alpha": 1.0}, **border)
        border["color"] = color(border["color"], "border.color")
        if not all(number(border[k]) and 0 <= border[k] <= 1 for k in ("width", "alpha")):
            raise PackagingError("border.width/alpha must be native finite values in [0,1].")
        result["border"] = border
    shadow = result["shadow"]
    if shadow is not None:
        if not isinstance(shadow, dict):
            raise PackagingError("style.shadow is null or an object.")
        check_keys(shadow, ("alpha", "color", "diffuse", "distance", "angle"), "shadow")
        shadow = dict({"alpha": 1.0, "color": [0, 0, 0], "diffuse": 15, "distance": 5, "angle": -45}, **shadow)
        shadow["color"] = color(shadow["color"], "shadow.color")
        for key, low, high in (("alpha", 0, 1), ("diffuse", 0, 100), ("distance", 0, 100), ("angle", -180, 180)):
            if not number(shadow[key]) or not low <= shadow[key] <= high:
                raise PackagingError("Invalid shadow." + key)
        result["shadow"] = shadow
    font = result["font"]
    if font != "system":
        if not isinstance(font, dict) or set(font) != {"from_material_id"} or not nonempty(font["from_material_id"]):
            raise PackagingError("font supports system or {from_material_id: current native text material id}; names/placeholder paths are unsupported.")
    return result


def highlight_ranges(text, highlights):
    if not isinstance(highlights, list):
        raise PackagingError("highlights must be a list.")
    result = []
    for item in highlights:
        if not isinstance(item, dict):
            raise PackagingError("Each highlight must be an object.")
        check_keys(item, ("word", "color", "bold", "size"), "highlight")
        if not nonempty(item.get("word")):
            raise PackagingError("Each highlight requires a nonempty word.")
        attrs = {k: copy.deepcopy(v) for k, v in item.items() if k != "word"}
        if not attrs:
            raise PackagingError("A highlight requires at least one styling change.")
        if "color" in attrs:
            attrs["color"] = color(attrs["color"], "highlight.color")
        if "bold" in attrs and type(attrs["bold"]) is not bool:
            raise PackagingError("highlight.bold must be boolean.")
        if "size" in attrs and (not number(attrs["size"]) or not 1 <= attrs["size"] <= 100):
            raise PackagingError("highlight.size must be in [1,100].")
        start, found = 0, False
        while True:
            at = text.find(item["word"], start)
            if at < 0:
                break
            end = at + len(item["word"])
            result.append((at, end, attrs))
            start, found = end, True
        if not found:
            raise PackagingError("Highlight word is absent from its text: " + item["word"])
    result.sort(key=lambda x: (x[0], x[1]))
    for previous, current in zip(result, result[1:]):
        if current[0] < previous[1]:
            raise PackagingError("Overlapping or duplicate highlight ranges are ambiguous.")
    return result


def remap_span(span, clips):
    if not isinstance(span, dict):
        raise PackagingError("Each source_spans item must be an object.")
    check_keys(span, ("clip_index", "source_start_us", "source_end_us"), "source span")
    index, start, end = (span.get(k) for k in ("clip_index", "source_start_us", "source_end_us"))
    if not integer(index) or not 0 <= index < len(clips):
        raise PackagingError("clip_index must be a valid zero-based index.")
    if not integer(start) or not integer(end) or start < 0 or end <= start:
        raise PackagingError("Source spans require integer microseconds and positive duration.")
    clip = clips[index]
    if start < clip["source_start_us"] or end > clip["source_end_us"]:
        raise PackagingError("Text crosses a cut boundary or deleted source area; describe retained source_spans.")
    target = clip["target_start_us"] + start - clip["source_start_us"]
    return dict(span, source_id=clip["source_id"], target_start_us=target, duration_us=end - start)


def checked_keyframes(value, duration, motion):
    if not isinstance(value, list):
        raise PackagingError("keyframes must be a list.")
    output, seen = [], set()
    if motion == "pop":
        seen.add("scale")
    for group in value:
        if not isinstance(group, dict):
            raise PackagingError("Each keyframe group must be an object.")
        check_keys(group, ("property", "points"), "keyframe group")
        prop, points = group.get("property"), group.get("points")
        if prop not in PROPERTIES or prop in seen:
            raise PackagingError("Unsupported/duplicate keyframe property or scale conflicts with pop.")
        seen.add(prop)
        if not isinstance(points, list) or len(points) < 2:
            raise PackagingError("A keyframe group requires at least two ordered points.")
        previous = -1
        for point in points:
            if not isinstance(point, dict):
                raise PackagingError("Keyframe point must be an object.")
            check_keys(point, ("time_offset_us", "value"), "keyframe point")
            offset, val = point.get("time_offset_us"), point.get("value")
            if not integer(offset) or not previous < offset < duration:
                raise PackagingError("Keyframe offsets must increase inside the text's one continuous duration.")
            previous = offset
            bounds = {"scale": (0.05, 10), "x": (-1, 1), "y": (-1, 1), "rotation": (-360, 360)}[prop]
            if not number(val) or not bounds[0] <= val <= bounds[1]:
                raise PackagingError("Invalid native keyframe value for " + prop)
        output.append(copy.deepcopy(group))
    return output


def validate_packaging(rough_plan, packaging_plan):
    base = audit(rough_plan)
    if not base["valid_structure"]:
        raise PackagingError("Rough plan failed audit: " + "; ".join(base["errors"]))
    canvas = rough_plan.get("canvas")
    if not isinstance(canvas, dict) or not all(integer(canvas.get(k)) and canvas[k] > 0 for k in ("width", "height")):
        raise PackagingError("rough-plan.canvas requires positive integer width and height.")
    clips = rough_plan["clips"]
    for clip in clips:
        if clip.get("reverse", False) is not False or any(clip.get(k) not in (None, [], {}) for k in ("curve_speed", "speed_curve")):
            raise PackagingError("Only forward constant 1x clips are supported.")
    duration = max(c["target_start_us"] + c["source_end_us"] - c["source_start_us"] for c in clips)
    if "duration_us" in rough_plan and rough_plan["duration_us"] != duration:
        raise PackagingError("rough-plan.duration_us does not match retained clips.")
    if not isinstance(packaging_plan, dict):
        raise PackagingError("packaging-plan must be an object.")
    check_keys(packaging_plan, ("texts", "emphasis", "captions", "checkpoint_end_us"), "packaging-plan (images/SFX are unsupported)")
    if packaging_plan.get("captions", []) != []:
        raise PackagingError("Do not create ordinary-text pseudo-subtitles: recognize subtitles in Jianying and batch-edit them there.")
    events, legacy = packaging_plan.get("texts", []), packaging_plan.get("emphasis", [])
    if not isinstance(events, list) or not isinstance(legacy, list):
        raise PackagingError("texts/emphasis must be lists.")
    if events and legacy:
        raise PackagingError("Use texts or legacy emphasis, not both.")
    events = copy.deepcopy(events or legacy)
    checkpoint = packaging_plan.get("checkpoint_end_us", duration)
    if not integer(checkpoint) or not 0 < checkpoint <= duration:
        raise PackagingError("checkpoint_end_us must be a positive integer within the final timeline.")
    mapped, seen = [], set()
    allowed = {"id", "role", "layer", "source_spans", "clip_index", "source_start_us", "source_end_us", "text",
               "evidence_quote", "reason", "verbatim", "style", "highlights", "motion", "keyframes"}
    for event in events:
        if not isinstance(event, dict):
            raise PackagingError("Each text must be an object.")
        check_keys(event, allowed, "text")
        eid, role = event.get("id"), event.get("role", "emphasis")
        if not nonempty(eid) or eid in seen:
            raise PackagingError("Text ids must be nonempty and globally unique.")
        seen.add(eid)
        if role not in ROLES:
            raise PackagingError("Unsupported role; choose " + ", ".join(ROLES))
        layer = event.get("layer", ROLES[role])
        if not integer(layer) or not 0 <= layer <= 1000:
            raise PackagingError("layer must be an integer in [0,1000].")
        has_spans = "source_spans" in event
        if has_spans and any(k in event for k in ("clip_index", "source_start_us", "source_end_us")):
            raise PackagingError("Use source_spans OR single-clip fields; ambiguous anchors are refused.")
        spans = event["source_spans"] if has_spans else [{k: event.get(k) for k in ("clip_index", "source_start_us", "source_end_us")}]
        if not isinstance(spans, list) or not spans:
            raise PackagingError("source_spans must be a nonempty ordered list.")
        spans = [remap_span(span, clips) for span in spans]
        for previous, current in zip(spans, spans[1:]):
            if current["clip_index"] != previous["clip_index"] + 1 or current["target_start_us"] != previous["target_start_us"] + previous["duration_us"]:
                raise PackagingError("Persistent text source_spans must cover consecutive retained cuts without target gaps or overlaps.")
        start, end = spans[0]["target_start_us"], spans[-1]["target_start_us"] + spans[-1]["duration_us"]
        if end > checkpoint:
            raise PackagingError("Text exceeds checkpoint_end_us; stop packaging at the agreed checkpoint.")
        if not nonempty(event.get("text")) or any(ord(c) > 0xffff for c in event["text"]):
            raise PackagingError("Text must be nonempty BMP text; non-BMP/emoji range indexing needs native verification.")
        if not nonempty(event.get("evidence_quote")) or not nonempty(event.get("reason")):
            raise PackagingError(eid + " requires evidence_quote and reason.")
        speech = "".join(w["text"] for span in spans for w in clips[span["clip_index"]]["word_intervals"]
                         if w["start_us"] < span["source_end_us"] and w["end_us"] > span["source_start_us"])
        evidence = lexical(event["evidence_quote"])
        if not evidence or evidence not in lexical(speech):
            raise PackagingError(eid + " evidence_quote is absent from the supplied overlapping source word text.")
        verbatim = event.get("verbatim", True)
        if type(verbatim) is not bool or (verbatim and (not lexical(event["text"]) or lexical(event["text"]) not in evidence)):
            raise PackagingError(eid + " requires boolean verbatim and original text when verbatim=true.")
        motion = event.get("motion", "none")
        if motion not in ("none", "pop") or (motion == "pop" and end - start < 200000):
            raise PackagingError("Motion supports none or one pop (minimum 200000us), with no preset resources.")
        mapped.append(dict(event, role=role, layer=layer, source_spans=spans, target_start_us=start, duration_us=end-start,
                           verbatim=verbatim, style=style_for(event.get("style", {}), role), motion=motion,
                           highlight_ranges=highlight_ranges(event["text"], event.get("highlights", [])),
                           keyframes=checked_keyframes(event.get("keyframes", []), end-start, motion)))
    if not mapped:
        raise PackagingError("The packaging plan contains no emphasis/chapter text. Use Jianying for ordinary subtitles.")
    mapped.sort(key=lambda e: (e["layer"], e["role"], e["target_start_us"], e["id"]))
    tracks = {}
    for row in mapped:
        tracks.setdefault((row["layer"], row["role"]), []).append(row)
    for rows in tracks.values():
        for previous, current in zip(rows, rows[1:]):
            if current["target_start_us"] < previous["target_start_us"] + previous["duration_us"]:
                raise PackagingError("Texts overlap within the same role/layer track; assign a distinct layer for simultaneous text.")
    return {"valid_structure": True, "ready_for_staging": base["ready_for_native_edit"],
            "continuity_risks": base["continuity_risks"],
            "readiness_blockers": base["readiness_blockers"], "duration_us": duration,
            "checkpoint_end_us": checkpoint, "stop_at_checkpoint": checkpoint < duration,
            "remaining_packaging_status": "not_started" if checkpoint < duration else "not_applicable",
            "canvas": {k: canvas[k] for k in ("width", "height")}, "mapped": {"texts": mapped},
            "ordinary_subtitles_generated": False, "native_subtitle_origin_verified": False,
            "semantic_review_verified": False, "native_ui_verified": False, "limitations": list(LIMITATIONS)}


def identifier(seed, label):
    return uuid.uuid5(uuid.NAMESPACE_URL, "wenyu-packaging-v2:" + seed + ":" + label).hex


def native_styles(event):
    base = event["style"]
    cuts, cursor = [], 0
    for start, end, attrs in event["highlight_ranges"]:
        if cursor < start:
            cuts.append((cursor, start, {}))
        cuts.append((start, end, attrs))
        cursor = end
    if cursor < len(event["text"]):
        cuts.append((cursor, len(event["text"]), {}))
    styles = []
    for start, end, attrs in cuts:
        chosen = dict(base, **attrs)
        style = {"range": [start, end], "size": chosen["size"], "bold": chosen["bold"],
                 "italic": False, "underline": False,
                 "fill": {"alpha": 1.0, "content": {"render_type": "solid", "solid": {"alpha": 1.0, "color": list(chosen["color"])}}},
                 "strokes": []}
        if base["border"] is not None:
            b = base["border"]
            style["strokes"] = [{"content": {"render_type": "solid", "solid": {"alpha": b["alpha"], "color": b["color"]}}, "width": b["width"]}]
        if base["shadow"] is not None:
            sh = base["shadow"]
            style["shadows"] = [{"alpha": sh["alpha"], "diffuse": sh["diffuse"]/600.0, "distance": sh["distance"],
                                  "angle": sh["angle"], "content": {"solid": {"color": sh["color"]}}}]
        if event.get("_native_font") is not None:
            style["font"] = copy.deepcopy(event["_native_font"])
        styles.append(style)
    return styles


def native_text(event, seed, render_index):
    mid = identifier(seed, "material:" + event["id"])
    flag = 7 | (8 if event["style"]["border"] is not None else 0) | (32 if event["style"]["shadow"] is not None else 0)
    material = {"id": mid, "type": "text", "typesetting": 0, "alignment": 1,
                "letter_spacing": 0, "line_spacing": 0.02, "line_feed": 1, "line_max_width": 0.82,
                "force_apply_line_max_width": False, "check_flag": flag, "global_alpha": 1.0,
                "content": json.dumps({"styles": native_styles(event), "text": event["text"]}, ensure_ascii=False, separators=(",", ":"), allow_nan=False)}
    segment = {"id": identifier(seed, "segment:" + event["id"]), "material_id": mid,
               "target_timerange": {"start": event["target_start_us"], "duration": event["duration_us"]},
               "source_timerange": None, "extra_material_refs": [], "common_keyframes": [], "keyframe_refs": [],
               "visible": True, "reverse": False, "speed": 1.0, "volume": 1.0, "last_nonzero_volume": 1.0,
               "is_tone_modify": False, "track_attribute": 0, "track_render_index": 0, "render_index": render_index,
               "enable_adjust": True, "enable_color_correct_adjust": False, "enable_color_curves": True,
               "enable_color_match_adjust": False, "enable_color_wheels": True, "enable_lut": True,
               "enable_smart_color_adjust": False,
               "clip": {"alpha": 1.0, "flip": {"horizontal": False, "vertical": False}, "rotation": 0.0,
                        "scale": {"x": 1.0, "y": 1.0}, "transform": {"x": event["style"]["x"], "y": event["style"]["y"]}},
               "uniform_scale": {"on": True, "value": 1.0}}
    groups = list(event["keyframes"])
    if event["motion"] == "pop":
        groups.insert(0, {"property": "scale", "points": [{"time_offset_us": t, "value": v} for t,v in ((0,.88),(80000,1.06),(160000,1.0))]})
    for group in groups:
        prop = group["property"]
        points = [{"id": identifier(seed, "key:" + event["id"] + ":" + prop + ":" + str(i)),
                   "curveType": "Line", "graphID": "", "time_offset": p["time_offset_us"], "values": [p["value"]],
                   "left_control": {"x": 0.0, "y": 0.0}, "right_control": {"x": 0.0, "y": 0.0}} for i,p in enumerate(group["points"])]
        segment["common_keyframes"].append({"id": identifier(seed, "keylist:" + event["id"] + ":" + prop),
                                             "property_type": PROPERTIES[prop], "material_id": "", "keyframe_list": points})
    return material, segment


def resolve_native_font(event, existing_texts):
    font = event["style"]["font"]
    if font == "system":
        return
    material = next((m for m in existing_texts if m.get("id") == font["from_material_id"]), None)
    if material is None:
        raise PackagingError("Font template material is absent from the trusted current draft.")
    try:
        runs = json.loads(material["content"])["styles"]
        fonts = [r["font"] for r in runs if r.get("font")]
        if not fonts or any(f != fonts[0] for f in fonts[1:]) or not isinstance(fonts[0], dict) or not nonempty(fonts[0].get("id")):
            raise ValueError("No unambiguous native font metadata")
        selected = fonts[0]
        if str(selected.get("path", "")).upper() in ("C:", "D:", "C:/", "D:/"):
            raise ValueError("Placeholder font path")
    except (KeyError, TypeError, ValueError) as exc:
        raise PackagingError("Cannot copy native font; arbitrary names and SDK placeholder paths are unsupported.") from exc
    event["_native_font"] = copy.deepcopy(selected)


def build_packaging(rough_plan, packaging_plan, draft_input):
    report = validate_packaging(rough_plan, packaging_plan)
    if not report["ready_for_staging"]:
        raise PackagingError("Rough plan is not ready: " + "; ".join(report["readiness_blockers"]))
    if not isinstance(draft_input, dict) or not nonempty(draft_input.get("id")):
        raise PackagingError("A trusted current plaintext native draft with id is required.")
    canonical(draft_input)
    if MANAGED_KEY in draft_input or LEGACY_KEY in draft_input:
        raise PackagingError("Managed packaging is already present; explicit migration/resume review is required.")
    if not integer(draft_input.get("duration")) or draft_input["duration"] != report["duration_us"]:
        raise PackagingError("Native draft duration does not match rough plan.")
    canvas = draft_input.get("canvas_config")
    if not isinstance(canvas, dict) or any(type(canvas.get(k)) is not int or canvas[k] != report["canvas"][k] for k in ("width", "height")):
        raise PackagingError("Native draft canvas does not match rough plan.")
    tracks, materials = draft_input.get("tracks"), draft_input.get("materials")
    if not isinstance(tracks, list) or not all(isinstance(t, dict) for t in tracks) or not isinstance(materials, dict):
        raise PackagingError("Native tracks/materials shape is invalid.")
    if any(not isinstance(t.get("segments"), list) or not all(isinstance(s,dict) for s in t["segments"]) for t in tracks):
        raise PackagingError("Native segment lists are invalid.")
    if any(t.get("name") in TRACK_NAMES or str(t.get("name", "")).startswith("Wenyu v2 ·") for t in tracks):
        raise PackagingError("Managed track name conflict; do not duplicate old packaging or captions.")
    if "texts" in materials and not isinstance(materials["texts"], list):
        raise PackagingError("Native materials.texts must be a list.")
    existing_texts = materials.get("texts", [])
    if not all(isinstance(m, dict) for m in existing_texts):
        raise PackagingError("Native text materials must be objects.")
    result = copy.deepcopy(draft_input)
    result["materials"].setdefault("texts", [])
    seed = digest({"draft": draft_input, "rough": rough_plan, "packaging": packaging_plan})
    indices = [0]
    for track in tracks:
        if integer(track.get("render_index")):
            indices.append(track["render_index"])
        indices.extend(s["render_index"] for s in track["segments"] if integer(s.get("render_index")))
    next_index = max(15000, max(indices)+1)
    by_track = {}
    for event in report["mapped"]["texts"]:
        by_track.setdefault((event["layer"], event["role"]), []).append(event)
    generated_tracks, generated_materials = [], []
    for offset, ((layer, role), rows) in enumerate(sorted(by_track.items())):
        name = "Wenyu v2 · {} · L{}".format(role, layer)
        track = {"id": identifier(seed, "track:" + name), "name": name, "type": "text", "attribute": 0,
                 "flag": 0, "is_default_name": False, "segments": []}
        for event in rows:
            native_event = copy.deepcopy(event)
            resolve_native_font(native_event, existing_texts)
            material, segment = native_text(native_event, seed, next_index+offset)
            result["materials"]["texts"].append(material)
            generated_materials.append(material["id"])
            track["segments"].append(segment)
        result["tracks"].append(track)
        generated_tracks.append(track["id"])
    result[MANAGED_KEY] = {"schema_version": 2, "rough_plan_sha256": digest(rough_plan), "packaging_plan_sha256": digest(packaging_plan),
                           "source_draft_sha256": digest(draft_input), "managed_track_ids": generated_tracks,
                           "managed_text_material_ids": generated_materials, "ordinary_subtitles_generated": False,
                           "checkpoint_end_us": report["checkpoint_end_us"], "stop_at_checkpoint": report["stop_at_checkpoint"],
                           "remaining_packaging_status": report["remaining_packaging_status"], "native_ui_verified": False,
                           "semantic_review_verified": False, "text_evidence": [
                               {k:e[k] for k in ("id","role","layer","source_spans","target_start_us","duration_us","text","evidence_quote","reason","verbatim")}
                               for e in report["mapped"]["texts"]]}
    report["preserved_existing_text_tracks"] = sum(t.get("type") in ("text","subtitle") for t in tracks)
    report["new_packaging_tracks"] = len(generated_tracks)
    return result, report


def write_staged(path, value, input_path=None):
    """Exclusive create; never truncate or overwrite an existing file/symlink."""
    path = Path(path).expanduser()
    resolved = path.resolve()
    if input_path is not None and resolved == Path(input_path).expanduser().resolve():
        raise PackagingError("Output cannot be the input draft.")
    if resolved.name in ("draft_info.json", "draft_content.json", "draft_meta_info.json") or "com.lveditor.draft" in resolved.parts:
        raise PackagingError("Output must be a staged filename outside the live native draft directory.")
    data = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(data)
    except OSError as exc:
        raise PackagingError("Cannot create a NEW staged output: " + str(exc)) from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rough-plan", type=Path, required=True)
    parser.add_argument("--packaging-plan", type=Path, required=True)
    parser.add_argument("--draft-input", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if args.validate_only and (args.draft_input is not None or args.out is not None):
        parser.error("--validate-only takes neither --draft-input nor --out")
    if not args.validate_only and (args.draft_input is None or args.out is None):
        parser.error("staging requires both --draft-input and --out")
    try:
        rough, packaging = load_json(args.rough_plan), load_json(args.packaging_plan)
        if args.validate_only:
            report = validate_packaging(rough, packaging)
        else:
            result, report = build_packaging(rough, packaging, load_json(args.draft_input))
            write_staged(args.out, result, args.draft_input)
            report["staged_output"] = str(args.out.expanduser().resolve())
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if report["ready_for_staging"] else 2
    except (PackagingError, ValueError, TypeError) as exc:
        print(json.dumps({"valid_structure": False, "ready_for_staging": False,
                          "errors": [str(exc)], "limitations": LIMITATIONS}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main())
