#!/usr/bin/env python3
"""Read-only local inventory; no network, conversion, upload or APK export."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

# From EditorTools GameVersion.cs, pinned in upstream-lock.json.
KNOWN_DATABASES = {
    "2060B40B8CBE5B8D": "3.0.0.x / V3_0_00_89",
    "641AD1D48E1FD7EC": "4.0.02.4x / V4_0_02_43",
}
MAX_XML_BYTES = 4 * 1024 * 1024
MAX_XML_DOCUMENTS = 2000

def inventory(root, inspect_xml=False):
    """Never follows symlinks. Counts are not evidence of engine compatibility."""
    counts = Counter()
    roots = Counter()
    objectives = Counter()
    errors = 0
    skipped_links = 0
    xml_checked = 0
    xml_skipped = 0
    total_bytes = 0

    def walk_error(_error):
        nonlocal errors
        errors += 1

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        keep = []
        for name in dirs:
            if (Path(directory) / name).is_symlink():
                skipped_links += 1
            else:
                keep.append(name)
        dirs[:] = keep
        for name in names:
            path = Path(directory) / name
            if path.is_symlink():
                skipped_links += 1
                continue
            try:
                size = path.stat().st_size
                extension = path.suffix.lower() or "(none)"
                counts[extension] += 1
                total_bytes += size
                if inspect_xml and extension == ".xdb":
                    if size > MAX_XML_BYTES or xml_checked >= MAX_XML_DOCUMENTS:
                        xml_skipped += 1
                        continue
                    payload = path.read_bytes()
                    # Reject DTD/entity declarations, including UTF-16 spellings.
                    check = payload.replace(b"\x00", b"").upper()
                    if b"<!DOCTYPE" in check or b"<!ENTITY" in check:
                        xml_skipped += 1
                        continue
                    document = ET.fromstring(payload)
                    xml_checked += 1
                    roots[document.tag.rsplit("}", 1)[-1]] += 1
                    for element in document.iter():
                        kind = element.attrib.get("type", "").rsplit(".", 1)[-1]
                        if kind in ("QuestCountItem", "QuestCountKill", "QuestCountSpecial"):
                            objectives[kind] += 1
            except (OSError, ET.ParseError, ValueError):
                errors += 1
    return {
        "extensions": dict(sorted(counts.items())),
        "bytes": total_bytes,
        "read_or_parse_errors": errors,
        "symlinks_skipped": skipped_links,
        "xml_checked": xml_checked,
        "xml_skipped": xml_skipped,
        "xml_root_types": dict(sorted(roots.items())),
        "objective_occurrences": dict(sorted(objectives.items())),
        "compatibility_verified": False,
    }

def audit_client(root):
    project = root / "project.godot"
    if not project.is_file():
        return {"project_found": False, "android_ready": False}
    text = project.read_text(encoding="utf-8-sig")
    quic = False
    touch = False
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in
                   (".git", ".godot", "converted", "upscaled", "bin", "obj")
                   and not (Path(directory) / d).is_symlink()]
        for name in names:
            path = Path(directory) / name
            if path.is_symlink() or path.suffix.lower() not in (".cs", ".gd"):
                continue
            code = path.read_text(encoding="utf-8-sig", errors="replace")
            quic |= "System.Net.Quic" in code
            touch |= any(token in code for token in
                         ("InputEventScreenTouch", "InputEventScreenDrag"))
    presets = root / "export_presets.cfg"
    preset_text = presets.read_text(encoding="utf-8-sig") if presets.is_file() else ""
    return {
        "project_found": True,
        "forward_plus_declared": "Forward Plus" in text,
        "system_net_quic_reference": quic,
        "touch_event_tokens_found": touch,
        "android_preset_found": bool(re.search(r'platform\s*=\s*"Android"', preset_text)),
        "android_ready": False,
        "note": "Static signals only; a preset or touch token does not prove a working port.",
    }

def within(path, parent):
    return path == parent or parent in path.parents

def write_report(path, report, inputs, repository):
    path = path.resolve()
    forbidden = [repository.resolve()] + [root.resolve() for root in inputs]
    if any(within(path, root) for root in forbidden):
        raise ValueError("Report must be outside this repository and all input trees.")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Never replace an existing file or follow an existing output symlink.
    with path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Owned installation or extracted XDB tree")
    parser.add_argument("--converted", type=Path, help="Existing converter output, if available")
    parser.add_argument("--client", type=Path, help="Local SarnautCore client source")
    parser.add_argument("--inspect-xdb", action="store_true",
                        help="Inspect up to 2000 XDB documents, each <=4 MiB")
    parser.add_argument("--out", required=True, type=Path, help="New local JSON outside repositories")
    args = parser.parse_args(argv)
    inputs = [p.resolve() for p in (args.source, args.converted, args.client) if p]
    if not inputs:
        parser.error("Provide at least one input tree.")
    if any(not p.is_dir() for p in inputs):
        parser.error("Every input must be an existing directory.")
    report = {
        "schema": 1,
        "mode": "local-read-only-inventory",
        "paths_and_file_contents_included": False,
        "known_editor_database_hashes": KNOWN_DATABASES,
        "installed_version_verified": False,
        "godot_conversion_verified": False,
        "apk_verified": False,
        "notes": [
            "Identify the actual database using EditorCLI pack info <Bin> pack.bin.",
            "No database hash is inferred from a folder name or filename.",
            "A successful XDB extraction is not a Godot geometry/animation conversion.",
            "SarnautCore classic-1.1 behavior is not proof of Allods 3.x/4.x behavior.",
            "Keep source data, converted assets and this report local.",
        ],
    }
    try:
        if args.source:
            report["source"] = inventory(args.source, args.inspect_xdb)
        if args.converted:
            report["converted"] = inventory(args.converted)
        if args.client:
            report["client"] = audit_client(args.client)
        repository = Path(__file__).resolve().parents[2]
        write_report(args.out, report, inputs, repository)
    except (OSError, ValueError):
        print("Audit failed: check input access and use a NEW report path outside input trees and this repository.",
              file=sys.stderr)
        return 2
    print("Local report created. No game files were changed or uploaded. Compatibility remains unverified.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
