# trainhorn-calc: Cursor plugin

Skills and rules that help Cursor's agent get horn acoustics and air system math
right: sound level at a distance with the inverse-square law, and compressed-air
tank runtime and compressor recovery with Boyle's law. Every code snippet in the
skills is executed by the test script and checked against the
[`trainhorn_calc`](https://github.com/train-horn/trainhorn-calc) Python library.

## What's inside

| Component | Path | What it does |
|---|---|---|
| Skill | [`skills/sound-level-at-distance/SKILL.md`](skills/sound-level-at-distance/SKILL.md) | SPL at distance, distance for a target dB, air absorption, combining sources, ft/m and reference-distance conversion, pitfalls, manufacturer claims vs measurements. Python + JavaScript. |
| Skill | [`skills/air-system-sizing/SKILL.md`](skills/air-system-sizing/SKILL.md) | Free air from Boyle's law, horn runtime and blast count, tank size for a target runtime, compressor recovery (constant or linearly derated CFM). Python + JavaScript. |
| Rule | [`rules/db-reference-distance.mdc`](rules/db-reference-distance.mdc) | Always state the reference distance (and weighting) with every dB value. |
| Rule | [`rules/db-source-labels.mdc`](rules/db-source-labels.mdc) | Label every dB figure: MFR claim, Independent, Statutory or Estimate. |
| Manifest | [`.cursor-plugin/plugin.json`](.cursor-plugin/plugin.json) | Plugin metadata. |

## Install

Install from the Cursor plugin directory, or clone this repository and add it as a
local plugin. The rules apply automatically; the skills load when a task involves
decibels at a distance or air tank / compressor sizing.

## Example

> "My horn is rated 118 dB at 1 m. Will it be under 100 dB(A) at 50 ft?"

With the skill, the agent converts both distances to the same unit, applies
`20·log10`, and answers "about 94 dB at 50 ft (Estimate from a MFR claim at 1 m;
free field, unweighted rating)" instead of comparing 118 to 100 directly.

## Tests

```bash
git clone https://github.com/train-horn/trainhorn-calc
python3 tests/run_snippets.py trainhorn-calc/src
```

Requires Python 3.8+ and Node.js 18+. The script runs every ```` ```python ```` and
```` ```js ```` block in the skills, compares the printed output with the documented
`Output:` block, and cross-checks the JavaScript ports against the Python library
on 410 input combinations.

## Limits

Results are engineering estimates from simple physical models (free field, isothermal
expansion). They are not measurements and not legal advice about horn use.

## Related

- [Train Horn calculators](https://train-horn.com/tools/): browser versions of these calculators.
- [trainhorn-calc (Python)](https://github.com/train-horn/trainhorn-calc) and
  [trainhorn-calc-js](https://github.com/train-horn/trainhorn-calc-js).

## License

MIT. See [LICENSE](LICENSE).
