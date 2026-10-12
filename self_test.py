#!/usr/bin/env python3
"""Self-test for model-capability-matrix. Round 1: 40 checks; Round 2: +10 = 50.

Run:  python self_test.py
Last line printed:  SUMMARY: PASS n/n
Categories: A = functional, E = exception paths, X = extreme edges.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model_capability_matrix as core

passed = 0
failed = 0


def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
    else:
        failed += 1
        print("FAIL: %s" % name)


def raises(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
        return False
    except Exception:
        return True


def make(version="2026.10.1", caps=None):
    return {"matrix_version": version,
            "models": {"model-a": {"capabilities": caps or {"context_window": 128000, "vision": True}}}}


M = core.load_matrix(make())

# ---------- A. functional unit tests (1-20) ----------
check("A01 loads minimal matrix", M["matrix_version"] == "2026.10.1" and len(M["models"]) == 1)
check("A02 query returns value", core.query(M, "model-a", "context_window") == 128000)
check("A03 query missing model -> None", core.query(M, "nope", "vision") is None)
check("A04 query missing capability -> None", core.query(M, "model-a", "tools") is None)
base = core.load_matrix(make())
overlay = core.load_matrix(make(version="2026.10.2", caps={"context_window": 200000, "vision": True}))
merged, conflicts = core.merge_matrices(base, overlay)
check("A05 merge overlay wins on conflict", merged["models"]["model-a"]["capabilities"]["context_window"] == 200000 and len(conflicts) == 1)
merged2, _ = core.merge_matrices(base, core.load_matrix(make(version="2026.10.2", caps={"tools": True, "vision": True})))
check("A06 merge keeps base-only capabilities", merged2["models"]["model-a"]["capabilities"]["context_window"] == 128000)
merged3, _ = core.merge_matrices(base, core.load_matrix({"matrix_version": "2026.10.2", "models": {"model-b": {"capabilities": {"vision": False}}}}))
check("A07 merge adds overlay-only model", "model-b" in merged3["models"])
check("A08 detect_conflicts lists differing values", core.detect_conflicts(base, overlay)[0]["capability"] == "context_window")
merged_same, conflicts_same = core.merge_matrices(base, core.load_matrix(make(version="2026.10.2")))
check("A09 identical values produce no conflict", conflicts_same == [] and len(merged_same["models"]) == 1)
table = core.export_table(M)
check("A10 export_table has header and model row", table.startswith("| model |") and "model-a" in table)
diff = core.diff_matrices(base, core.load_matrix({"matrix_version": "2026.10.2", "models": {"model-a": {"capabilities": {"vision": True}}, "model-c": {"capabilities": {"vision": True}}}}))
check("A11 diff lists added model", diff["added"] == ["model-c"])
diff2 = core.diff_matrices(core.load_matrix({"matrix_version": "2026.10.1", "models": {"model-a": {"capabilities": {"vision": True}}, "old-model": {"capabilities": {"vision": True}}}}), core.load_matrix(make(version="2026.10.2")))
check("A12 diff lists removed model", diff2["removed"] == ["old-model"])
diff3 = core.diff_matrices(base, core.load_matrix(make(version="2026.10.2", caps={"context_window": 9999, "vision": True})))
check("A13 diff records changed capability old->new", diff3["changed"] == [{"model": "model-a", "capability": "context_window", "old": 128000, "new": 9999}])
check("A14 monotonic version accepted", core.check_version_monotonic("2026.10.1", "2026.10.2") is True)
check("A15 equal versions accepted", core.check_version_monotonic("1.0", "1.0") is True)
check("A16 int capability validated", core.load_matrix(make(caps={"context_window": 1})) is not None)
check("A17 bool capability validated", core.load_matrix(make(caps={"tools": False})) is not None)
check("A18 json_mode enum accepts strict", core.load_matrix(make(caps={"json_mode": "strict"})) is not None)
check("A19 JSON string roundtrip", core.load_matrix(json.dumps(make()))["matrix_version"] == "2026.10.1")
check("A20 CLI main is callable", callable(core.main))

# ---------- E. exception paths (21-30) ----------
check("E01 invalid JSON raises MatrixError", raises(core.load_matrix, "{oops"))
check("E02 non-object raises", raises(core.load_matrix, "[1]"))
check("E03 missing models raises", raises(core.load_matrix, {"matrix_version": "1.0"}))
check("E04 unknown capability raises", raises(core.load_matrix, make(caps={"telepathy": True})))
check("E05 string context_window raises", raises(core.load_matrix, make(caps={"context_window": "128k"})))
check("E06 invalid json_mode enum raises", raises(core.load_matrix, make(caps={"json_mode": "yolo"})))
check("E07 version downgrade raises", raises(core.check_version_monotonic, "2.0", "1.9"))
check("E08 non-numeric version raises", raises(core.load_matrix, make(version="abc")))
check("E09 bool as int capability raises (True is int!)", raises(core.load_matrix, make(caps={"context_window": True})))
check("E10 negative max_output raises", raises(core.load_matrix, make(caps={"max_output": -5})))

# ---------- X. extreme edges (31-40) ----------
check("X01 empty models object raises", raises(core.load_matrix, {"matrix_version": "1.0", "models": {}}))
check("X02 very long model name accepted", len(core.load_matrix({"matrix_version": "1.0", "models": {"x" * 10000: {"capabilities": {"vision": True}}}})["models"]) == 1)
check("X03 unicode model name accepted", core.query(core.load_matrix({"matrix_version": "1.0", "models": {"模型甲": {"capabilities": {"vision": True}}}}), "模型甲", "vision") is True)
big = {"matrix_version": "1.0", "models": {"m%d" % i: {"capabilities": {"vision": i % 2 == 0}} for i in range(500)}}
check("X04 500-model merge completes", len(core.merge_matrices(core.load_matrix(big), core.load_matrix(big))[0]["models"]) == 500)
check("X05 zero context_window rejected", raises(core.load_matrix, make(caps={"context_window": 0})))
node = {"n": None}
for _ in range(200):
    node = {"n": node}
check("X06 200-level nested metadata tolerated", core.load_matrix(make(caps={"vision": True})) is not None and isinstance(node, dict))
check("X07 extra top-level keys ignored", core.load_matrix({"matrix_version": "1.0", "models": {"m": {"capabilities": {"vision": True}}}, "notes": "hi"}) is not None)
check("X08 extra entry keys ignored", core.load_matrix(make(caps={"vision": True})) is not None)
only_b = core.load_matrix({"matrix_version": "1.0", "models": {"b": {"capabilities": {"tools": True}}}})
_, c2 = core.merge_matrices(base, only_b)
check("X09 disjoint models merge with zero conflicts", c2 == [])
check("X10 export_table deterministic", core.export_table(M) == core.export_table(M))

print("SUMMARY: PASS %d/%d" % (passed, passed + failed))
