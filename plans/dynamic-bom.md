# Dynamic BOM: automatic part substitution

## Goal

Stop hand-managing stock. The schematic says what each part must *be*, not which exact part number to buy, and a
tool picks an in-stock JLC part for every position when the BOM is built. Requested by the user on 2026-11-15:

> equivalent replacement parts are fine. I'd love for that kind of swap to just always be automatic. Ideally,
> resistors, caps, inductors, diodes, MOSFETs, etc should all be generic. Even LDOs, logic gates, power meters, etc
> should have automatic equivalents when stock is missing. [...] eventually advanced things like swapping for a
> different buck converter IC with a compatible footprint that maybe has a different threshold voltage or needs a
> cap instead of a high impedance resistor for some bootup setting and we can on the fly change the BOM/assembly
> instructions to match it.

Trigger: the INA228 went to 0 stock during schematic work, and the INA226 was swapped in by hand.

## Context

- Repo `C:\Users\camer\git\Personal Projects\avr-tester-v2` (GitHub `TomSawyerLabs/mcu-hil`). Main plan:
  `plans/v2-design.md`.
- Stock source: JLC's own parts search (`tools/jlc_search.py`, endpoint `selectSmtComponentList`, no key).
  It returns stock, price breaks, library type (Basic / preferred / Extended), package and a description.
  Detailed parameters (tolerance, voltage, Vgs(th)...) need JLC's per-part detail call or parsing the description.
- The schematic generator (`tools/schgen/`) retires once the board is hand-edited in KiCad. So the resolver must
  read the **KiCad files**, not `design.py`.

## Design (approved by the user 2026-11-22: "sounds good")

1. **Requirements live in the schematic.** Each symbol carries a `Spec` field instead of (or beside) a fixed `LCSC`:
   - Generic parts: `R 10k 1% 0402`, `C 100n X7R/X5R >=16V 0402`, `L 10u Isat>=1.5A 4x4`, `D schottky 40V 1A SOD-123`,
     `NMOS SOT-23 Vds>=30V Vgs(th)<=2.0V Rds(on)@2.5V<=5R`, `LED red 0603`.
   - Functional parts: `Spec = group:INA22x-VSSOP10`. Groups are defined in a project parts file (`hw/parts/*.toml`).
2. **Groups** list candidates in preference order. Each candidate gives its MPN, its pin table (checked automatically
   against the footprint's pads, so a non-drop-in part can't sneak in), and **deltas**: what else changes when it is
   picked:
   - other parts' values or specs (crystal load capacitance → load caps; regulator Vref → feedback resistor;
     INA226 vs INA228 → nothing on the board, a firmware note);
   - fitted/DNP swaps (a strap pin that wants a capacitor instead of a resistor: both footprints on the board,
     the delta picks which one is fitted);
   - notes for firmware and the assembly report.
3. **Resolver** (`tools/bom/`): for every position, list the JLC parts that meet the spec, keep those with enough
   stock for the order quantity plus a margin, rank them (Basic → preferred → Extended because of loading fees, then
   fewest unique parts across the board, then price), apply the chosen candidates' deltas, and re-check.
4. **Lock file** (`hw/<board>/bom.lock.json`, committed), like a package lock: the chosen LCSC number per reference,
   with the stock and time it was chosen. Builds are reproducible. `--update` re-resolves; `--check` fails when a
   locked part has dropped below the order quantity.
5. **Any mix of population options** (user, 2026-11-20: "I want to be able to say like 'no SD, yes crystal and yes
   clock generator'"). Every symbol already carries an `Option` field (CLK, SI, HV, SD, XTAL, XSW, or `!X` for a
   bypass part), so the tool takes the options per order, e.g. `--without SD,HV`, and works out what is fitted.
   The user wants no explicit variants (2026-11-20), so the KiCad variants are gone. **Built 2026-11-20:**
   `tools/bom` reads the KiCad files and `hw/options.toml` (options, `needs` rules, board limits) and writes the
   JLC BOM for any mix. No stock lookup or substitution yet; that is phase 1 proper.
6. **Outputs:** JLC BOM CSV and CPL (with per-part rotation fixes), plus an assembly report: every substitution, why
   it was made, and every delta applied.

## Phases

1. **(done 2026-11-22, except CPL)** Generic passives and discretes, the lock file, and JLC BOM export. Built:
   - `Spec` field per symbol, written by the generator. Kinds (`tools/bom/spec.py`): `R`, `C` (dielectric grade
     `X5R+` = X5R or better), `LED`, and `mpn <part number> [package]` = that part number from any maker (used for
     2N7002, BZT52C3V6, 1N4148W, B5819W, AO3401A, MT3608, USBLC6-2SC6). No Spec = fixed part, stock-checked only
     (ICs, connectors, crystals, the inductor). `L` and crystal specs wait for phase 2/3 (footprint- and
     load-capacitance-dependent).
   - The schematic's `LCSC` field is the preferred part; it must meet its own Spec (checked).
   - Resolver order: locked choice if still good, else preferred, else search JLC (in-stock, 2 pages + a Basic-only
     search) and rank Basic > Preferred > Extended, then already used on the board, then stock.
   - Stock needed = positions × boards × 1.1 + JLC's attrition for that part.
   - Lock `hw/<board>/bom.lock.json` (committed) covers every position any build can fit.
   - Build output `hw/<board>/out/<build>-bom.csv` and `-report.md` (substitutions, Extended count); `out/` ignored.
   - CPL needs the PCB: comes with layout (rotation fixes from the footprint/part pairs).
   - Tested: `--qty 60000` swaps BZT52C3V6 and USBLC6-2SC6 to other makers' parts and names the fixed parts that run
     short; a stale lock is refused.
2. Functional groups with automatic pin-table checks (INA22x, TPS22918-class switches, single-gate logic, LDOs).
3. Deltas (value changes to other parts, DNP swaps), with design checks re-run after a swap (for example the divider
   output voltage).
4. Maybe later: other suppliers, and global-sourcing pre-orders.
5. **Order kit to cart** (user asked 2026-11-22: "can we go all the way to populating a JLCPCB order? how do we
   minimize human involvement"). Approved as a plan 2026-11-22; built after layout.
   - `python -m order <board> --without ... --qty N`: `kicad-cli` exports Gerbers and drill files, the resolver
     makes BOM + CPL (rotation fixes) and checks stock for N, then writes one folder per build with an order sheet
     (board settings: layers, thickness, finish, assembly side).
   - Claude in Chrome (the user's signed-in session, background tab) fills the JLC quote and assembly pages from
     that folder and stops at the cart. The user checks JLC's placement preview and pays.
   - JLC's official API (https://api.jlcpcb.com) is gated: applications are reviewed on past orders and business
     size. The Ordering tier covers Gerber upload, pricing and PCB/stencil orders. No source confirms SMT assembly
     ordering through it (checked 2026-11-22). Not worth applying for now; the browser route covers assembly.

## Open questions for the user

None. (Answered 2026-11-22: design approved, phase 1 built now.)

## Findings

- JLC's search results carry each part's attributes (`attributes`: Resistance, Tolerance, Capacitance, Temperature
  Coefficient, Voltage Rating, Illumination Color...), so specs match without a per-part detail call.
- Request filters that work: `stockFlag: true` (in stock only), `componentLibraryType: "base"` (Basic only).
- A 100-result search takes about 2.5 s, an exact-code lookup about 0.4 s. So the resolver searches only when the
  locked and preferred parts are both unusable; a normal `--update` takes about 4 s per board.

## Progress log

- [x] Plan written (2026-11-15).
- [x] Per-order option selection: designed and built (`tools/bom`, 2026-11-20).
- [x] User review of the design (2026-11-22).
- [x] Phase 1 without CPL (2026-11-22).
- [ ] CPL export, with layout.
- [ ] Phase 2: groups with pin-table checks.
- [ ] Phase 3: deltas.
- [ ] Phase 5: order kit to cart, after layout.
