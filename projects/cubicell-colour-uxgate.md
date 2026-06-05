# Cubicell accent colour — owner UX gate

Base: `feat/accent-colour` worktree. Dev http://localhost:5174 · Preview http://127.0.0.1:4175  
Authoring surface under test: Inspect **Color** (Theme / Black / White / **Accent**) on a selected face or edge.

Fill **Verdict** with pass / fail and a short note. Judge by eye on the canvas.

| # | Outcome | Verdict |
|---|---------|---------|
| 1 | Author **Accent** on one face of a black cube. Face reads as a hue at pinned lightness, not Theme/Black/White. | |
| 2 | Author **Accent** on one face of a white cube. Same hue family as (1); still readable on white. | |
| 3 | Author **Accent** on one edge. Edge hue matches face accent family; thickness/opacity unchanged by the colour pick. | |
| 4 | Accent face against a **black** neighbour: both roles stay distinct; no muddying or accidental theme bleed. | |
| 5 | Accent face against a **white** neighbour: both roles stay distinct; contrast still holds. | |
| 6 | Transition **into** Accent (from Theme or Black/White): canvas morph is clean, no flash or wrong intermediate. | |
| 7 | Transition **out of** Accent (to Theme or Black/White): settles on the target role with no residual hue. | |
| 8 | After hard reload, authored Accent on face and edge is still present and correct. | |
| 9 | Export or state thumbnail still shows Accent where authored (not collapsed to Theme/Black/White). | |

**Ship call:** ship / hold — ______  
**Date:** ______
