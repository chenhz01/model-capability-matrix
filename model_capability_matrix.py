#!/usr/bin/env python3
"""model-capability-matrix: versioned capability declarations for AI models.

A matrix is a JSON document (JSON is a subset of YAML 1.2) declaring typed
capabilities per model. The tool validates matrices, merges overlays with
conflict detection, diffs two versions, enforces monotonic versioning, and
exports a Markdown table.
"""
from __future__ import annotations

import argparse
import json
import sys

__version__ = "0.1.1"

_CAPABILITIES = {
    "context_window": "int_positive",
    "max_output": "int_positive",
    "vision": "bool",
    "tools": "bool",
    "streaming": "bool",
    "fine_tuning": "bool",
    "json_mode": ("enum", ("strict", "lax", "none")),
}


class MatrixError(ValueError):
    """Raised when a matrix document violates the schema."""


def _check_capability(name, value):
    spec = _CAPABILITIES.get(name)
    if spec is None:
        raise MatrixError("unknown capability: %s" % name)
    if spec == "int_positive":
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise MatrixError("capability %s must be a positive integer, got %r" % (name, value))
    elif spec == "bool":
        if not isinstance(value, bool):
            raise MatrixError("capability %s must be a boolean, got %r" % (name, value))
    else:
        allowed = spec[1]
        if value not in allowed:
            raise MatrixError("capability %s must be one of %s, got %r"
                              % (name, "/".join(allowed), value))


def _version_tuple(version):
    if not isinstance(version, str) or not version:
        raise MatrixError("matrix_version must be a non-empty string")
    parts = version.split(".")
    if not all(p.isdigit() for p in parts):
        raise MatrixError("matrix_version must be dot-separated integers, got %r" % version)
    return tuple(int(p) for p in parts)


def load_matrix(data):
    """Load and validate a matrix from a JSON string or a parsed dict."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError as exc:
            raise MatrixError("matrix is not valid JSON: %s" % exc) from None
    if not isinstance(data, dict):
        raise MatrixError("matrix must be a JSON object, got %s" % type(data).__name__)
    version = data.get("matrix_version")
    _version_tuple(version)
    models = data.get("models")
    if not isinstance(models, dict) or not models:
        raise MatrixError("matrix.models must be a non-empty object")
    clean = {}
    for model, entry in models.items():
        if not isinstance(entry, dict):
            raise MatrixError("model %s: entry must be an object" % model)
        caps = entry.get("capabilities")
        if not isinstance(caps, dict) or not caps:
            raise MatrixError("model %s: capabilities must be a non-empty object" % model)
        for cap, value in caps.items():
            _check_capability(cap, value)
        clean[model] = {"capabilities": dict(caps)}
        for optional in ("as_of", "source"):
            if optional in entry:
                if not isinstance(entry[optional], str):
                    raise MatrixError("model %s: %s must be a string" % (model, optional))
                clean[model][optional] = entry[optional]
    return {"matrix_version": version, "models": clean}


def _entry_copy(entry):
    return {"capabilities": dict(entry["capabilities"]),
            **{k: entry[k] for k in ("as_of", "source") if k in entry}}


def merge_matrices(base, overlay):
    """Overlay wins. Returns (merged_matrix, conflicts) where conflicts lists
    same model+capability pairs whose values disagree."""
    conflicts = []
    merged_models = {m: _entry_copy(e) for m, e in base["models"].items()}
    for model, entry in overlay["models"].items():
        if model in merged_models:
            for cap, value in entry["capabilities"].items():
                if cap in merged_models[model]["capabilities"] \
                        and merged_models[model]["capabilities"][cap] != value:
                    conflicts.append({"model": model, "capability": cap,
                                      "base_value": merged_models[model]["capabilities"][cap],
                                      "overlay_value": value})
            merged_models[model]["capabilities"].update(entry["capabilities"])
            for key in ("as_of", "source"):
                if key in entry:
                    merged_models[model][key] = entry[key]
        else:
            merged_models[model] = _entry_copy(entry)
    return {"matrix_version": overlay["matrix_version"], "models": merged_models}, conflicts


def detect_conflicts(base, overlay):
    _, conflicts = merge_matrices(base, overlay)
    return conflicts


def check_version_monotonic(old_version, new_version):
    if _version_tuple(new_version) < _version_tuple(old_version):
        raise MatrixError("version downgrade: %s -> %s" % (old_version, new_version))
    return True


def diff_matrices(old, new):
    old_t = _version_tuple(old["matrix_version"])
    new_t = _version_tuple(new["matrix_version"])
    added = sorted(set(new["models"]) - set(old["models"]))
    removed = sorted(set(old["models"]) - set(new["models"]))
    changed = []
    for model in sorted(set(old["models"]) & set(new["models"])):
        old_caps = old["models"][model]["capabilities"]
        new_caps = new["models"][model]["capabilities"]
        for cap in sorted(set(old_caps) | set(new_caps)):
            ov, nv = old_caps.get(cap), new_caps.get(cap)
            if ov != nv:
                changed.append({"model": model, "capability": cap, "old": ov, "new": nv})
    return {"version_old": old["matrix_version"], "version_new": new["matrix_version"],
            "version_downgrade": new_t < old_t, "added": added, "removed": removed,
            "changed": changed}


def query(matrix, model, capability):
    entry = matrix["models"].get(model)
    if entry is None:
        return None
    return entry["capabilities"].get(capability)


def export_table(matrix):
    caps = []
    for entry in matrix["models"].values():
        for cap in entry["capabilities"]:
            if cap not in caps:
                caps.append(cap)
    caps.sort()
    header = "| model | " + " | ".join(caps) + " | as_of |"
    sep = "|" + "---|" * (len(caps) + 2)
    sep = sep[:-1] + "|"
    rows = []
    for model in sorted(matrix["models"]):
        entry = matrix["models"][model]
        cells = " | ".join(str(entry["capabilities"].get(c, "-")) for c in caps)
        rows.append("| %s | %s | %s |" % (model, cells, entry.get("as_of", "-")))
    return "\n".join([header, sep] + rows)


def _read_file(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main(argv=None):
    parser = argparse.ArgumentParser(prog="model-capability-matrix", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_v = sub.add_parser("validate", help="validate a matrix file")
    p_v.add_argument("file")
    p_m = sub.add_parser("merge", help="merge overlay onto base")
    p_m.add_argument("base")
    p_m.add_argument("overlay")
    p_m.add_argument("--out", default=None)
    p_d = sub.add_parser("diff", help="diff two matrix versions")
    p_d.add_argument("old")
    p_d.add_argument("new")
    p_q = sub.add_parser("query", help="query one capability of one model")
    p_q.add_argument("file")
    p_q.add_argument("model")
    p_q.add_argument("capability")
    p_e = sub.add_parser("export", help="export a Markdown table")
    p_e.add_argument("file")
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            load_matrix(_read_file(args.file))
            print("OK")
            return 0
        if args.command == "merge":
            merged, conflicts = merge_matrices(load_matrix(_read_file(args.base)),
                                               load_matrix(_read_file(args.overlay)))
            payload = json.dumps({"matrix": merged, "conflicts": conflicts}, indent=2)
            if args.out:
                with open(args.out, "w", encoding="utf-8") as fh:
                    fh.write(payload)
            else:
                print(payload)
            return 0
        if args.command == "diff":
            print(json.dumps(diff_matrices(load_matrix(_read_file(args.old)),
                                           load_matrix(_read_file(args.new))), indent=2))
            return 0
        if args.command == "query":
            value = query(load_matrix(_read_file(args.file)), args.model, args.capability)
            if value is None:
                print("not found", file=sys.stderr)
                return 1
            print(json.dumps(value))
            return 0
        if args.command == "export":
            print(export_table(load_matrix(_read_file(args.file))))
            return 0
    except MatrixError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
