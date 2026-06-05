# Manual test: Turn (group rotation)

**Build:** `feat/turn-rotate-selection` @ `1796e43`  
**URL:** http://localhost:5199/ (already running; do not restart servers)  
**Start:** blank default **1×1×1** home, one cube, Ortho default view  
**Time:** ~15 minutes  

Labels below match the live UI (Inspect / MODIFY / Motion dock).

---

## Phase A — Build an asymmetric multi-cube selection  
*(risk: setup; multi-select + Set edit target)*

1. **ACTION:** On the left rail **SCENE** tab, find the **Toggle build mode** switch. Turn it **on** (checked).  
   **EXPECTED:** Build mode is active. Semi-transparent neighbor slots appear on the open faces of the centre cube.  
   *Closes: setup*

2. **ACTION:** Click the neighbor slot on the cube’s **right** side (+X, along the red axis line if axes are visible).  
   **EXPECTED:** A second cube appears attached on +X. You now have two cubes side by side.  
   *Closes: multi-cube setup*

3. **ACTION:** Click the neighbor slot on the **front** of the **original** centre cube (toward you / out of the screen, +Z if the red line is X). Prefer the face that makes an **L**, not a straight line.  
   **EXPECTED:** A third cube appears. The three cubes form an **L** (or a clear bent arm), not a symmetric block or full square. If you accidentally made a straight line, undo (step 4) and pick a different face.  
   *Closes: asymmetric arrangement for joint-body check*

4. **ACTION:** Press **⌘Z** (Undo) once only if the third cube was wrong; re-place until you have an obvious L. Then turn **Toggle build mode** **off**.  
   **EXPECTED:** Build slots disappear. Three solid cubes remain.  
   *Closes: setup*

5. **ACTION:** Click the **corner** cube of the L (the tip of one arm). Then **Shift-click** the other two cubes so all three are in the selection set.  
   **EXPECTED:** Orange selection chrome on all three. Inspect panel shows **Selection** readout **Set 3** (or similar count). **Clear** button appears next to **Similar**.  
   *Closes: multi-cube selection*

6. **ACTION:** On the Inspect panel, find the segmented control **Edit target** with options **Part** and **Set 3**. Click **Set 3**.  
   **EXPECTED:** **Set 3** is pressed. Turns will apply to the whole set, not only the primary cube.  
   *Closes: joint turn targets the selection set (without this, only one cube turns)*

7. **ACTION:** Click Inspect tab **modify**. Confirm subtab **Dimensions** is pressed (not **Style**).  
   **EXPECTED:** You see **Home** readout (e.g. `X… Y… Z…`), **Width** / **Height** / **Depth**, **Offset X/Y/Z**, then **Turn axis**, **Direction**, **Turn** amounts **¼** and **½**, and **Snap home**.  
   *Closes: turn affordances present*

---

## Phase B — Negative check: no full-turn remnant  
*(risk: full-turn removed)*

8. **ACTION:** Look at the **Turn** control (segmented next to / under **Direction**). Count the amount buttons.  
   **EXPECTED:** Exactly **two** amounts: **¼** and **½**. There is **no** **1**, **full**, or third amount. No greyed-out dead full-turn control.  
   *Closes: no full-turn option*

---

## Phase C — Direction labels (CCW) from default view  
*(risk: label vs screen direction — highest value visual proof)*

Default view is **Ortho**, face-on. **Turn axis** defaults to **Y** (vertical). **Direction** defaults to **CCW**.

9. **ACTION:** Leave **Turn axis** on **Y**, **Direction** on **CCW**. Note which cube is the **right-hand tip** of the L (higher X). Press **¼**.  
   **EXPECTED:** The whole L rotates **as one piece** about its centre. From the default face-on view, a **CCW** turn about **Y** should move the right-hand arm **toward you** or **left/right in a coherent orbit** — the L’s silhouette **reorients in the plane**; cubes **do not** stay in place while only spinning on their own centres.  
   *Closes: CCW label vs visible motion; joint body*

10. **ACTION:** If unsure about CCW, press **⌘Z** once to undo the ¼, switch **Direction** to **CW**, press **¼** again.  
    **EXPECTED:** Motion is the **opposite** of step 9. Same rigid L, opposite way.  
    *Closes: CW opposite of CCW*

11. **ACTION:** Press **⌘Z** until the L is back to the pre-turn pose from after Phase A (homes still an L on the grid).  
    **EXPECTED:** Exact prior arrangement; no drift or residual tilt.  
    *Closes: undo after direction checks*

---

## Phase D — Joint body (unmissable defect catch)  
*(risk: independent per-cube spin vs shared pivot)*

**What “joint” looks like:** every cube’s **centre** moves on a circle around the **shared centre** of the three cubes; relative distances between centres stay fixed; the L **sweeps** as a rigid arm.

**What “broken independent” looks like:** each cube **stays on its grid home** and only **spins in place**; the L footprint does **not** reorient — only each cube’s face markings / edges revolve.

12. **ACTION:** Confirm **Edit target** is still **Set 3**. **Turn axis** **Y**, **Direction** **CCW**, press **½**.  
    **EXPECTED:** After a half turn about Y, the L is **upside-down in plan** (arms swapped to opposite sides of the centre). Cube **homes** in the panel **Home** readout may still show original grid coords (coord stays fixed; motion is offset). The three cubes remain an L, **rotated**, not three cubes each twirling on the spot.  
    *Closes: joint rigid body (D2)*

13. **ACTION:** Without undoing, click **only one** tip cube so the set collapses to a single selection (or press **Clear** on the selection block then re-select one cube). Press **¼** with **Y** / **CCW**.  
    **EXPECTED:** That single cube orbits about **its own** centre only (small spin of one body). Compare mentally to step 12: multi-set move was large arm motion; single is local.  
    *Closes: contrast single vs set (optional sanity)*

14. **ACTION:** Re-select all three (**Shift-click**), set **Edit target** to **Set 3** again. **⌘Z** as needed until the L matches the post–Phase A pose.  
    **EXPECTED:** Back to the known L, ready for axis sweep.  
    *Closes: restore setup*

---

## Phase E — All three axes, both directions, quarter and half  
*(risk: axis / amount coverage)*

Work on **Set 3**. After each press, glance that the **L stays rigid** (joint), then **⌘Z** once to reset before the next axis unless the script says otherwise.

15. **ACTION:** **Turn axis** **X**, **Direction** **CCW**, **¼**.  
    **EXPECTED:** L tumbles about horizontal X; joint motion; no coord change in **Home** for a representative cube if you still have one primary selected.  
    *Closes: axis X + quarter + CCW*

16. **ACTION:** **⌘Z**. **Direction** **CW**, **¼** on **X**.  
    **EXPECTED:** Opposite tumble to step 15.  
    *Closes: axis X + CW*

17. **ACTION:** **⌘Z**. **Turn axis** **Z**, **CCW**, **¼**.  
    **EXPECTED:** Rotation about depth axis; joint L motion in the view plane.  
    *Closes: axis Z + quarter*

18. **ACTION:** **⌘Z**. **Turn axis** **Y**, **CCW**, **½**.  
    **EXPECTED:** Half turn about Y; L reoriented 180° in plan; still one rigid body.  
    *Closes: half amount*

19. **ACTION:** Without undoing, **Y** / **CCW** / **¼** again (stack turns).  
    **EXPECTED:** Further quarter on top of the half; pose advances; no jump to origin or dissolve of the L.  
    *Closes: stacked turns*

20. **ACTION:** Press **⌘Z** repeatedly until you return to the post–Phase A L (before Phase E).  
    **EXPECTED:** Exact recovery of the L after several undos; no leftover offsets or odd Euler tilt.  
    *Closes: undo after stacked turns*

---

## Phase F — Burial and edge-claim re-resolution  
*(risk: hidden faces / shared edges after turn)*

21. **ACTION:** Turn **Toggle build mode** **on**. From the centre of the L, add cubes until you have a **2×2 flat square** on the ground plane (four cubes in a square, all adjacent). Turn build mode **off**.  
    **EXPECTED:** Four cubes packed; **internal shared faces are not drawn** (you should not see a dark double wall between neighbors). Outer silhouette is a larger square.  
    *Closes: packed burial baseline*

22. **ACTION:** Select all four cubes (**Shift-click**), set **Edit target** to **Set 4**. **Turn axis** **Y**, **CCW**, **¼**.  
    **EXPECTED:** The block rotates 90° as one. After the turn, cubes that no longer sit face-to-face should **show faces that were buried** (new internal walls appear where the pack opened). Shared edges on still-touching pairs should remain a **single** seam, not a doubled thick edge.  
    *Closes: burial reveal + edge claim redraw*

23. **ACTION:** **⌘Z** once.  
    **EXPECTED:** Back to the packed square; internal faces hidden again as before the turn.  
    *Closes: undo restores burial*

---

## Phase G — Persistence (reload)  
*(risk: authored pose survives reload)*

24. **ACTION:** From a distinctive pose (e.g. after a **Y** **CCW** **¼** on the packed set, or re-apply if you undid). Note the silhouette. Reload the browser tab (hard refresh if needed: **⌘R**).  
    **EXPECTED:** Same cube count and same turned silhouette after load (project restore). Turn controls still **¼** / **½** only.  
    *Closes: reload persistence*

25. **ACTION:** If the project restored to an earlier snapshot without the turn, re-select set, re-apply **Y** **CCW** **¼**, reload again.  
    **EXPECTED:** Pose that was present at reload time is what comes back.  
    *Closes: persistence clarification*

---

## Phase H — Capture, turn, capture, play; camera still sane  
*(risk: camera maths refactor + state morph)*

26. **ACTION:** Expand the **Motion** dock if collapsed (**Expand Motion panel** / open until you see transport). Click **Snapshot current scene**.  
    **EXPECTED:** A state appears on the piece strip (first snapshot). **Play** may still be limited until a second state exists.  
    *Closes: capture state 1*

27. **ACTION:** With multi-cube **Set** still active, apply a clear turn (**Y** / **CCW** / **¼**). Optionally nudge the view with keypad **Rotate right** once. Click **Snapshot current scene** again.  
    **EXPECTED:** Second state on the strip; a transition gap between the two cards.  
    *Closes: capture state 2 after turn*

28. **ACTION:** Click **Play** on the Motion transport row.  
    **EXPECTED:** Playback morphs between the two states (cube poses interpolate). Motion should be continuous; no camera explosion, black frame, or stuck view.  
    *Closes: piece playback after turn*

29. **ACTION:** Click **Stop**. Use keypad **Reset view** or **Rotate** buttons a few times.  
    **EXPECTED:** Camera orbits/resets normally (refactor of axis maths must not break orbit).  
    *Closes: camera after shared maths extraction*

30. **ACTION:** If a state shows **Capture view → …** / **Recapture view → …** on the transport row, click it once after framing a deliberate view.  
    **EXPECTED:** Button label updates; selecting that state later can restore the framed view (no crash).  
    *Closes: camera capture control still works*

---

## Stop and tell me immediately if

1. **Multi-cube Set turn** leaves the L footprint fixed while each cube only spins on its home (independent spin) — joint pivot is broken.  
2. **CCW** and **CW** produce the **same** on-screen direction, or **CCW** clearly matches clockwise from the default Ortho view.  
3. A **full-turn** amount (**1** / full) appears, or **¼** / **½** are missing/disabled.  
4. After a turn that separates a packed block, **internal faces stay missing** or **shared edges double-draw**; or **⌘Z** / reload leaves cubes in the wrong place.

---

## Notes (affordances that do not exist)

- There is **no** free “turn angle degrees” scrub — only **¼** and **½**.  
- There is **no** full-turn control (by design at this SHA).  
- Multi-cube turn requires **Edit target → Set N**, not only multi-select.  
- **MODIFY** subtabs are **Dimensions** and **Style** only (no separate Shape tab for turn).
