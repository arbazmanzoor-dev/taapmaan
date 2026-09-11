---
name: Civic Thermal Command
colors:
  surface: '#fff8f5'
  surface-dim: '#e2d8d2'
  surface-bright: '#fff8f5'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#fcf2eb'
  surface-container: '#f6ece6'
  surface-container-high: '#f0e6e0'
  surface-container-highest: '#eae1da'
  on-surface: '#1f1b17'
  on-surface-variant: '#59413a'
  inverse-surface: '#342f2b'
  inverse-on-surface: '#f9efe8'
  outline: '#8d7168'
  outline-variant: '#e1bfb5'
  surface-tint: '#ac3400'
  primary: '#9b2f00'
  on-primary: '#ffffff'
  primary-container: '#c2410c'
  on-primary-container: '#ffece7'
  inverse-primary: '#ffb59d'
  secondary: '#555f6f'
  on-secondary: '#ffffff'
  secondary-container: '#d6e0f3'
  on-secondary-container: '#596373'
  tertiary: '#983311'
  on-tertiary: '#ffffff'
  tertiary-container: '#b94a27'
  on-tertiary-container: '#ffede8'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdbd0'
  primary-fixed-dim: '#ffb59d'
  on-primary-fixed: '#390c00'
  on-primary-fixed-variant: '#832600'
  secondary-fixed: '#d9e3f6'
  secondary-fixed-dim: '#bdc7d9'
  on-secondary-fixed: '#121c2a'
  on-secondary-fixed-variant: '#3d4756'
  tertiary-fixed: '#ffdbd1'
  tertiary-fixed-dim: '#ffb59f'
  on-tertiary-fixed: '#3a0a00'
  on-tertiary-fixed-variant: '#842503'
  background: '#fff8f5'
  on-background: '#1f1b17'
  surface-variant: '#eae1da'
typography:
  display-hero:
    fontFamily: Bricolage Grotesque
    fontSize: 2.75rem
    fontWeight: '700'
    lineHeight: 3rem
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Bricolage Grotesque
    fontSize: 2rem
    fontWeight: '700'
    lineHeight: 2.25rem
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Bricolage Grotesque
    fontSize: 2rem
    fontWeight: '600'
    lineHeight: 2.375rem
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Bricolage Grotesque
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 1.875rem
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Bricolage Grotesque
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: 1.875rem
    letterSpacing: -0.015em
  headline-sm:
    fontFamily: Bricolage Grotesque
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: 1.5rem
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Inter
    fontSize: 1.0625rem
    fontWeight: '400'
    lineHeight: 1.625rem
  body-md:
    fontFamily: Inter
    fontSize: 0.9375rem
    fontWeight: '400'
    lineHeight: 1.5rem
  body-sm:
    fontFamily: Inter
    fontSize: 0.8125rem
    fontWeight: '400'
    lineHeight: 1.25rem
  telemetry-metric-lg:
    fontFamily: Space Mono
    fontSize: 2.25rem
    fontWeight: '700'
    lineHeight: 2.5rem
    letterSpacing: -0.02em
  telemetry-metric-md:
    fontFamily: Space Mono
    fontSize: 1.375rem
    fontWeight: '700'
    lineHeight: 1.75rem
    letterSpacing: -0.01em
  telemetry-data:
    fontFamily: Space Mono
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: 1.25rem
  label-caps:
    fontFamily: Space Mono
    fontSize: 0.6875rem
    fontWeight: '700'
    lineHeight: 0.875rem
    letterSpacing: 0.06em
  caption:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '500'
    lineHeight: 1rem
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-tablet: 1.5rem
  margin-desktop: 2rem
  space-2xs: 0.25rem
  space-xs: 0.5rem
  space-sm: 0.75rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
---

## Brand & Style

This design system delivers an operational, mission-critical console for municipal corporations, state disaster management authorities, and urban public health officers monitoring severe heat-wave episodes across Indian metropolises. 

The visual style blends **Civic Editorial Authority** with **High-Density Control-Room Precision**. Rather than defaulting to dark, fatigue-inducing command center themes, the design relies on an intentional warm off-white canvas inspired by sun-bleached administrative paper, architectural stone, and natural terracotta. The interface emphasizes:
- **Absolute Composure Under Crisis:** Clean card surfaces, quiet negative space, and disciplined typography reduce cognitive strain during 14-hour monitoring shifts.
- **Operational Honesty:** Explicit data provenance (sensor IDs, satellite passes, confidence intervals, and sync latencies) built directly into telemetry displays.
- **Strict Color Restraint:** The UI remains largely achromatic and neutral terracotta-accented; the 5-tier heat-risk palette is quarantined strictly for alert statuses, ward severity maps, and thermal thresholds to prevent alarm fatigue.

## Colors

The color system organizes spatial and operational hierarchy through strict surface discipline, reserving vibrant chroma strictly for emergency status indicators.

### Base Canvases & Structuring Neutrals
- **App Canvas:** `#FAF8F5` (Warm off-white base reducing eye fatigue in bright operations rooms).
- **Surface Elevation (Cards/Panels):** `#FFFFFF` (Crisp pure white).
- **Subtle Fill / Muted Canvas:** `#F4F0EA` (For headers, inactive table rows, telemetry blocks).
- **Structural Hairlines:** `#E6E2DA` (Divider rules, panel perimeters, structural grid lines).
- **Text Primary:** `#1C1917` (High-contrast stone black for critical legibility).
- **Text Secondary / Metadata:** `#57534E` (Mid-tone stone for labels, units, and timestamps).
- **Text Muted:** `#A8A29E` (Grid markings, inactive icons, hairline indicators).

### Civic Brand Accents
- **Terracotta Primary:** `#C2410C` (Primary action triggers, active tabs, selected states).
- **Terracotta Deep (Hover/Active):** `#9A3412` (Pressed states, key operational anchors).
- **Terracotta Wash:** `#FFF7ED` (Selected navigation rows, highlighted configuration tiles).

### 5-Level Heat-Risk Operational Scale
These tokens are strictly restricted to temperature metrics, map layers, severity badges, and ward status boards:
- **Level 1 (Normal / Low Risk):**
  - Solid: `#15803D` | Wash: `#F0FDF4` | Border: `#BBF7D0` | Text: `#166534`
- **Level 2 (Moderate Advisory):**
  - Solid: `#B45309` | Wash: `#FEF3C7` | Border: `#FDE68A` | Text: `#92400E`
- **Level 3 (High Warning):**
  - Solid: `#EA580C` | Wash: `#FFEDD5` | Border: `#FED7AA` | Text: `#9A3412`
- **Level 4 (Severe Emergency):**
  - Solid: `#DC2626` | Wash: `#FEF2F2` | Border: `#FECACA` | Text: `#991B1B`
- **Level 5 (Extreme Crisis):**
  - Solid: `#9333EA` | Wash: `#FAF5FF` | Border: `#E9D5FF` | Text: `#6B21A8`

## Typography

The typographic hierarchy separates editorial authority, legible narrative guidelines, and machine telemetry:

- **Bricolage Grotesque (Display & Headings):** Conveys official civic gravitas and rapid scan-ability. Its expressive ink traps and structural heft evoke broadsheet news and civic directives.
- **Inter (User Interface & Body):** Handles tactical instructions, contingency protocols, administrative notes, and dense tabular text with maximum clarity.
- **Space Mono (Telemetry, Timestamps, Latency, and Sensor Feeds):** Tabular, monospaced numbers ensure real-time temperature fluctuations, wet-bulb metrics, ward population stats, and UTC/IST timestamps align across columns without jumping.

Always pair high-impact telemetry values (`telemetry-metric-lg`) with uppercase monospaced labels (`label-caps`) positioned either directly above or below to ensure unambiguous unit comprehension (e.g., `43.8 °C` with `WET-BULB GLOBE TEMP`).

## Layout & Spacing

The console utilizes an adaptive 12-column fluid grid configured for continuous monitoring across field tablets, desktop workstations, and wall-mounted projection screens:

- **Desktop & Multi-Display (≥1280px):** 12-column grid, `gutter-desktop` (24px), `margin-desktop` (32px). Maximum container constraint of 1680px for standard command centers, fluid on ultra-wide ops walls. Supports asymmetric workspace layouts (e.g., 8-column ward geo-visualization paired with a 4-column live dispatch and hospital triage stream).
- **Tablet (768px – 1279px):** 8-column grid, `gutter` (16px), `margin-tablet` (24px). Primary map and telemetry collapse into balanced split panels or stacked triage modules for field supervisors.
- **Mobile Handheld (≤767px):** 4-column grid, `gutter` (16px), `margin` (16px). All multi-column telemetry arrays stack vertically into single-card feeds with sticky emergency broadcast triggers.

Consistent pacing relies on the base-8 modular scale:
- Use `space-2xs` (4px) and `space-xs` (8px) for inline metadata badges, unit offsets, and internal chip padding.
- Use `space-sm` (12px) and `space-md` (16px) for interior card padding and form control clusters.
- Use `space-lg` (24px) and `space-xl` (32px) for structural section separation and multi-panel boundaries.

## Elevation & Depth

To avoid visual murkiness and glare in operational environments, this system shuns heavy dropshadows, glassmorphism blurs, and saturated dark surfaces. Depth is established through **architectural stratification**:

1. **Substrate Level (Z0):** The app canvas (`#FAF8F5`) sits furthest back, establishing the warm neutral grounding.
2. **Surface Level (Z1 - Cards & Structural Panels):** Pure white (`#FFFFFF`) card surfaces sit over the canvas, bounded by a continuous 1px hairline border (`#E6E2DA`) and an ultra-soft diffused ambient shadow:
   `box-shadow: 0 1px 3px rgba(28, 25, 23, 0.04), 0 6px 16px -4px rgba(28, 25, 23, 0.03);`
3. **Elevated Overlays & Flyouts (Z2):** Slide-over diagnostic drawers, ward drill-down inspectors, and operational popovers maintain a `#FFFFFF` fill with an intensified hairline border (`#D6D1C7`) and a deeper soft perimeter spread:
   `box-shadow: 0 4px 6px -1px rgba(28, 25, 23, 0.05), 0 12px 28px -6px rgba(28, 25, 23, 0.08);`
4. **Active Heat-Alert States:** Surfaces indicating Level 4 or Level 5 risks do not cast colored neon glows. Instead, they leverage internal tinted washes (`#FEF2F2` or `#FAF5FF`) framed by crisp, saturated 1.5px structural borders (`#FECACA` or `#E9D5FF`) with neutral ambient grounding.

## Shapes

The geometric framework balances human municipal software with clean mathematical discipline:

- **Surface Standard:** All primary monitoring cards, operational modules, and map framing containers strictly use a **12px corner radius** (`rounded-lg` under roundedness level 2). This softens the dense interface while remaining precise and space-efficient.
- **Controls & Form Elements:** Input fields, buttons, dropdown triggers, and triage filters use an **8px corner radius** (`rounded-md`).
- **Telemetry Chips & Badges:** Data provenance tags, confidence indicators, and heat alert badges use a **6px corner radius** to align cleanly with monospaced data blocks.
- **Borders:** Consistent 1px solid hairline (`#E6E2DA`) across all neutral cards; increased to 1.5px solid for active severity borders. Never use dashed or decorative borders in operational states.

## Components

### Buttons
- **Primary Operational Button:** Terracotta `#C2410C` background, `#FFFFFF` bold text, 8px radius, height 40px (padding: 0 16px). Hover: `#9A3412`. Active: `#7C2D12`. Focused: 2px offset ring in `#C2410C`.
- **Secondary / Administrative Button:** Pure `#FFFFFF` background, hairline border `#E6E2DA`, `#1C1917` text. Hover: `#F4F0EA` fill and `#D6D1C7` border.
- **Emergency Action Trigger (Broadcast / Dispatch):** Level 4 Red `#DC2626` background, `#FFFFFF` text, paired with uppercase monospaced sub-labeling. Used strictly for mass SMS alerts, cooling center activations, and water tanker deployment orders.

### Heat-Risk Severity Badges & Status Chips
- Pill-shaped or 6px rounded indicators with uppercase `label-caps` typography.
- Consists of:
  1. A 6px solid circular pulse indicator (solid tier color).
  2. Text label (e.g., `LVL 4: SEVERE`).
  3. Metric bounds (e.g., `> 44.5 °C`).
- Always structured using the dedicated wash background, matching border, and high-contrast foreground text specified in the color section.

### Telemetry Cards & Metric Blocks
- Pure white `#FFFFFF` surface, 12px radius, hairline border `#E6E2DA`.
- **Header:** Uppercase `label-caps` in `#57534E` paired with an operational status dot.
- **Body:** Dominant metric in Space Mono (`telemetry-metric-lg`), accompanied by baseline delta (e.g., `+3.2°C vs 10yr avg`).
- **Footer / Provenance Strip:** Border-top 1px `#F4F0EA`, displaying sensor ID (`IMD-STN-4201`), sync timestamp (`08:42:10 IST`), and transmission confidence (`99.4% VALID`).

### Input Fields & Selectors
- Background `#FFFFFF`, 8px radius, 1px border `#E6E2DA`, height 40px. Font: Inter 14px (`body-md`).
- Focused state: `#FFFFFF` background, border `#C2410C`, box-shadow `0 0 0 3px rgba(194, 65, 12, 0.12)`.
- Numeric input overrides: Numbers displayed in Space Mono for coordinate entries, threshold inputs, and dispatch counts.

### Checkboxes & Radio Controls
- Size 18×18px with 4px radius (checkbox) or circular (radio).
- Default: `#FFFFFF` fill, 1.5px border `#A8A29E`.
- Checked: `#C2410C` fill with white checkmark/dot.

### Provenance & Honesty Banners
- Subtle container embedded above analytical tables and heat maps.
- Background `#F4F0EA`, 8px radius, 1px border `#E6E2DA`.
- Displays source authority metadata (e.g., "India Meteorological Department INSAT-3D Thermal Feed · Calibrated 6m ago · 4 Station Feeds Degraded").

### Tabular Ward Roster
- Header: `#FAF8F5`, uppercase `label-caps`, 36px height, hairline bottom divider.
- Rows: `#FFFFFF` alternating with clean hover highlight `#FFF7ED`. 48px row height for rapid finger-tap or mouse target acquisition.
- Critical columns (Wet-Bulb Index, Vulnerable Density, Water Deficit) right-aligned in Space Mono.