"""NickelScope PDF Report Generator — Clean & Professional Design."""
import io, os, re
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether, Flowable
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics import renderPDF

W, H = A4

# ── Color Palette ──
NAVY      = HexColor('#0B1D3A')
BLUE      = HexColor('#1565C0')
BLUE_LT   = HexColor('#E3F2FD')
BLUE_MED  = HexColor('#42A5F5')
TEAL      = HexColor('#00897B')
TEAL_LT   = HexColor('#E0F2F1')
AMBER     = HexColor('#FF8F00')
AMBER_LT  = HexColor('#FFF8E1')
RED       = HexColor('#C62828')
RED_LT    = HexColor('#FFEBEE')
GRAY_900  = HexColor('#212121')
GRAY_700  = HexColor('#616161')
GRAY_500  = HexColor('#9E9E9E')
GRAY_300  = HexColor('#E0E0E0')
GRAY_100  = HexColor('#F5F5F5')
BG_CREAM  = HexColor('#FAFBFC')


# ══════════════════════════════════════════════════════════════
#  Custom Flowables
# ══════════════════════════════════════════════════════════════

class SectionHeader(Flowable):
    """Styled section header with colored left bar."""
    def __init__(self, number, title, width=170*mm, height=14*mm):
        Flowable.__init__(self)
        self.number = number
        self.title = title
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        # Background bar
        c.setFillColor(BLUE_LT)
        c.roundRect(0, 0, self.width, self.height, 3, fill=1, stroke=0)
        # Left accent bar
        c.setFillColor(BLUE)
        c.roundRect(0, 0, 5, self.height, 2, fill=1, stroke=0)
        # Number circle
        c.setFillColor(BLUE)
        c.circle(18, self.height / 2, 8, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont('Helvetica-Bold', 10)
        c.drawCentredString(18, self.height / 2 - 3.5, str(self.number))
        # Title text
        c.setFillColor(NAVY)
        c.setFont('Helvetica-Bold', 13)
        c.drawString(34, self.height / 2 - 4, self.title)


class CoverBlock(Flowable):
    """Full-width cover page block."""
    def __init__(self, width=170*mm, height=260*mm):
        Flowable.__init__(self)
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        # Top accent bar
        c.setFillColor(BLUE)
        c.rect(0, self.height - 8, self.width, 8, fill=1, stroke=0)
        # Thin amber line
        c.setFillColor(AMBER)
        c.rect(0, self.height - 11, self.width, 3, fill=1, stroke=0)


class KeyMetricBox(Flowable):
    """Highlighted metric card for the summary table area."""
    def __init__(self, label, value, color=BLUE, width=50*mm, height=18*mm):
        Flowable.__init__(self)
        self.label = label
        self.value = value
        self.color = color
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        # Card background
        c.setFillColor(GRAY_100)
        c.roundRect(0, 0, self.width, self.height, 4, fill=1, stroke=0)
        # Top accent
        c.setFillColor(self.color)
        c.rect(0, self.height - 3, self.width, 3, fill=1, stroke=0)
        # Value
        c.setFillColor(NAVY)
        c.setFont('Helvetica-Bold', 16)
        c.drawCentredString(self.width / 2, self.height / 2, self.value)
        # Label
        c.setFillColor(GRAY_700)
        c.setFont('Helvetica', 7)
        c.drawCentredString(self.width / 2, 3, self.label)


class Footer(Flowable):
    """Page footer with logo and page number."""
    def __init__(self, page_num, width=170*mm, height=10*mm):
        Flowable.__init__(self)
        self.page_num = page_num
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        # Top line
        c.setStrokeColor(GRAY_300)
        c.setLineWidth(0.5)
        c.line(0, self.height, self.width, self.height)
        # Left: branding
        c.setFillColor(GRAY_500)
        c.setFont('Helvetica', 7)
        c.drawString(0, 3, 'NickelScope v3  |  ANTAM Hackathon 2026')
        # Right: page number
        c.setFillColor(GRAY_700)
        c.setFont('Helvetica', 7)
        c.drawRightString(self.width, 3, f'Page {self.page_num}')


# ══════════════════════════════════════════════════════════════
#  Styles
# ══════════════════════════════════════════════════════════════

def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle('CoverTitle', parent=ss['Title'], fontSize=32, textColor=NAVY,
                          spaceAfter=4, alignment=TA_LEFT, fontName='Helvetica-Bold',
                          leading=38))
    ss.add(ParagraphStyle('CoverSub', parent=ss['Normal'], fontSize=13, textColor=BLUE,
                          alignment=TA_LEFT, spaceAfter=2, fontName='Helvetica'))
    ss.add(ParagraphStyle('SectionTitle', parent=ss['Heading1'], fontSize=14, textColor=NAVY,
                          spaceBefore=10, spaceAfter=6, fontName='Helvetica-Bold'))
    ss.add(ParagraphStyle('SubTitle', parent=ss['Heading2'], fontSize=11, textColor=BLUE,
                          spaceBefore=6, spaceAfter=3, fontName='Helvetica-Bold'))
    ss.add(ParagraphStyle('Body', parent=ss['Normal'], fontSize=9.5, leading=13.5,
                          alignment=TA_JUSTIFY, spaceAfter=5, textColor=GRAY_900))
    ss.add(ParagraphStyle('BodySmall', parent=ss['Normal'], fontSize=8.5, leading=11,
                          alignment=TA_JUSTIFY, spaceAfter=4, textColor=GRAY_700))
    ss.add(ParagraphStyle('Caption', parent=ss['Normal'], fontSize=7.5, textColor=GRAY_500,
                          alignment=TA_CENTER, spaceAfter=6, fontName='Helvetica-Oblique'))
    ss.add(ParagraphStyle('Callout', parent=ss['Normal'], fontSize=9, leading=12,
                          textColor=RED, fontName='Helvetica-Bold', spaceAfter=4))
    ss.add(ParagraphStyle('MetricLabel', parent=ss['Normal'], fontSize=7.5, textColor=GRAY_500,
                          fontName='Helvetica'))
    ss.add(ParagraphStyle('MetricValue', parent=ss['Normal'], fontSize=14, textColor=NAVY,
                          fontName='Helvetica-Bold'))
    ss.add(ParagraphStyle('TableCell', parent=ss['Normal'], fontSize=8.5, leading=11,
                          textColor=GRAY_900))
    ss.add(ParagraphStyle('TableHeader', parent=ss['Normal'], fontSize=8.5, leading=11,
                          textColor=white, fontName='Helvetica-Bold'))
    ss.add(ParagraphStyle('SmallNote', parent=ss['Normal'], fontSize=7, textColor=GRAY_500,
                          fontName='Helvetica-Oblique'))
    return ss


# ══════════════════════════════════════════════════════════════
#  Chart Helpers
# ══════════════════════════════════════════════════════════════

def _fig_to_image(fig, width=16*cm, height=10*cm):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    return Image(buf, width=width, height=height)


def _to_hex(color):
    """Convert HexColor to '#rrggbb' string for matplotlib."""
    return f'#{color.red():02x}{color.green():02x}{color.blue():02x}'


def _style_ax(ax, title=None):
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color(_to_hex(GRAY_300))
    ax.spines['bottom'].set_color(_to_hex(GRAY_300))
    ax.tick_params(colors=_to_hex(GRAY_700), labelsize=8)
    ax.set_xlabel(ax.get_xlabel(), fontsize=9, color=_to_hex(GRAY_700), labelpad=8)
    ax.set_ylabel(ax.get_ylabel(), fontsize=9, color=_to_hex(GRAY_700), labelpad=8)
    if title:
        ax.set_title(title, fontsize=11, fontweight='bold', color=_to_hex(NAVY), pad=12)


def _make_heatmap(grid, b, n_g=80):
    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor('white')
    xi = np.linspace(b[0], b[2], n_g)
    yi = np.linspace(b[1], b[3], n_g)
    xi, yi = np.meshgrid(xi, yi)
    from scipy.interpolate import griddata
    zi = griddata(grid[['lon', 'lat']].values, grid['probability'].values, (xi, yi), method='cubic')
    zi = np.clip(np.nan_to_num(zi, nan=0), 0, 1)
    colors_list = ['#0D47A1', '#1565C0', '#42A5F5', '#80D8FF', '#E0F7FA', '#FFFF00',
                   '#FFD54F', '#FFC107', '#FF9800', '#F44336', '#B71C1C']
    cmap = LinearSegmentedColormap.from_list('ni', colors_list, N=256)
    c = ax.pcolormesh(xi, yi, zi, cmap=cmap, shading='gouraud', vmin=0, vmax=1)
    cb = plt.colorbar(c, ax=ax, shrink=0.8, aspect=20, pad=0.02)
    cb.set_label('Probability', fontsize=9, color=_to_hex(GRAY_700))
    cb.ax.tick_params(labelsize=8, colors=_to_hex(GRAY_700))
    _style_ax(ax, 'Nickel Prospectivity Heatmap')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.15, color=_to_hex(GRAY_500), linewidth=0.5)
    fig.tight_layout()
    return _fig_to_image(fig, width=16*cm, height=9.5*cm)


def _make_prob_chart(grid):
    fig, ax = plt.subplots(figsize=(6, 3.2))
    fig.patch.set_facecolor('white')
    bins = np.arange(0, 1.05, 0.1)
    counts = [int(((grid.probability >= bins[i]) & (grid.probability < bins[i + 1])).sum())
              for i in range(len(bins) - 1)]
    labels = [f'{bins[i]:.1f}' for i in range(len(bins) - 1)]
    colors = ['#1565C0', '#1976D2', '#1E88E5', '#2196F3', '#42A5F5',
              '#FFA726', '#FF9800', '#FB8C00', '#F57C00', '#EF6C00']
    bars = ax.bar(labels, counts, color=colors, edgecolor='white', linewidth=0.5, width=0.8)
    for bar, count in zip(bars, counts):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                    str(count), ha='center', va='bottom', fontsize=7, color=_to_hex(GRAY_700))
    _style_ax(ax, 'Probability Distribution')
    ax.set_xlabel('Probability')
    ax.set_ylabel('Sample Count')
    ax.grid(axis='y', alpha=0.15, color=_to_hex(GRAY_500), linewidth=0.5)
    fig.tight_layout()
    return _fig_to_image(fig, width=15*cm, height=7.5*cm)


def _make_rock_chart(grid):
    from nickelscope.geology import ROCK_COLORS
    fig, ax = plt.subplots(figsize=(5, 3.5))
    fig.patch.set_facecolor('white')
    vc = grid.rock_type.value_counts()
    colors = [ROCK_COLORS.get(k, '#999') for k in vc.index]
    wedges, texts, autotexts = ax.pie(
        vc.values, labels=vc.index, autopct='%1.1f%%',
        colors=colors, textprops={'fontsize': 8, 'color': _to_hex(GRAY_900)},
        pctdistance=0.75, startangle=90,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5}
    )
    for t in autotexts:
        t.set_fontsize(7)
        t.set_fontweight('bold')
        t.set_color('white')
    ax.set_title('Rock Type Distribution', fontsize=11, fontweight='bold',
                 color=_to_hex(NAVY), pad=10)
    fig.tight_layout()
    return _fig_to_image(fig, width=13*cm, height=8*cm)


def _make_uncertainty_chart(grid):
    fig, ax = plt.subplots(figsize=(6, 3.2))
    fig.patch.set_facecolor('white')
    u = grid.uncertainty.values
    bins = np.linspace(0, max(u.max(), 0.01), 11)
    counts = [int(((u >= bins[i]) & (u < bins[i + 1])).sum()) for i in range(len(bins) - 1)]
    labels = [f'{bins[i]:.2f}' for i in range(len(bins) - 1)]
    colors = ['#7B1FA2' if float(l) <= 0.15 else '#E91E63' for l in labels]
    bars = ax.bar(labels, counts, color=colors, edgecolor='white', linewidth=0.5, width=0.8)
    for bar, count in zip(bars, counts):
        if count > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                    str(count), ha='center', va='bottom', fontsize=7, color=_to_hex(GRAY_700))
    _style_ax(ax, 'Uncertainty Distribution')
    ax.set_xlabel('Uncertainty (std)')
    ax.set_ylabel('Sample Count')
    ax.grid(axis='y', alpha=0.15, color=_to_hex(GRAY_500), linewidth=0.5)
    fig.tight_layout()
    return _fig_to_image(fig, width=15*cm, height=7.5*cm)


# ══════════════════════════════════════════════════════════════
#  Table Builders
# ══════════════════════════════════════════════════════════════

def _build_summary_table(grid, b, styles):
    area_km = (b[2] - b[0]) * 111 * abs(np.cos(np.radians(b[1]))) * (b[3] - b[1]) * 111
    mean_p = grid.probability.mean()
    max_p = grid.probability.max()
    n_high = int((grid.probability >= 0.5).sum())
    n_total = len(grid)
    mean_u = grid.uncertainty.mean() if 'uncertainty' in grid.columns else 0

    rows = [
        [Paragraph('Parameter', styles['TableHeader']),
         Paragraph('Value', styles['TableHeader'])],
        [Paragraph('Study Area', styles['TableCell']),
         Paragraph(f'{area_km:.1f} km\u00B2', styles['TableCell'])],
        [Paragraph('Coordinates', styles['TableCell']),
         Paragraph(f'({b[0]:.4f}, {b[1]:.4f}) to ({b[2]:.4f}, {b[3]:.4f})', styles['TableCell'])],
        [Paragraph('Total Sample Points', styles['TableCell']),
         Paragraph(f'{n_total}', styles['TableCell'])],
        [Paragraph('Mean Probability', styles['TableCell']),
         Paragraph(f'{mean_p:.3f}', styles['TableCell'])],
        [Paragraph('Max Probability', styles['TableCell']),
         Paragraph(f'{max_p:.3f}', styles['TableCell'])],
        [Paragraph('High-Risk Points (\u22650.5)', styles['TableCell']),
         Paragraph(f'{n_high} ({n_high/n_total*100:.1f}%)', styles['TableCell'])],
        [Paragraph('Mean Uncertainty', styles['TableCell']),
         Paragraph(f'{mean_u:.3f}', styles['TableCell'])],
    ]

    if 'rock_type' in grid.columns:
        rock_dist = grid.rock_type.value_counts()
        for rock, count in rock_dist.items():
            rows.append([Paragraph(f'Rock: {rock}', styles['TableCell']),
                         Paragraph(f'{count} ({count/n_total*100:.1f}%)', styles['TableCell'])])

    t = Table(rows, colWidths=[8*cm, 8*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.4, GRAY_300),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, GRAY_100]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('ROUNDEDCORNERS', [3, 3, 3, 3]),
    ]))
    return t


def _build_rock_table(grid, styles):
    from nickelscope.geology import ROCK_COLORS
    rock_counts = grid.rock_type.value_counts()
    rows = [
        [Paragraph('Rock Type', styles['TableHeader']),
         Paragraph('Count', styles['TableHeader']),
         Paragraph('Percentage', styles['TableHeader']),
         Paragraph('Prospectivity', styles['TableHeader'])],
    ]
    for rock, count in rock_counts.items():
        pct = count / len(grid) * 100
        if rock == 'ULTRAMAFIC':
            prospect = 'PRIMARY HOST'
        elif rock == 'MAFIC':
            prospect = 'Secondary Host'
        elif rock in ('FELSIC', 'SEDIMENTARY'):
            prospect = 'Not Prospective'
        else:
            prospect = 'Variable'
        rows.append([
            Paragraph(f'<font color="{ROCK_COLORS.get(rock, "#999")}">\u25CF</font>  {rock}', styles['TableCell']),
            Paragraph(str(count), styles['TableCell']),
            Paragraph(f'{pct:.1f}%', styles['TableCell']),
            Paragraph(prospect, styles['TableCell']),
        ])

    t = Table(rows, colWidths=[5*cm, 2.5*cm, 3*cm, 4*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.4, GRAY_300),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, GRAY_100]),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


# ══════════════════════════════════════════════════════════════
#  AI Interpretation
# ══════════════════════════════════════════════════════════════

def _clean_ai_text(text):
    text = re.sub(r'\|[^\n]*\|', '', text)
    text = re.sub(r'\|[-:]+\|', '', text)
    text = re.sub(r'^\s*\|', '', text, flags=re.MULTILINE)
    text = re.sub(r'\|\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*[-*]\s+', '- ', text, flags=re.MULTILINE)
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    text = re.sub(r'`([^`]+)`', r'\1', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _generate_ai_interpretation(grid, b, geo_loaded):
    try:
        from nickelscope.chat import _get_client, _get_model_name
        client = _get_client()
        if not client:
            return _template_interpretation(grid, b, geo_loaded)

        area_km = (b[2] - b[0]) * 111 * abs(np.cos(np.radians(b[1]))) * (b[3] - b[1]) * 111
        mean_p = grid.probability.mean()
        max_p = grid.probability.max()
        n_high = int((grid.probability >= 0.5).sum())
        n_total = len(grid)
        mean_u = grid.uncertainty.mean()

        rock_info = ""
        if 'rock_type' in grid.columns:
            rock_dist = grid.rock_type.value_counts().to_dict()
            rock_info = f"Rock type distribution: {rock_dist}"

        if geo_loaded:
            province_list = ', '.join(sorted(geo_loaded))
            location_block = f"""LOCATION DATA:
Country: Indonesia
Geological provinces: {province_list}
Bounding box: ({b[0]:.4f}, {b[1]:.4f}) to ({b[2]:.4f}, {b[3]:.4f})
Center: ({(b[0]+b[2])/2:.4f}, {(b[1]+b[3])/2:.4f})"""
        else:
            location_block = f"""LOCATION DATA:
Country: Indonesia
Bounding box: ({b[0]:.4f}, {b[1]:.4f}) to ({b[2]:.4f}, {b[3]:.4f})
Center: ({(b[0]+b[2])/2:.4f}, {(b[1]+b[3])/2:.4f})"""

        prompt = f"""You are a senior economic geologist specializing in Indonesian nickel laterite deposits.

=== STUDY AREA DATA ===
{location_block}

Area: {area_km:.1f} km2
Mean prospectivity probability: {mean_p:.3f}
Max prospectivity probability: {max_p:.3f}
High-probability cells (>0.5): {n_high} of {n_total} ({n_high/n_total*100:.1f}%)
Mean uncertainty: {mean_u:.3f}
{rock_info}

=== YOUR TASK ===
Using the location data above, determine the exact geographic region of this study area.
The geological province names tell you exactly where this is in Indonesia.
Use your knowledge of Indonesian geology to describe the specific geological setting of that region.

Write a professional report with these sections:

Section A: GEOLOGICAL ASSESSMENT
Identify the region from the province names above. Describe its geological setting, particularly ultramafic rocks and ophiolite complexes relevant to nickel laterite mineralization. Discuss lateritization processes specific to that region.

Section B: PROSPECTIVITY INTERPRETATION
Interpret the probability values in the context of nickel exploration potential.

Section C: RISK AND UNCERTAINTY
Discuss data limitations and uncertainty implications.

Section D: RECOMMENDATIONS
List 4-5 specific exploration recommendations.

Use plain text only (NO tables, NO markdown pipes, NO special symbols). Bold labels only. 800-1000 words total."""

        response = client.chat.completions.create(
            model=_get_model_name(),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=16384, 
        )
        return _clean_ai_text(response.choices[0].message.content)
    except Exception:
        return _template_interpretation(grid, b, geo_loaded)


def _template_interpretation(grid, b, geo_loaded):
    area_km = (b[2] - b[0]) * 111 * abs(np.cos(np.radians(b[1]))) * (b[3] - b[1]) * 111
    mean_p = grid.probability.mean()
    max_p = grid.probability.max()
    n_high = int((grid.probability >= 0.5).sum())
    n_total = len(grid)
    pct = n_high / n_total * 100

    if mean_p >= 0.7:
        level = "HIGH"
        desc = "The analyzed area shows strong indicators of nickel laterite prospectivity."
    elif mean_p >= 0.5:
        level = "MODERATE"
        desc = "The area shows moderate indicators that warrant further investigation."
    elif mean_p >= 0.3:
        level = "LOW"
        desc = "The area shows limited indicators for nickel laterite deposits."
    else:
        level = "VERY LOW"
        desc = "The area shows minimal indicators for economic nickel laterite deposits."

    text = f"""<b>Geological Assessment</b>

{desc} The analysis covers {area_km:.1f} km\u00B2 of terrain with a mean prospectivity probability of {mean_p:.3f}.

<b>Prospectivity Interpretation</b>

Overall prospectivity level: <b>{level}</b>. Of {n_total} sample points analyzed, {n_high} ({pct:.1f}%) show probability \u2265 0.5, indicating potential nickel laterite mineralization. The maximum probability recorded is {max_p:.3f}.

<b>Risk and Uncertainty</b>"""

    mean_u = grid.uncertainty.mean()
    if mean_u > 0.15:
        text += f"""\n\nThe mean uncertainty of {mean_u:.3f} is relatively high, suggesting mixed geological units or transition zones within the study area. This may affect the reliability of prospectivity estimates and should be considered in exploration planning."""

    text += f"""\n\n<b>Recommendations</b>

1. Prioritize areas with probability \u2265 0.7 for detailed ground investigation
2. Conduct field mapping to verify rock types and weathering profiles
3. Collect soil and rock samples for geochemical analysis
4. Consider geophysical surveys to confirm subsurface geology"""

    if geo_loaded:
        text += f"\n5. Further analyze the loaded geological formations from {', '.join(list(geo_loaded)[:3])}"

    return text


# ══════════════════════════════════════════════════════════════
#  Page Builders
# ══════════════════════════════════════════════════════════════

def _page_cover(story, b, geo_loaded, styles):
    area_km = (b[2] - b[0]) * 111 * abs(np.cos(np.radians(b[1]))) * (b[3] - b[1]) * 111

    story.append(CoverBlock())
    story.append(Spacer(1, -240*mm))

    story.append(Paragraph('NickelScope', styles['CoverTitle']))
    story.append(Paragraph('v3', ParagraphStyle('CoverVer', parent=styles['CoverTitle'],
                                                fontSize=20, textColor=BLUE, spaceAfter=8)))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width='35%', thickness=2, color=AMBER))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph('Nickel Laterite Prospectivity', styles['CoverSub']))
    story.append(Paragraph('Analysis Report', styles['CoverSub']))
    story.append(Spacer(1, 1.5*cm))

    # Info card
    info_data = [
        ['Study Area', f'{area_km:.1f} km\u00B2'],
        ['Coordinates', f'({b[0]:.4f}, {b[1]:.4f}) to ({b[2]:.4f}, {b[3]:.4f})'],
        ['Model', 'Random Forest (400 trees)'],
        ['Features', '8 spectral + terrain indices'],
        ['Generated', datetime.now().strftime('%B %d, %Y')],
    ]
    if geo_loaded:
        info_data.append(['Geology', ', '.join(list(geo_loaded)[:3])])

    info_table = Table(info_data, colWidths=[3.5*cm, 10*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY_500),
        ('TEXTCOLOR', (1, 0), (1, -1), GRAY_900),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, -2), 0.3, GRAY_300),
    ]))
    story.append(info_table)

    story.append(Spacer(1, 4*cm))
    story.append(Paragraph('ANTAM Hackathon 2026', ParagraphStyle(
        'Hackathon', parent=styles['CoverSub'], fontSize=11, textColor=AMBER,
        fontName='Helvetica-Bold')))
    story.append(Paragraph('AI-GIS Nickel Laterite Prospectivity Tool', styles['SmallNote']))
    story.append(PageBreak())


def _page_aoi(story, grid, b, geo_loaded, styles):
    area_km = (b[2] - b[0]) * 111 * abs(np.cos(np.radians(b[1]))) * (b[3] - b[1]) * 111
    lat_center = (b[1] + b[3]) / 2
    lon_center = (b[0] + b[2]) / 2
    lat_span = b[3] - b[1]
    lon_span = b[2] - b[0]

    story.append(SectionHeader(1, 'Area of Interest (AOI) Overview'))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph(
        f'The study area covers <b>{area_km:.1f} km\u00B2</b> of terrain in the Indonesian archipelago, '
        f'centered at <b>{lat_center:.4f}\u00B0S, {lon_center:.4f}\u00B0E</b>. '
        f'The rectangular analysis window spans <b>{lon_span:.4f}\u00B0</b> in longitude '
        f'({b[0]:.4f}\u00B0 to {b[2]:.4f}\u00B0) and <b>{lat_span:.4f}\u00B0</b> in latitude '
        f'({b[1]:.4f}\u00B0 to {b[3]:.4f}\u00B0).',
        styles['Body']
    ))
    story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph(
        '<b>Data Sources:</b> The analysis integrates multi-source remote sensing and geospatial data: '
        '(1) Sentinel-2 Level-2A surface reflectance imagery for spectral index computation, '
        '(2) SRTM 30m digital elevation model for terrain derivatives, and '
        '(3) MERIT Hydro dataset for topographic wetness index. '
        'A grid of sample points was generated across the AOI and processed through a Random Forest classifier '
        'trained on known nickel laterite occurrences.',
        styles['Body']
    ))
    story.append(Spacer(1, 0.2*cm))

    if geo_loaded:
        story.append(Paragraph(
            f'<b>Geological Context:</b> Geology overlay data was loaded for provinces: '
            f'<b>{", ".join(list(geo_loaded)[:5])}</b>. '
            f'Rock formations were classified into lithological categories to assess their '
            f'potential as nickel laterite host rocks.',
            styles['Body']
        ))
        story.append(Spacer(1, 0.2*cm))

    story.append(Paragraph(
        '<b>Methodology:</b> The prospectivity mapping workflow involves: (a) extraction of 8 spectral and '
        'terrain features at each grid point, (b) classification of geological units from shapefile data, '
        '(c) prediction of nickel laterite probability using a trained Random Forest model with 400 decision trees, '
        'and (d) uncertainty estimation based on prediction variance across individual trees.',
        styles['Body']
    ))
    story.append(Spacer(1, 0.4*cm))
    story.append(_make_heatmap(grid, b))
    story.append(Paragraph(
        'Figure 1: Nickel prospectivity heatmap. Red indicates high probability zones; '
        'blue indicates low prospectivity areas.',
        styles['Caption']
    ))
    story.append(PageBreak())


def _page_prospectivity(story, grid, b, styles):
    story.append(SectionHeader(2, 'Prospectivity Analysis'))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph(
        f'The machine learning model analyzed <b>{len(grid)} sample points</b> across the study area. '
        f'The probability distribution below shows the likelihood of nickel laterite mineralization '
        f'at each point.',
        styles['Body']
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(_make_prob_chart(grid))
    story.append(Paragraph(
        'Figure 2: Distribution of prospectivity probabilities across sample points.',
        styles['Caption']
    ))
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph('Summary Statistics', styles['SubTitle']))
    story.append(_build_summary_table(grid, b, styles))
    story.append(PageBreak())


def _page_geology(story, grid, b, styles):
    story.append(SectionHeader(3, 'Geological Analysis'))
    story.append(Spacer(1, 0.5*cm))

    if 'rock_type' in grid.columns:
        rock_counts = grid.rock_type.value_counts()
        dominant_rock = rock_counts.index[0]
        dominant_pct = rock_counts.iloc[0] / len(grid) * 100
        n_ultra = rock_counts.get('ULTRAMAFIC', 0)
        n_mafic = rock_counts.get('MAFIC', 0)

        story.append(Paragraph(
            'The geological context was assessed using the Indonesia Geological Survey '
            'shapefile database. Each sample point was classified based on the dominant '
            'lithological unit at its location.',
            styles['Body']
        ))
        story.append(Spacer(1, 0.2*cm))

        story.append(Paragraph(
            f'The dominant lithology is <b>{dominant_rock}</b> (<b>{dominant_pct:.1f}%</b>). '
            f'Ultramafic rocks (serpentinite, peridotite, dunite) are the primary host rocks for nickel laterite '
            f'deposits, containing elevated Ni, Co, and Cr that concentrate during tropical weathering. '
            f'Mafic rocks (basalt, gabbro) serve as secondary hosts.',
            styles['Body']
        ))
        story.append(Spacer(1, 0.3*cm))

        story.append(_make_rock_chart(grid))
        story.append(Paragraph(
            'Figure 3: Rock type distribution. Ultramafic and mafic rocks have the highest prospectivity.',
            styles['Caption']
        ))
        story.append(Spacer(1, 0.4*cm))

        story.append(_build_rock_table(grid, styles))
        story.append(Spacer(1, 0.4*cm))

        story.append(Paragraph(
            f'<b>Exploration Significance:</b> A total of <b>{n_ultra + n_mafic}</b> points '
            f'({(n_ultra + n_mafic)/len(grid)*100:.1f}%) are located on ultramafic or mafic lithologies. '
            f'Of these, {n_ultra} ({n_ultra/len(grid)*100:.1f}%) are on ultramafic units, '
            f'representing the primary exploration targets.',
            styles['Body']
        ))
    else:
        story.append(Paragraph('Geological data not available for this area.', styles['Body']))

    story.append(PageBreak())


def _page_uncertainty(story, grid, styles):
    story.append(SectionHeader(4, 'Uncertainty Analysis'))
    story.append(Spacer(1, 0.5*cm))

    mean_u = grid.uncertainty.mean()
    max_u = grid.uncertainty.max()
    std_u = grid.uncertainty.std()

    story.append(Paragraph(
        'Model uncertainty was estimated as the standard deviation of probability predictions across '
        '400 individual decision trees in the Random Forest ensemble. This metric quantifies the model\'s '
        'confidence in its predictions at each sample point.',
        styles['Body']
    ))
    story.append(Spacer(1, 0.3*cm))

    # Key metrics boxes
    metric_data = [[
        KeyMetricBox('MEAN UNCERTAINTY', f'{mean_u:.3f}', BLUE),
        KeyMetricBox('STD DEVIATION', f'{std_u:.3f}', TEAL),
        KeyMetricBox('MAX UNCERTAINTY', f'{max_u:.3f}', AMBER),
    ]]
    metric_table = Table(metric_data, colWidths=[5.5*cm, 5.5*cm, 5.5*cm])
    metric_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(metric_table)
    story.append(Spacer(1, 0.4*cm))

    if mean_u > 0.15:
        story.append(Paragraph(
            '<b>Note:</b> The relatively high mean uncertainty (>0.15) suggests that the study area '
            'contains mixed geological units or transition zones between different lithologies. '
            'This may indicate: (1) areas with complex geological contacts, '
            '(2) regions with limited ground-truth data, or '
            '(3) areas where sedimentary cover obscures underlying bedrock. '
            'Field verification is strongly recommended for high-probability, high-uncertainty zones.',
            styles['Callout']
        ))
    else:
        story.append(Paragraph(
            '<b>Note:</b> The relatively low mean uncertainty indicates that the model is generally '
            'confident in its predictions across the study area. This suggests consistent geological '
            'signals and adequate training data coverage.',
            styles['Body']
        ))

    story.append(Spacer(1, 0.3*cm))
    story.append(_make_uncertainty_chart(grid))
    story.append(Paragraph(
        'Figure 4: Uncertainty distribution. Purple bars indicate low uncertainty (reliable); '
        'pink bars indicate high uncertainty (needs field verification).',
        styles['Caption']
    ))
    story.append(Spacer(1, 0.4*cm))

    n_high_u = int((grid.uncertainty > 0.15).sum())
    story.append(Paragraph(
        f'<b>Uncertainty Classification:</b> Of {len(grid)} sample points, <b>{n_high_u}</b> '
        f'({n_high_u/len(grid)*100:.1f}%) have uncertainty > 0.15, indicating areas where predictions '
        f'may be less reliable. These points should be prioritized for field verification.',
        styles['Body']
    ))
    story.append(PageBreak())


def _page_ai(story, grid, b, geo_loaded, styles):
    story.append(SectionHeader(5, 'AI Interpretation & Recommendations'))
    story.append(Spacer(1, 0.5*cm))

    interpretation = _generate_ai_interpretation(grid, b, geo_loaded)
    for para in interpretation.split('\n\n'):
        para = para.strip()
        if para:
            story.append(Paragraph(para, styles['Body']))
            story.append(Spacer(1, 0.2*cm))

    story.append(Spacer(1, 1.5*cm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=GRAY_300))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        'This report was automatically generated by NickelScope v3 \u2014 AI-GIS Nickel Laterite '
        'Prospectivity Tool. Results should be validated with field investigation.',
        styles['SmallNote']
    ))


# ══════════════════════════════════════════════════════════════
#  Main Generator
# ══════════════════════════════════════════════════════════════

def generate_report(grid, b, geo_loaded=None, output_path=None):
    if geo_loaded is None:
        geo_loaded = set()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = _styles()
    story = []

    _page_cover(story, b, geo_loaded, styles)
    _page_aoi(story, grid, b, geo_loaded, styles)
    _page_prospectivity(story, grid, b, styles)
    _page_geology(story, grid, b, styles)
    _page_uncertainty(story, grid, styles)
    _page_ai(story, grid, b, geo_loaded, styles)

    # Build with page numbers
    page_num = [0]
    def on_page(canvas, doc):
        page_num[0] += 1
        canvas.saveState()
        footer = Footer(page_num[0])
        footer.drawOn(canvas, doc.leftMargin, 0.8*cm)
        canvas.restoreState()

    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    buf.seek(0)
    return buf.getvalue()
