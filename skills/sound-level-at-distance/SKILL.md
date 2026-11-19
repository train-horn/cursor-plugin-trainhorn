---
name: sound-level-at-distance
description: Compute the sound pressure level (SPL, dB) of a horn, siren, speaker or other source at a given distance with the inverse-square law. Use when code or a question converts "X dB at Y ft/m" to another distance, finds the distance where a level drops to a limit, adds several sources together, or compares manufacturer dB claims. Covers the reference distance, ft/m units, optional air absorption, combining levels and the common pitfalls.
---

# Sound level at distance (inverse-square law)

Use this skill whenever you write or review code that turns a decibel figure into
a level somewhere else: "150 dB horn, how loud at 100 ft?", "where does it drop
below 90 dB?", "two horns of 150 dB together?".

## The model

A small source in open air (free field) spreads its energy over a sphere, so
intensity falls with the square of distance and the **level falls by
20 · log10(d / d_ref) dB**:

```
L(d) = L_ref - 20·log10(d / d_ref) - α·(d - d_ref)/1000
```

| Symbol | Meaning |
|---|---|
| `L_ref` | level in dB **at the reference distance** `d_ref` (for example "150 dB at 10 ft") |
| `d`, `d_ref` | distances in the **same unit** (ft or m); only their ratio matters for the first term |
| `α` | optional air absorption in dB/km (distances in metres for this term); 0 for a pure inverse-square estimate |

Rules of thumb that follow from it:

- **-6.02 dB per doubling** of distance (20·log10 2), **-20 dB per tenfold** distance.
- Inverse: `d = d_ref · 10^((L_ref - L)/20)` (closed form only when `α = 0`).
- Incoherent sources add on an energy basis: `L = 10·log10(Σ 10^(L_i/10))`.
  Two equal horns give **+3.01 dB**, not double the decibels.

## Python: the `trainhorn_calc` library

`trainhorn_calc` is a dependency-free, MIT-licensed Python package
(<https://github.com/train-horn/trainhorn-calc>, `conda install -c trainhorn trainhorn-calc`
or `pip install .` from a checkout). Its defaults are `ref_distance=10`, `unit="ft"`.

```python
from trainhorn_calc import spl_at_distance, distance_for_spl, db_doubling_loss, combine_levels

# Rated "150 dB at 10 ft": estimate at 100 ft and at 500 ft
print(round(spl_at_distance(150, 100, ref_distance=10, unit="ft"), 1))
print(round(spl_at_distance(150, 500, ref_distance=10, unit="ft"), 1))

# Same, with air absorption for the 500 Hz octave band (about 1.9 dB/km)
print(round(spl_at_distance(150, 500, ref_distance=10, unit="ft", absorption_db_per_km=1.9), 1))

# Distance at which the level falls to 90 dB, without and with absorption
print(round(distance_for_spl(150, 90, ref_distance=10, unit="ft")))
print(round(distance_for_spl(150, 90, ref_distance=10, unit="ft", absorption_db_per_km=1.9)))

print(round(db_doubling_loss(), 2))         # dB lost per doubling of distance
print(round(combine_levels([150, 150]), 1))  # two equal horns
print(round(combine_levels([110, 100]), 1))  # a 10 dB quieter source barely adds
```

Output:

```text
130.0
116.0
115.7
10000
6491
6.02
153.0
110.4
```

### Changing the reference distance or unit

A rating "at 1 m" and a rating "at 10 ft" are **not** comparable until you move
them to the same distance. 10 ft = 3.048 m, so a "1 m" figure is about 9.7 dB
higher than the same horn rated at 10 ft.

```python
from trainhorn_calc import spl_at_distance

# A horn rated "118 dB at 1 m": what is that at 10 ft (3.048 m) and at 50 ft (15.24 m)?
at_10_ft = spl_at_distance(118, 3.048, ref_distance=1, unit="m")
at_50_ft = spl_at_distance(118, 15.24, ref_distance=1, unit="m")
print(f"{at_10_ft:.1f} dB at 10 ft")
print(f"{at_50_ft:.1f} dB at 50 ft")

# Same answer if you convert the 1 m reference to feet instead of the distance to metres
print(f"{spl_at_distance(118, 50, ref_distance=1 / 0.3048, unit='ft'):.1f} dB at 50 ft")
```

Output:

```text
108.3 dB at 10 ft
94.3 dB at 50 ft
94.3 dB at 50 ft
```

## JavaScript (no dependencies)

A self-contained port with the same formulas and defaults. A full library with
input validation lives at <https://github.com/train-horn/trainhorn-calc-js>.

```js
const M_PER_FT = 0.3048;

function splAtDistance(sourceDb, distance, refDistance = 10, unit = "ft", absorptionDbPerKm = 0) {
  if (!(distance > 0) || !(refDistance > 0)) throw new RangeError("distances must be > 0");
  if (unit !== "ft" && unit !== "m") throw new RangeError('unit must be "ft" or "m"');
  if (!(absorptionDbPerKm >= 0)) throw new RangeError("absorption must be >= 0");
  let level = sourceDb - 20 * Math.log10(distance / refDistance);
  if (absorptionDbPerKm > 0) {
    const toM = unit === "ft" ? M_PER_FT : 1;
    level -= (absorptionDbPerKm * (distance - refDistance) * toM) / 1000;
  }
  return level;
}

function distanceForSpl(sourceDb, targetDb, refDistance = 10, unit = "ft", absorptionDbPerKm = 0) {
  const freeField = refDistance * 10 ** ((sourceDb - targetDb) / 20);
  if (!absorptionDbPerKm || freeField === refDistance) return freeField;
  // Level falls monotonically with distance: bisect between d_ref and the free-field answer.
  let [lo, hi] = [freeField, refDistance].sort((a, b) => a - b);
  for (let i = 0; i < 200 && hi - lo > 1e-12 * hi; i++) {
    const mid = (lo + hi) / 2;
    if (splAtDistance(sourceDb, mid, refDistance, unit, absorptionDbPerKm) > targetDb) lo = mid;
    else hi = mid;
  }
  return (lo + hi) / 2;
}

function combineLevels(levels) {
  if (!levels.length) throw new RangeError("need at least one level");
  const peak = Math.max(...levels);
  return peak + 10 * Math.log10(levels.reduce((s, l) => s + 10 ** ((l - peak) / 10), 0));
}

console.log(splAtDistance(150, 100).toFixed(1));
console.log(splAtDistance(150, 500, 10, "ft", 1.9).toFixed(1));
console.log(Math.round(distanceForSpl(150, 90)));
console.log(Math.round(distanceForSpl(150, 90, 10, "ft", 1.9)));
console.log(splAtDistance(118, 15.24, 1, "m").toFixed(1));
console.log(combineLevels([150, 150]).toFixed(1));
```

Output:

```text
130.0
115.7
10000
6491
94.3
153.0
```

## Pitfalls to check in code review

1. **Missing reference distance.** "150 dB" alone is meaningless. Store and print the
   distance with every level (`150 dB @ 10 ft`). If a source gives none, say so instead
   of assuming one. Aftermarket train horns are usually rated at 10 ft; many
   specifications and noise limits use 1 m, 50 ft or 100 ft.
2. **Mixed units.** `d` and `d_ref` must share a unit. Converting only one of them is the
   most common bug (`spl_at_distance(150, 30, ref_distance=10)` with 30 m and 10 ft
   silently gives the wrong answer). 1 ft = 0.3048 m exactly.
3. **10·log10 instead of 20·log10.** dB SPL is a pressure level; distance changes use
   20·log10 (6 dB per doubling). 10·log10 (3 dB per doubling) applies to line sources
   such as busy roads or a long passing train, not to a single horn.
4. **Adding decibels arithmetically.** 150 dB + 150 dB = 153 dB, not 300 dB. Use the
   energy sum. Subtracting background noise works the same way in reverse.
5. **Near field.** Inside roughly one or two horn lengths the law does not hold. Do not
   extrapolate a "150 dB at 10 ft" rating to 1 ft.
6. **Real outdoor conditions.** Ground reflection, barriers, wind and temperature
   gradients can change outdoor levels by several dB either way. Air absorption is
   frequency dependent (about 1 dB/km at 250 Hz, 2 at 500 Hz, 4 at 1 kHz at 10 °C /
   70 % RH); train horn chords sit mostly between 250 and 600 Hz, so it only matters
   at long range. Present results as **estimates**, never as measurements.
7. **Weighting and metric.** dB(A), dB(C), peak and Lmax are different numbers. Keep the
   weighting from the source (`dBA`) and do not mix weighted and unweighted values.

## Manufacturer claims vs measurements

- Treat a catalogue figure as a **manufacturer claim** until an independent measurement
  with a stated distance, weighting and meter confirms it. Label every value with its
  source, for example `MFR claim`, `Independent measurement`, `Statutory limit`.
- Claims are often taken at the horn mouth, in the near field, or as unweighted peaks.
  An independent test of the same horn at the same distance is commonly several dB lower.
- When comparing two horns, first move both figures to the **same reference distance**
  (see the 1 m vs 10 ft example) and the same weighting; otherwise the comparison is invalid.
- Legal limits are written as a level **at a stated distance** (for example a maximum
  dB(A) at 50 ft). Compute the estimated level at that distance, label it as an estimate,
  and point users to the statute for the real rule. This is not legal advice.

## Related

Browser versions of these calculators (decibel distance, PSI to loudness, air tank
runtime, compressor recovery, wire gauge): <https://train-horn.com/tools/>.
