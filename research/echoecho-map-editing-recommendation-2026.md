# EchoEcho Map Editing Recommendation (2026)

See also:
- `react-native-map-editing-2026.md`
- `web-gis-map-editing-2026.md`
- `map-editing-products-2026.md`
- `echoecho-map-editing-proposal-2026.md`

## Recommendation

Do not chase a drop-in React Native polygon editor for `@rnmapbox/maps`.

There is no strong maintained 2026 package that cleanly delivers EchoEcho's required editing workflow on top of the current native map stack.

### Near-Term

Build a constrained native geometry editor in the admin app for:
- polygon redraw
- vertex edit
- add/delete vertices
- entrance and POI placement
- explicit route segment authoring
- reset / undo / save / discard

### References To Borrow From

- `terra-draw` for architecture
- `Geoman` for editing UX
- `QField`, `Mergin Maps`, and `Every Door` for mobile workflow patterns

### Longer-Term

If the editing workflow becomes substantially more advanced, add a dedicated web editor.

Preferred future stacks:
- `MapLibre + Geoman` for speed
- `MapLibre/OpenLayers + Terra Draw` for control
