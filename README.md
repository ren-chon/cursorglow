# CursorGlow

CursorGlow is a customizable cursor highlighting tool that adds a glowing effect around your mouse cursor. It features:

- Configurable highlight size, color, shape and broken animation
- Support for different cursor shapes (rounded square, circle)
- Adjustable inner and outer stroke widths
- Rotation effects
- Corner radius customization

The settings can be configured through JSON files:

- `settings.json`

Key settings include:
- `highlight_size`: Size of the glow effect (in pixels)
- `highlight_color`: RGBA color values for the glow [R, G, B, A]
- `corner_radius`: Roundness of corners for rounded square shape
- `rotation`: Rotation angle in degrees
- `shape`: "rounded_square" or "circle"
- `outer_stroke_width`: Width of outer highlight border
- `inner_stroke_width`: Width of inner highlight border
- `animation_enabled`: Enable/disable animation effects
- `animation_speed`: Speed of animations (lower is faster)

<!-- The tool uses GTK4 and Cairo for rendering smooth, hardware-accelerated graphics with minimal system resource usage. -->


## Installation

1. Clone the repository:

```bash
git clone https://github.com/ren-chon/cursorglow.git
```

2. Install dependencies:

```bash
dnf install gtk4-devel cairo-devel
# or
apt install libgtk-4-dev libcairo2-dev
```

3. Python dependencies:

```bash
pip install PyGObject cairo
```

4. Run the extension:

```bash
python3 ./cursorglow.py
```
