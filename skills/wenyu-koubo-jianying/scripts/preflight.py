#!/usr/bin/env python3
"""Read-only dependency inventory and optional media probe; no credentials read."""
import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

CORE_SKILLS = ("volcengine-audio-transcription", "jianying-editor")
OPTIONAL_SKILLS = ("dbs-content", "dbs-title-cover-intro",
                   "dbs-beta-compress-without-loss", "dbs-script-flow")


def path_status(path):
    return {"path": str(path), "exists": path.exists(),
            "is_directory": path.is_dir(), "is_symlink": path.is_symlink(),
            "broken_symlink": path.is_symlink() and not path.exists()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--skills-root", type=Path, action="append", default=[])
    parser.add_argument("--draft-root", type=Path)
    args = parser.parse_args()
    roots = [Path.home() / x / "skills" for x in (".agents", ".codex", ".workbuddy")]
    roots = list(dict.fromkeys(p.expanduser().absolute() for p in roots + args.skills_root))
    tools = {name: shutil.which(name) for name in ("ffmpeg", "ffprobe")}
    skills = {}
    for name in CORE_SKILLS + OPTIONAL_SKILLS:
        candidates = []
        for root in roots:
            path = root / name
            candidate = path_status(path)
            candidate["skill_file_exists"] = (path / "SKILL.md").is_file()
            candidate["skill_file_broken_symlink"] = ((path / "SKILL.md").is_symlink()
                                                        and not (path / "SKILL.md").exists())
            candidates.append(candidate)
        skills[name] = {"required": name in CORE_SKILLS, "candidates": candidates,
                        "present": any(p["skill_file_exists"] for p in candidates)}
    errors = []
    python_ok = sys.version_info >= (3, 9)
    if not python_ok:
        errors.append("Python 3.9 or newer is required.")
    for name, path in tools.items():
        if not path:
            errors.append(name + " was not found on PATH.")
    for name in CORE_SKILLS:
        if not skills[name]["present"]:
            errors.append(name + "/SKILL.md was not found.")
    result = {"python": {"version": platform.python_version(), "executable": sys.executable,
                         "version_supported": python_ok}, "tools": tools, "skills": skills,
              "limitations": ["Existence checks do not validate tool quality, credentials, service access, or native editing readiness.",
                              "Choose audio by listening and source context; channel count does not identify the correct track."]}
    if args.draft_root:
        result["draft_root"] = path_status(args.draft_root.expanduser().absolute())
        if not result["draft_root"]["is_directory"]:
            errors.append("The supplied draft root is not an existing directory.")
    if args.source:
        source = args.source.expanduser().absolute()
        result["source"] = path_status(source)
        if not source.is_file():
            errors.append("The supplied source is not an existing file.")
        elif tools["ffprobe"]:
            try:
                proc = subprocess.run([tools["ffprobe"], "-v", "error", "-show_streams",
                                       "-show_format", "-of", "json", str(source)],
                                      capture_output=True, text=True, timeout=30)
                if proc.returncode:
                    errors.append("ffprobe failed (exit {}).".format(proc.returncode))
                else:
                    probe = json.loads(proc.stdout)
                    streams = []
                    for stream in probe.get("streams", []):
                        item = {k: stream.get(k) for k in ("index", "codec_type", "codec_name",
                                "sample_rate", "channels", "channel_layout", "avg_frame_rate",
                                "r_frame_rate", "width", "height", "duration", "start_time")}
                        item["default"] = stream.get("disposition", {}).get("default", 0)
                        item["rotation"] = stream.get("tags", {}).get("rotate")
                        for side in stream.get("side_data_list", []):
                            if "rotation" in side:
                                item["rotation"] = side["rotation"]
                        streams.append(item)
                    result["media"] = {"streams": streams, "duration": probe.get("format", {}).get("duration"),
                                       "start_time": probe.get("format", {}).get("start_time"),
                                       "selected_audio_stream": None, "audio_selection_requires_judgment": True}
            except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
                errors.append("ffprobe could not complete: " + type(exc).__name__)
    result["errors"] = errors
    result["core_environment_present"] = python_ok and all(tools.values()) and all(skills[n]["present"] for n in CORE_SKILLS)
    result["requested_checks_passed"] = not errors
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
