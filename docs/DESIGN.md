# Design

The visual direction for Waypoint's landing page (`site/index.html`). Waypoint
is a CLI/library, so this covers the marketing page only; the product itself is
a terminal experience. The page and the tool share one voice: precise,
technical, unhurried.

## 1. Aesthetic direction

**Waypoint is a dark trail-map for developers: an ink-slate topographic field,
a dashed route line, and a single amber trail-blaze marking the point you
resume from.** The whole page leans on one metaphor — a long route with a
marker partway along it — because that is literally what the tool does: it
remembers the last marker you passed so you never re-walk the trail.

## 2. Tokens

Colors:

- `--bg`: `#0e1116` (deep ink slate, never pure black)
- `--surface`: `#151a21` (raised panels)
- `--surface-2`: `#1c232c` (code blocks, insets)
- `--text`: `#e8edf2` (off-white)
- `--muted`: `#8b98a8` (slate-gray secondary text)
- `--accent`: `#f5a524` (trail-blaze amber — the "you are here" marker)
- `--accent-2`: `#4fd1c5` (signal teal — the route already covered)
- `--danger`: `#f87171` (a killed run)
- `--line`: `#232b35` (hairline borders, contour strokes)

Type:

- Display / wordmark + headings: **Space Grotesk** (geometric, technical),
  fallback `system-ui, sans-serif`.
- UI / body: **Inter**, fallback `system-ui, sans-serif`.
- Code: **JetBrains Mono**, fallback `ui-monospace, "SFMono-Regular", monospace`.
- Scale ~1.25 ratio; display weight 600–700, body 400–500.

Spacing on a 4/8px scale. Corner radius 10px (panels), 6px (chips/buttons).
Depth via layered shadows over the ink field, never flat single-hue panels.
Motion: UI transitions 160–220ms ease-out; the route line and blaze animate
slowly (1.6s+) so the page breathes without distracting.

## 3. Layout intent

- **Hero (the signature):** a wordmark top-left, a headline + subhead on the
  left, and on the right an animated **route**: a dashed path across a faint
  contour-line field with a pulsing amber waypoint pin at the resume point, and
  a short code sample below showing the crash → rerun → resume story. The route
  is the hero and fills its column.
- Below: a three-up benefits row (real capabilities, not gray-card filler), a
  "how it works" strip, an install/usage block with real commands, and an
  FAQ/answer section (useful copy).
- Composes at 1440 (two columns), 768 (stacked, route full-width), and 390
  (single column, route scales down, no horizontal scroll). No dead margins:
  the contour field extends to the page edges as atmosphere.

## 4. Signature detail

The **animated route line**: a dashed SVG path with `stroke-dashoffset`
drifting slowly, a teal "covered" segment up to an amber pulsing waypoint pin,
and a faint dashed "remaining" segment beyond it. It restates the pitch without
a word of copy. `prefers-reduced-motion` freezes it (marker still shown, no
drift/pulse).

## 5. Brand assets

- **Favicon:** inline SVG data-URI — an amber waypoint pin (a rounded marker
  with a dot) on the ink background. No default globe.
- **Wordmark:** "Waypoint" in Space Grotesk 700 with a small amber pin glyph
  standing in for the dot, top-left, consistent with the favicon.

The page honors `prefers-color-scheme` by staying legible; the design is
dark-first (a developer trail-map at dusk) and does not flash white.
