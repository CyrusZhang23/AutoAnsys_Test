# Waveguide T-Junction Power Divider
## Model Description — **Frozen Reference**

**Status:** **FROZEN** — geometry is normative for HFSS / PyAEDT and **must match** this document, **`config/params.json`**, and **`wg_tee.preview`** (reference preview).  
**Revision:** 2026-03-28 — do not change geometry without updating **all three** together.

**Normative rule:** The **shape** is defined by the **axis-aligned box bounds** and **Boolean sequence** in §4–§5. Any HFSS or scripted model shall reproduce that shape within solver/mesh tolerance.

---

## 1. Overall Geometry

The model is a **rectangular waveguide T-junction power divider**, used as the gold reference for HFSS simulation and PyAEDT automation.

The **reference body** (same topology as **`wg_tee.preview`**) is built from **three identical rectangular arms** in a **global Cartesian frame**, **Boolean-united** into one solid, with an **optional Boolean subtract** for the tuning slot.

- All waveguides are **air-filled**; walls are **PEC** in simulation (materials/boundaries are separate from this geometric spec).
- **Parameter values** and **units** come from **`config/params.json`** (see §6).

---

## 2. Coordinate System and Orientation

- **Origin:** **T-junction center** (intersection reference point for all arms).
- **Axes:**
  - **+X** — Port 1 (main arm)
  - **±Y** — Ports 2 and 3 (branch arms)
  - **Z** — waveguide height (cross-section “tall” direction)

### Port Orientation

| Port | Arm direction | Outer end (waveguide axis) |
|-----:|---------------|----------------------------|
| **Port 1** | **+X** | Plane **x = L** |
| **Port 2** | **+Y** | Plane **y = L** |
| **Port 3** | **−Y** | Plane **y = −L** |

---

## 3. Waveguide Cross Section and Arm Length

All three arms share the same rectangular cross section and the same length **L**:

| Symbol | Meaning | Axis / note |
|--------|---------|-------------|
| **a** | Cross-section width | In the plane perpendicular to the arm: spans **a** in the transverse in-plane direction (see §4 per arm) |
| **b** | Cross-section height | Along **Z**, from **z = −b/2** to **z = +b/2** |
| **L** | Arm length | Along each arm’s axis; **all three arms use the same L** |

**Units:** **millimetres (mm)** — `config/params.json` shall include **`"units": "mm"`**.

---

## 4. Canonical Construction (Axis-Aligned Boxes + Booleans)

This section is the **authoritative** construction. It is **equivalent** to “create `a×b×L` sections, rotate about **Z**, translate to meet at the origin, then Unite”, but **implementations shall use the bounds below** so results match **`wg_tee.preview`** / **`wg_tee.geometry`**.

### 4.1 Arm solids (closed boxes)

Let **Arm_X**, **Arm_Y+**, **Arm_Y−** be axis-aligned rectangular solids with **inclusive** bounds:

| Solid | x | y | z |
|-------|---|---|---|
| **Arm_X** (Port 1, +X) | **\[0, L\]** | **\[−a/2, +a/2\]** | **\[−b/2, +b/2\]** |
| **Arm_Y+** (Port 2, +Y) | **\[−a/2, +a/2\]** | **\[0, L\]** | **\[−b/2, +b/2\]** |
| **Arm_Y−** (Port 3, −Y) | **\[−a/2, +a/2\]** | **\[−L, 0\]** | **\[−b/2, +b/2\]** |

### 4.2 Body without slot

\[
\text{Body}_0 = \text{Arm\_X} \;\cup\; \text{Arm\_Y+} \;\cup\; \text{Arm\_Y−}
\]

(Boolean **Unite** / union — operand order does not change the result.)

### 4.3 Optional slot tool (subtract only when enabled)

When **`enable_slot`** is **true**, define solid **SlotTool** with bounds:

| Axis | Interval |
|------|----------|
| **x** | **\[−a/2, −a/2 + D\]** |
| **y** | **\[offset − X/2, offset + X/2\]** |
| **z** | **\[−b/2, +b/2\]** |

Then:

\[
\text{Body} = \text{Body}_0 \setminus \text{SlotTool}
\]

(Boolean **Subtract** / difference: remove **SlotTool** from **Body₀**.)

When **`enable_slot`** is **false**, **Body = Body₀**; **X**, **D**, and **offset** **must not** affect geometry (they may still appear in **`config/params.json`**).

**Parameter meanings (slot):**

| Symbol | Role in §4.3 |
|--------|----------------|
| **D** | Extent of **SlotTool** along **+X**, starting at **x = −a/2** |
| **X** | Extent of **SlotTool** along **Y** (opening width), centered at **y = offset** |
| **b** | Same **b** as waveguide; **SlotTool** spans full height in **Z** |
| **offset** | **Y** coordinate of **SlotTool** centre (relative to origin) |

---

## 5. Tuning Slot (Summary)

- **Purpose:** rectangular recess (capacitive tuning feature); **normative shape** is **SlotTool** in §4.3 and the subtract in §4.3.
- **Placement:** outer **−X** envelope of the united arms at **x = −a/2**; pocket extends **+X** by **D**.
- **Control:** **`enable_slot`** in `config/params.json` (see §6).

---

## 6. External Parameters (`config/params.json`)

**Required keys** (geometry):

| Key | Type | Rule |
|-----|------|------|
| **`units`** | string | **`"mm"`** for this project |
| **`a`** | number | > 0 |
| **`b`** | number | > 0 |
| **`L`** | number | > 0 |
| **`enable_slot`** | boolean | If **false**, ignore **X**, **D**, **offset** for geometry |

**Slot keys** (read only when **`enable_slot`** is **true**; if **false**, values **must be ignored**):

| Key | Type | Rule |
|-----|------|------|
| **`X`** | number | > 0 |
| **`D`** | number | > 0 |
| **`offset`** | number | any finite value (Y centre of slot) |

**Optional object `simulation`** (HFSS / `wg-hfss`, ignored by `wg-preview`): if omitted, code uses the same defaults as the stock `config/params.json`. Partial objects merge over those defaults.

| Key | Type | Rule |
|-----|------|------|
| **`setup_name`** | string | non-empty; HFSS setup name |
| **`sweep_name`** | string | non-empty; frequency sweep name |
| **`adaptive_frequency_ghz`** | number | > 0; adaptive solve frequency (passed to HFSS as `"{value}GHz"`) |
| **`sweep_start_ghz`** | number | sweep lower end (GHz) |
| **`sweep_stop_ghz`** | number | ≥ `sweep_start_ghz` |
| **`sweep_step_ghz`** | number | > 0 |
| **`sweep_type`** | string | **`Discrete`**, **`Interpolating`**, or **`Fast`** |
| **`save_fields`** | boolean | sweep field save |
| **`save_rad_fields`** | boolean | radiating fields save |
| **`body_material`** | string | non-empty; e.g. **`vacuum`** |
| **`modes_per_port`** | integer | ≥ 1 |
| **`pec_boundary_name`** | string | non-empty; Perfect E boundary name |
| **`sparam_csv_filename`** | string or null | optional **basename** only (no path); default **`{project_stem}_s_params.csv`** under **`output/results/`** |
| **`field_top_freq_ghz`** | number or null | frequency (GHz) for **top-surface** field plot; if **null**, see **`field_top_use_s11_min`** |
| **`field_top_use_s11_min`** | boolean | if **`field_top_freq_ghz`** is null and S-parameter CSV exists, use frequency at **minimum S11 (dB)** (“谐振/匹配” 频点近似) |
| **`field_top_quantity`** | string | HFSS quantity, e.g. **`Mag_E`** |
| **`field_top_image_basename`** | string or null | optional basename for **`output/results/{stem}_field_top.jpg`** |

---

## 7. Ports and Excitation (HFSS)

- Three **modal wave ports**, one on each arm, on the **outer** faces: **x = L** (Port 1), **y = L** (Port 2), **y = −L** (Port 3).
- **Driven Modal**; fundamental **TE₁₀** only (simulation intent; independent of geometric freeze).
- **`wg-hfss`** (unless `--geometry-only`) assigns **Perfect E** on every body face except those three caps, names excitations **`Port1`**, **`Port2`**, **`Port3`** in that order (so post-processing **S11**, **S21**, **S31** match §2 port numbering).

### Port Summary

| Port | Direction | Outer face | HFSS name (script) |
|-----:|-----------|------------|--------------------|
| Port 1 | +X | x = L | `Port1` |
| Port 2 | +Y | y = L | `Port2` |
| Port 3 | −Y | y = −L | `Port3` |

---

## 8. Simulation Setup

- Solution type: **HFSS Driven Modal**
- Frequency domain; **PEC** walls; no radiating boundaries required for closed waveguide.
- **Material:** unified body **vacuum** (`wg-hfss`).
- **Scripted setup:** values come from **`config/params.json`** → **`simulation`** (defaults match former hard-coded `Setup1` + **0–10 GHz** step **0.1 GHz** discrete sweep). Below the guide cutoff, solutions are non-physical — raise **`sweep_start_ghz`** in JSON if needed.
- **S-parameter export:** **`wg-hfss --solve`** or **`wg-solve-export`** runs the solver and writes **`dB(S(1,1))`**, **`dB(S(2,1))`**, **`dB(S(3,1))`** vs frequency to a **semicolon-separated** CSV under **`output/results/`** (see **`sparam_csv_filename`**). **`wg-plot-s`** reads that CSV and saves an image (default **JPG**). **`wg-run-sim`** chains **non-graphical** build + solve + CSV + **JPG** in one command.
- **Top-surface field:** exterior faces at **z = +b/2** (**+Z** outward normal), quantity **`field_top_quantity`** (default **Mag_E**), frequency **`field_top_freq_ghz`** or **S11-min** from CSV or **adaptive** frequency. **`wg-hfss --field-top`** / **`wg-run-sim --field-top`** / **`wg-field-top`** (export only, requires solved project) writes **`output/results/{stem}_field_top.jpg`**. If the plot fails, try **`save_fields`: true** on the sweep.

---

## 9. Intended Usage

- **HFSS GUI** gold model and **PyAEDT** automation shall match §4–§6.
- **`wg_tee.preview`** is the **non-solver** reference mesh for the **same** booleans (implementation uses trimesh/manifold; HFSS uses its own kernel — **final surfaces must coincide** within tolerance).

---

## 10. Notes

- Screenshots in `ModelDescribe/` are illustrative; **§4–§6 override** if there is any discrepancy.
- CAD/STEP are optional; automation may build from parameters only.
- **Any geometry change** requires updating **`ModelDescribe.md`**, **`config/params.json`** field definitions, **`src/wg_tee/geometry.py`**, and **`src/wg_tee/preview.py`** in the same change set.
- **PyAEDT automation** (same §4–§6 geometry): console command **`wg-hfss`** → **`wg_tee.hfss_build`**; normative box math in **`src/wg_tee/geometry.py`**, parameters in **`src/wg_tee/params.py`**. Python environment: **`uv sync`** (includes **pyaedt**); a local **Ansys Electronics Desktop** install is still required to run HFSS. **3D preview:** **`wg-preview`** → **`wg_tee.preview`**.
