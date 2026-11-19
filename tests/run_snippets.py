#!/usr/bin/env python3
"""Run every code snippet in skills/*/SKILL.md and check its printed output.

Each ```python or ```js block must be followed by an "Output:" line and a
```text block. The snippet is executed (Python with trainhorn_calc on the path,
JavaScript with node) and its stdout must match the text block exactly.

It also cross-checks the JavaScript ports against the Python library on a grid
of inputs, so the two implementations cannot drift apart.

Usage:
    python3 tests/run_snippets.py [path/to/trainhorn-calc/src]

The library path defaults to $TRAINHORN_CALC_SRC, then ../core-python/src next
to this repository. Exit status is 0 only if every check passes.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BLOCK = re.compile(
    r"```(python|js)\n(?P<code>.*?)```\s*\n\s*Output:\s*\n\s*```text\n(?P<out>.*?)```",
    re.S,
)
ANY_CODE = re.compile(r"```(python|js)\n", re.S)


def library_src() -> Path:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).resolve()
    env = os.environ.get("TRAINHORN_CALC_SRC")
    if env:
        return Path(env).resolve()
    return (ROOT.parent / "core-python" / "src").resolve()


def run(lang: str, code: str, src: Path) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        if lang == "python":
            path = Path(tmp) / "snippet.py"
            path.write_text(code)
            env = dict(os.environ, PYTHONPATH=str(src))
            cmd = [sys.executable, str(path)]
        else:
            path = Path(tmp) / "snippet.mjs"
            path.write_text(code)
            env = dict(os.environ)
            cmd = ["node", str(path)]
        proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=tmp, timeout=60)
    if proc.returncode != 0:
        raise RuntimeError(f"exit {proc.returncode}\n{proc.stderr}")
    return proc.stdout


def snippet_checks(src: Path) -> "list[tuple[str, bool, str]]":
    results = []
    skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
    if not skills:
        return [("skills found", False, "no skills/*/SKILL.md files")]
    for skill in skills:
        text = skill.read_text()
        blocks = list(BLOCK.finditer(text))
        n_code = len(ANY_CODE.findall(text))
        name = skill.parent.name
        if n_code != len(blocks):
            results.append((f"{name}: every snippet has an Output block", False,
                            f"{n_code} code blocks but {len(blocks)} with Output"))
        for i, m in enumerate(blocks, 1):
            label = f"{name} #{i} ({m.group(1)})"
            try:
                got = run(m.group(1), m.group("code"), src)
            except Exception as exc:  # noqa: BLE001 - report any failure
                results.append((label, False, str(exc)))
                continue
            want = m.group("out")
            ok = got.rstrip("\n") == want.rstrip("\n")
            results.append((label, ok, "" if ok else f"expected:\n{want}got:\n{got}"))
    return results


def js_functions(skill: str) -> str:
    text = (ROOT / "skills" / skill / "SKILL.md").read_text()
    for m in BLOCK.finditer(text):
        if m.group(1) == "js":
            # Drop the demo console.log lines; keep the definitions.
            return "\n".join(l for l in m.group("code").splitlines() if not l.startswith(("console.log", "const secs")))
    raise LookupError(f"no js block in {skill}")


def cross_checks(src: Path) -> "list[tuple[str, bool, str]]":
    sys.path.insert(0, str(src))
    import trainhorn_calc as tc  # noqa: E402

    spl_cases = [(150, d, r, u, a) for d in (0.5, 3, 10, 57.5, 100, 1000, 25000)
                 for r in (1, 3.048, 10) for u in ("ft", "m") for a in (0, 1.9, 9.7)]
    dist_cases = [(s, t, r, u, a) for s in (118, 150) for t in (60, 90, 117, 160)
                  for r in (1, 10) for u in ("ft", "m") for a in (0, 1.9)]
    comb_cases = [[150], [150, 150], [110, 100], [90, 95, 101, 60]]
    air_cases = [(g, hi, lo, q) for g in (0.5, 2, 5, 10) for hi in (120, 150, 200)
                 for lo in (0, 90, 110) for q in (0.8, 3.5, 10)]

    js = js_functions("sound-level-at-distance") + "\n" + js_functions("air-system-sizing") + f"""
const S = {json.dumps(spl_cases)}, D = {json.dumps(dist_cases)}, C = {json.dumps(comb_cases)}, A = {json.dumps(air_cases)};
console.log(JSON.stringify({{
  spl: S.map(c => splAtDistance(...c)),
  dist: D.map(c => distanceForSpl(...c)),
  comb: C.map(c => combineLevels(c)),
  run: A.map(([g, hi, lo, q]) => tankRuntimeSeconds(g, hi, lo, q)),
  rec: A.map(([g, hi, lo, q]) => compressorRecoverySeconds(g, lo, hi, q)),
}}));
"""
    got = json.loads(run("js", js, src))
    want = {
        "spl": [tc.spl_at_distance(*c) for c in spl_cases],
        "dist": [tc.distance_for_spl(*c) for c in dist_cases],
        "comb": [tc.combine_levels(c) for c in comb_cases],
        "run": [tc.tank_runtime_seconds(g, hi, lo, q) for g, hi, lo, q in air_cases],
        "rec": [tc.compressor_recovery_seconds(g, lo, hi, q) for g, hi, lo, q in air_cases],
    }
    results = []
    for key, expected in want.items():
        bad = [(i, e, g) for i, (e, g) in enumerate(zip(expected, got[key]))
               if abs(e - g) > 1e-9 * max(1.0, abs(e))]
        ok = not bad and len(expected) == len(got[key])
        results.append((f"js matches trainhorn_calc: {key} ({len(expected)} cases)", ok,
                        "" if ok else f"first mismatches: {bad[:3]}"))
    return results


def main() -> int:
    src = library_src()
    if not (src / "trainhorn_calc" / "__init__.py").exists():
        print(f"trainhorn_calc not found under {src}; pass its src directory as an argument")
        return 2
    if shutil.which("node") is None:
        print("node is required for the JavaScript snippets")
        return 2
    results = snippet_checks(src) + cross_checks(src)
    failed = 0
    for label, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {label}")
        if not ok:
            failed += 1
            print("      " + detail.replace("\n", "\n      "))
    print(f"\n{len(results) - failed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
