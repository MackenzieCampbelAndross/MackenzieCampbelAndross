import urllib.request
import re
import os
import xml.etree.ElementTree as ET

def fetch_and_generate_svg(output_path):
    url = "https://github.com/users/MackenzieCampbelAndross/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req).read().decode("utf-8")

    # Extract contribution count
    count_match = re.search(r'([\d,]+)\s+contributions\s+in the last year', html)
    total_contribs = count_match.group(1) if count_match else "1,873"

    # Extract month labels from thead
    # Each td has colspan and text
    month_labels = []
    thead_match = re.search(r'<thead>(.*?)</thead>', html, re.DOTALL)
    current_col = 0
    if thead_match:
        for m in re.finditer(r'<td[^>]*colspan="(\d+)"[^>]*>.*?<span aria-hidden="true"[^>]*>([^<]+)</span>', thead_match.group(1), re.DOTALL):
            span = int(m.group(1))
            name = m.group(2).strip()
            month_labels.append((current_col, name))
            current_col += span

    # Extract grid cells from tbody
    # 7 rows
    tbody_match = re.search(r'<tbody>(.*?)</tbody>', html, re.DOTALL)
    if not tbody_match:
        raise ValueError("Could not find tbody in contributions html")

    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', tbody_match.group(1), re.DOTALL)
    
    # We want a 2D matrix [col][row] or list of cells with col, row, level, count, date
    grid_cells = []
    
    # In GitHub table, row 0 is Sunday, row 1 is Monday ... row 6 is Saturday
    for r_idx, row_html in enumerate(rows):
        cells = re.findall(r'<td[^>]*data-date="([^"]+)"[^>]*data-level="([^"]+)"', row_html)
        for c_idx, (date_str, level_str) in enumerate(cells):
            grid_cells.append({
                "col": c_idx,
                "row": r_idx,
                "date": date_str,
                "level": int(level_str)
            })

    # Total columns is max(col) + 1 (usually 53)
    num_cols = max(c["col"] for c in grid_cells) + 1
    print(f"Num columns: {num_cols}, total cells: {len(grid_cells)}")

    # Palette matching GitHub Dark Mode / Obsidian pitch-black:
    # Level 0: #161b22 (empty cell)
    # Level 1: #0e4429
    # Level 2: #006d32
    # Level 3: #26a641
    # Level 4: #39d353
    COLORS = {
        0: "#161b22",
        1: "#0e4429",
        2: "#006d32",
        3: "#26a641",
        4: "#39d353"
    }

    # SVG layout geometry:
    # Total width: 850
    # Card container: width: 846, height: 210
    # Left padding inside card for labels: 40px
    # Top padding for title: 38px
    # Grid starts at x=52, y=68
    # Square size: 10.5 x 10.5, gap: 3.2px -> pitch = 13.7px
    # 53 columns * 13.7 = ~726px
    # 52 + 726 = 778px
    # 7 rows * 13.7 = ~96px
    # y: 68 to 164
    # Bottom legend at y=182: "Less" [0][1][2][3][4] "More"
    
    cell_size = 10.5
    gap = 3.2
    pitch = cell_size + gap
    grid_start_x = 56
    grid_start_y = 66

    svg_cells = []
    for c in grid_cells:
        x = grid_start_x + c["col"] * pitch
        y = grid_start_y + c["row"] * pitch
        color = COLORS.get(c["level"], COLORS[0])
        # Border for level 0 to give that crisp GitHub tile feel
        border_attr = 'stroke="rgba(255,255,255,0.04)" stroke-width="0.8"' if c["level"] == 0 else 'stroke="rgba(255,255,255,0.1)" stroke-width="0.5"'
        svg_cells.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell_size}" height="{cell_size}" rx="2.5" fill="{color}" {border_attr}/>')

    # Month text labels
    month_svgs = []
    for col_idx, name in month_labels:
        mx = grid_start_x + col_idx * pitch
        month_svgs.append(f'<text x="{mx:.1f}" y="{grid_start_y - 8}" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Inter, sans-serif" font-size="10.5" fill="#7d8590">{name}</text>')

    # Day labels (Mon at row 1, Wed at row 3, Fri at row 5)
    day_labels = [
        (1, "Mon"),
        (3, "Wed"),
        (5, "Fri")
    ]
    day_svgs = []
    for r_idx, name in day_labels:
        dy = grid_start_y + r_idx * pitch + 8.5
        day_svgs.append(f'<text x="{grid_start_x - 10}" y="{dy:.1f}" text-anchor="end" font-family="-apple-system, BlinkMacSystemFont, \'Segoe UI\', Inter, sans-serif" font-size="10" fill="#7d8590">{name}</text>')

    # Legend at bottom right
    # "Less" [0][1][2][3][4] "More"
    legend_right_x = grid_start_x + num_cols * pitch - 5
    legend_svg = f'''
    <g transform="translate({legend_right_x - 135}, 184)">
      <text x="0" y="9" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif" font-size="10" fill="#7d8590">Less</text>
      <rect x="28" y="0" width="10.5" height="10.5" rx="2" fill="{COLORS[0]}" stroke="rgba(255,255,255,0.06)" stroke-width="0.8"/>
      <rect x="42" y="0" width="10.5" height="10.5" rx="2" fill="{COLORS[1]}"/>
      <rect x="56" y="0" width="10.5" height="10.5" rx="2" fill="{COLORS[2]}"/>
      <rect x="70" y="0" width="10.5" height="10.5" rx="2" fill="{COLORS[3]}"/>
      <rect x="84" y="0" width="10.5" height="10.5" rx="2" fill="{COLORS[4]}"/>
      <text x="100" y="9" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif" font-size="10" fill="#7d8590">More</text>
    </g>
    <text x="{grid_start_x}" y="193" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif" font-size="10" fill="#57606a">Learn how we count contributions</text>
    '''

    all_cells_str = "\n    ".join(svg_cells)
    all_months_str = "\n    ".join(month_svgs)
    all_days_str = "\n    ".join(day_svgs)

    svg_content = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 850 215" width="100%" height="215">
  <defs>
    <!-- Card Background -->
    <linearGradient id="contribBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0e0e12"/>
      <stop offset="100%" stop-color="#020204"/>
    </linearGradient>

    <!-- Crisp Silver Rim -->
    <linearGradient id="contribBorder" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.25"/>
      <stop offset="50%" stop-color="#ffffff" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0.02"/>
    </linearGradient>

    <filter id="contribShadow" x="-2%" y="-5%" width="104%" height="115%">
      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000000" flood-opacity="0.9"/>
    </filter>
  </defs>

  <!-- Container Box -->
  <rect x="2" y="2" width="846" height="211" rx="10" fill="url(#contribBg)" stroke="url(#contribBorder)" stroke-width="1.2" filter="url(#contribShadow)"/>

  <!-- Card Header -->
  <text x="24" y="30" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif" font-size="14.5" font-weight="600" fill="#f0f6fc">{total_contribs} contributions in the last year</text>
  <text x="822" y="30" text-anchor="end" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, sans-serif" font-size="11" fill="#7d8590">Contribution settings &#9662;</text>

  <!-- Month Labels -->
    {all_months_str}

  <!-- Day Labels -->
    {all_days_str}

  <!-- Contribution Heatmap Squares -->
    {all_cells_str}

  <!-- Footer / Legend -->
    {legend_svg}
</svg>'''

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    
    ET.parse(output_path)
    print(f"Successfully generated and validated {output_path}!")

if __name__ == "__main__":
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(repo_root, "assets", "contributions.svg")
    fetch_and_generate_svg(out)
