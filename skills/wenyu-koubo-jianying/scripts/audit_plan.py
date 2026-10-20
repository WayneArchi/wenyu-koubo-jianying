#!/usr/bin/env python3
"""Audit a JSON cut plan. Word times are absolute source microseconds, not clip offsets."""
import argparse
import json
import sys
from pathlib import Path


def integer(value):
    return type(value) is int


def audit(plan, require_listening=False):
    errors, blockers = [], []
    if not isinstance(plan, dict):
        errors.append("Plan must be a JSON object.")
        plan = {}
    sources = plan.get("sources")
    durations, seen_ids = {}, set()
    if not isinstance(sources, list) or not sources:
        errors.append("sources must be a nonempty list.")
        sources = []
    for i, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append("sources[{}] must be an object.".format(i))
            continue
        sid, duration = source.get("id"), source.get("duration_us")
        if not isinstance(sid, str) or not sid.strip() or sid in seen_ids:
            errors.append("sources[{}] has a missing, empty, or duplicate id.".format(i))
        else:
            seen_ids.add(sid)
            if not integer(duration) or duration <= 0:
                errors.append("sources[{}].duration_us must be a positive integer.".format(i))
            else:
                durations[sid] = duration
    clips = plan.get("clips")
    if not isinstance(clips, list) or not clips:
        errors.append("clips must be a nonempty list.")
        clips = []
    target_end, source_ranges = 0, {}
    for i, clip in enumerate(clips):
        label = "clips[{}]".format(i)
        if not isinstance(clip, dict):
            errors.append(label + " must be an object.")
            continue
        sid = clip.get("source_id")
        speed = clip.get("speed", 1)
        if type(speed) not in (int, float) or speed != 1:
            errors.append(label + " has unsupported speed; this auditor only supports constant 1x clips.")
        start, end, target = [clip.get(k) for k in ("source_start_us", "source_end_us", "target_start_us")]
        times_ok = all(integer(v) for v in (start, end, target))
        if not times_ok or start < 0 or end <= start or target < 0:
            errors.append(label + " requires integer, nonnegative starts and positive duration.")
            times_ok = False
        if not isinstance(sid, str) or sid not in durations:
            errors.append(label + " refers to an unknown source.")
        elif times_ok:
            if end > durations[sid]:
                errors.append(label + " exceeds the source duration.")
            source_ranges.setdefault(sid, []).append((start, end, i))
        if times_ok:
            if target != target_end:
                errors.append(label + " target timeline must be contiguous from zero.")
            target_end = target + end - start
        if clip.get("speaker_status") not in ("confirmed_target", "single_speaker_confirmed"):
            errors.append(label + " speaker_status is not confirmed.")
        words = clip.get("word_intervals")
        if not isinstance(words, list) or not words:
            errors.append(label + ".word_intervals must be a nonempty list.")
            words = []
        previous_end = None
        for j, word in enumerate(words):
            wlabel = label + ".word_intervals[{}]".format(j)
            if not isinstance(word, dict):
                errors.append(wlabel + " must be an object.")
                continue
            ws, we = word.get("start_us"), word.get("end_us")
            if not integer(ws) or not integer(we) or ws < 0 or we <= ws:
                errors.append(wlabel + " requires integer times and positive duration.")
                continue
            if not isinstance(word.get("text"), str) or not word["text"].strip():
                errors.append(wlabel + " requires nonempty text.")
            if times_ok and (ws < start or we > end):
                errors.append(wlabel + " crosses a cut boundary (zero tolerance).")
            if previous_end is not None and ws < previous_end:
                errors.append(wlabel + " overlaps or is out of chronological order.")
            previous_end = we
    for sid, ranges in source_ranges.items():
        ranges.sort()
        for previous, current in zip(ranges, ranges[1:]):
            if current[0] < previous[1]:
                errors.append("Source {} has overlapping retained clip ranges.".format(sid))
    for flag in ("approved", "speaker_identity_confirmed"):
        if type(plan.get(flag)) is not bool:
            errors.append(flag + " must be a boolean.")
    if "full_listening_review" in plan and type(plan["full_listening_review"]) is not bool:
        errors.append("full_listening_review must be a boolean when present.")
    reference = plan.get("approval_reference")
    if not isinstance(reference, str):
        errors.append("approval_reference must be a string.")
    if plan.get("approved") is not True:
        blockers.append("User approval is required.")
    if not isinstance(reference, str) or not reference.strip():
        blockers.append("A nonempty approval_reference is required.")
    if plan.get("speaker_identity_confirmed") is not True:
        blockers.append("Speaker identity confirmation is required.")
    listening = plan.get("full_listening_review") is True
    if require_listening and not listening:
        blockers.append("A full_listening_review claim is required by --require-listening.")
    return {"valid_structure": not errors, "ready_for_native_edit": not errors and not blockers,
            "listening_claim_received": listening, "listening_required": require_listening,
            "errors": errors, "readiness_blockers": blockers,
            "limitations": ["Only the supplied intervals and claims were checked; omitted ASR words cannot be detected.",
                            "No audio was heard, cuts created, real phoneme boundaries certified, or quality pass granted.",
                            "Approval references and listening claims require independent human verification."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--require-listening", action="store_true")
    args = parser.parse_args()
    try:
        def reject_constant(value):
            raise ValueError("Non-finite JSON number: " + value)
        plan = json.loads(args.plan.expanduser().read_text(encoding="utf-8"), parse_constant=reject_constant)
        result = audit(plan, args.require_listening)
    except (OSError, UnicodeError, ValueError) as exc:
        result = {"valid_structure": False, "ready_for_native_edit": False,
                  "listening_claim_received": False, "errors": ["Could not read plan: " + str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if result["ready_for_native_edit"] else 2


if __name__ == "__main__":
    sys.exit(main())
