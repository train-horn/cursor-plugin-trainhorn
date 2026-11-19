---
name: air-system-sizing
description: Size an onboard compressed-air system for an air horn or train horn with Boyle's law. Use when code or a question computes how long a tank of given gallons and PSI can sound a horn rated in CFM, how many blasts fit, how big a tank is needed for a target runtime, or how long a compressor takes to refill the tank between cut-in and cut-out pressure. Covers gauge vs absolute pressure, free-air CFM and compressor derating.
---

# Air system sizing: tank runtime and compressor recovery

Horns and compressors are rated in **CFM of free air** (cubic feet per minute at
atmospheric pressure). A tank stores air at pressure. Boyle's law (isothermal,
`P·V = const` with absolute pressures) converts between the two.

## The model

Free air released while the tank falls from `P_start` to `P_end` (both **gauge** psi):

```
V_free  = V_tank · (P_start - P_end) / P_atm        P_atm = 14.696 psi at sea level
runtime = V_free / horn_CFM · 60                     seconds
refill  = V_free / compressor_CFM · 60               seconds, between cut-in and cut-out
```

`V_tank` in cubic feet: 1 US gallon = 231 in³ = 0.133681 ft³.

The `+ P_atm` terms of the absolute pressures cancel in the difference, which is why
gauge readings work directly here. Only the air **above the horn's cut-off pressure**
is usable: the tank never empties to 0 psi while the horn still sounds properly.

## Python: the `trainhorn_calc` library

`trainhorn_calc` (<https://github.com/train-horn/trainhorn-calc>, MIT, no dependencies)
implements these formulas with input validation.

```python
from trainhorn_calc import tank_runtime_seconds, blast_count, compressor_recovery_seconds
from trainhorn_calc.airsystem import free_air_volume_cuft

# 5 gal tank, full at 150 psi, horn still sounds well down to 110 psi, horn uses 10 CFM
print(round(free_air_volume_cuft(5, 150, 110), 2))            # usable free air, ft3
secs = tank_runtime_seconds(5, start_psi=150, cutoff_psi=110, horn_cfm=10)
print(round(secs, 1))                                         # continuous horn seconds
print(blast_count(secs, 2))                                   # whole 2 s blasts

# 2 gal tank, compressor cuts in at 110 psi and out at 150 psi
print(round(compressor_recovery_seconds(2, cut_in_psi=110, cut_out_psi=150, compressor_cfm=1.0), 1))

# Same compressor rated 1.0 CFM at 150 psi but 2.0 CFM at 0 psi (linear derating)
print(round(compressor_recovery_seconds(2, 110, 150, 1.0, cfm_at_zero_psi=2.0, rated_psi=150), 1))
```

Output:

```text
1.82
10.9
5
43.7
38.7
```

### Sizing the tank for a target runtime

Invert the runtime formula: `V_tank = runtime · CFM / 60 · P_atm / (P_start - P_end)`.

```python
from trainhorn_calc import tank_runtime_seconds
from trainhorn_calc.airsystem import ATMOSPHERIC_PSI, CUBIC_FEET_PER_GALLON

def tank_gallons_for(runtime_s, horn_cfm, start_psi, cutoff_psi):
    free_air_cuft = runtime_s * horn_cfm / 60.0
    return free_air_cuft * ATMOSPHERIC_PSI / (start_psi - cutoff_psi) / CUBIC_FEET_PER_GALLON

gallons = tank_gallons_for(15, horn_cfm=10, start_psi=150, cutoff_psi=110)
print(f"{gallons:.2f} gal")
# Round-trip check with the library
print(round(tank_runtime_seconds(gallons, 150, 110, 10), 6))
```

Output:

```text
6.87 gal
15.0
```

## JavaScript (no dependencies)

```js
const P_ATM_PSI = 14.696;
const CUFT_PER_GAL = 231 / 1728;

function freeAirCuft(tankGallons, highPsi, lowPsi, atmPsi = P_ATM_PSI) {
  if (!(tankGallons > 0)) throw new RangeError("tankGallons must be > 0");
  if (!(lowPsi >= 0) || !(highPsi > lowPsi)) throw new RangeError("need highPsi > lowPsi >= 0");
  return (tankGallons * CUFT_PER_GAL * (highPsi - lowPsi)) / atmPsi;
}

function tankRuntimeSeconds(tankGallons, startPsi, cutoffPsi, hornCfm) {
  if (!(hornCfm > 0)) throw new RangeError("hornCfm must be > 0");
  return (freeAirCuft(tankGallons, startPsi, cutoffPsi) / hornCfm) * 60;
}

function compressorRecoverySeconds(tankGallons, cutInPsi, cutOutPsi, compressorCfm) {
  if (!(compressorCfm > 0)) throw new RangeError("compressorCfm must be > 0");
  return (freeAirCuft(tankGallons, cutOutPsi, cutInPsi) / compressorCfm) * 60;
}

const secs = tankRuntimeSeconds(5, 150, 110, 10);
console.log(secs.toFixed(1), Math.floor(secs / 2 + 1e-9));
console.log(compressorRecoverySeconds(2, 110, 150, 1.0).toFixed(1));
```

Output:

```text
10.9 5
43.7
```

## Pitfalls to check in code review

1. **Absolute pressure in the ratio.** `V_tank · (150 + 14.7) / 14.7` counts all the air in
   the tank, including the part that stays behind below the cut-off. Use the pressure
   **difference** between start and cut-off.
2. **Starting from 0 psi.** A horn rated for 150 psi does not sound properly near 0 psi.
   Use the real cut-off (often 90 to 110 psi) or the result is a large overestimate.
3. **Compressor CFM at the wrong pressure.** Compressors are often advertised with their
   0 psi flow. Output falls as pressure rises, so refill times computed from the 0 psi
   figure are optimistic. Use the CFM at (or near) the cut-out pressure, or the linear
   model (`cfm_at_zero_psi`, `rated_psi`).
4. **Gallons vs cubic feet vs litres.** 1 US gal = 0.133681 ft³ = 3.785 L. Keep CFM and tank
   volume in matching units.
5. **Compressor running during the blast.** The simple model assumes the compressor is off
   (worst case). Adding its output gives `runtime = V_free / (horn_CFM - compressor_CFM)`,
   valid only while horn CFM is larger.
6. **Temperature.** Long or rapid blasts cool the air (closer to adiabatic), so real runtime
   is a little shorter than the Boyle estimate. Present results as upper estimates.
7. **Duty cycle.** Small 12 V compressors have duty-cycle limits (for example 33 % or 100 %
   at a stated pressure). Recovery time alone does not show whether the compressor
   can keep up with repeated blasts.

## Related

Browser versions: air tank runtime <https://train-horn.com/tools/air-tank-runtime/> and
compressor recovery <https://train-horn.com/tools/compressor-recovery/>.
