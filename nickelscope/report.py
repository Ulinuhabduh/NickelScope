"""NickelScope PDF Report Generator — Multi-page professional report."""
import io, os
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.backends.backend_agg import FigureCanvasAgg
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
    PageBreak, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable

W, H = A4
PRIMARY = HexColor('#1565C0')
PRIMARY_DARK = HexColor('#0D47A1')
LIGHT_BG = HexColor('#F5F7FA')
ACCENT = HexColor('#FF9800')


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle('CoverTitle', parent=ss['Title'], fontSize=28, textColor=PRIMARY_DARK,
                          spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Bold'))
    ss.add(ParagraphStyle('CoverSub', parent=ss['Normal'], fontSize=14, textColor=PRIMARY,
                          alignment=TA_CENTER, spaceAfter=4))
    ss.add(ParagraphStyle('SectionTitle', parent=ss['Heading1'], fontSize=16, textColor=PRIMARY_DARK,
                          spaceBefore=12, spaceAfter=8, fontName='Helvetica-Bold'))
    ss.add(ParagraphStyle('SubTitle', parent=ss['Heading2'], fontSize=12, textColor=PRIMARY,
                          spaceBefore=8, spaceAfter=4, fontName='Helvetica-Bold'))
    ss.add(ParagraphStyle('BodyText2', parent=ss['Normal'], fontSize=10, leading=14,
                          alignment=TA_JUSTIFY, spaceAfter=6))
    ss.add(ParagraphStyle('SmallText', parent=ss['Normal'], fontSize=8, textColor=HexColor('#666666')))
    ss.add(ParagraphStyle('Highlight', parent=ss['Normal'], fontSize=10, textColor=HexColor('#C62828'),
                          fontName='Helvetica-Bold'))
    return ss


def _fig_to_image(fig, width=16*cm, height=10*cm):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    buf.seek(0)
    img = Image(buf, width=width, height=height)
    return img


def _make_heatmap(grid, b, n_g=80):
    fig, ax = plt.subplots(figsize=(8, 5))
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
    plt.colorbar(c, ax=ax, label='Probability', shrink=0.8)
    ax.set_title('Nickel Prospectivity Heatmap', fontsize=12, fontweight='bold')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_aspect('equal')
    fig.tight_layout()
    return _fig_to_image(fig, width=16*cm, height=10*cm)


def _make_prob_chart(grid):
    fig, ax = plt.subplots(figsize=(6, 3.5))
    bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    counts = [int(((grid.probability >= bins[i]) & (grid.probability < bins[i + 1])).sum())
              for i in range(len(bins) - 1)]
    labels = [f'{bins[i]:.1f}' for i in range(len(bins) - 1)]
    colors = ['#1565C0', '#1976D2', '#1E88E5', '#2196F3', '#42A5F5',
              '#FFA726', '#FF9800', '#FB8C00', '#F57C00', '#EF6C00']
    ax.bar(labels, counts, color=colors)
    ax.set_title('Probability Distribution', fontsize=11, fontweight='bold')
    ax.set_xlabel('Probability')
    ax.set_ylabel('Sample Count')
    ax.tick_params(labelsize=8)
    fig.tight_layout()
    return _fig_to_image(fig, width=14*cm, height=8*cm)


def _make_rock_chart(grid):
    from nickelscope.geology import ROCK_COLORS
    fig, ax = plt.subplots(figsize=(6, 3.5))
    vc = grid.rock_type.value_counts()
    colors = [ROCK_COLORS.get(k, '#999') for k in vc.index]
    wedges, texts, autotexts = ax.pie(vc.values, labels=vc.index, autopct='%1.1f%%',
                                       colors=colors, textprops={'fontsize': 8})
    for t in autotexts:
        t.set_fontsize(7)
    ax.set_title('Rock Type Distribution', fontsize=11, fontweight='bold')
    fig.tight_layout()
    return _fig_to_image(fig, width=14*cm, height=8*cm)


def _make_uncertainty_chart(grid):
    fig, ax = plt.subplots(figsize=(6, 3.5))
    u = grid.uncertainty.values
    bins = np.linspace(0, max(u.max(), 0.01), 11)
    counts = [int(((u >= bins[i]) & (u < bins[i + 1])).sum()) for i in range(len(bins) - 1)]
    labels = [f'{bins[i]:.2f}' for i in range(len(bins) - 1)]
    ax.bar(labels, counts, color='#7B1FA2')
    ax.set_title('Uncertainty Distribution', fontsize=11, fontweight='bold')
    ax.set_xlabel('Uncertainty (std)')
    ax.set_ylabel('Sample Count')
    ax.tick_params(labelsize=7, rotation=45)
    fig.tight_layout()
    return _fig_to_image(fig, width=14*cm, height=8*cm)


def _build_summary_table(grid, b):
    area_km = (b[2] - b[0]) * 111 * abs(np.cos(np.radians(b[1]))) * (b[3] - b[1]) * 111
    mean_p = grid.probability.mean()
    max_p = grid.probability.max()
    n_high = int((grid.probability >= 0.5).sum())
    n_total = len(grid)
    mean_u = grid.uncertainty.mean() if 'uncertainty' in grid.columns else 0

    data = [
        ['Parameter', 'Value'],
        ['Area', f'{area_km:.1f} km\u00B2'],
        ['Coordinates', f'({b[0]:.4f}, {b[1]:.4f}) to ({b[2]:.4f}, {b[3]:.4f})'],
        ['Total Sample Points', str(n_total)],
        ['Mean Probability', f'{mean_p:.3f}'],
        ['Max Probability', f'{max_p:.3f}'],
        ['High-Risk Points (\u22650.5)', str(n_high)],
        ['High-Risk Percentage', f'{n_high/n_total*100:.1f}%'],
        ['Mean Uncertainty', f'{mean_u:.3f}'],
    ]

    if 'rock_type' in grid.columns:
        rock_dist = grid.rock_type.value_counts()
        for rock, count in rock_dist.items():
            data.append([f'Rock: {rock}', f'{count} ({count/n_total*100:.1f}%)'])

    t = Table(data, colWidths=[8*cm, 8*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CCCCCC')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    return t


def _clean_ai_text(text):
    """Clean AI-generated text for PDF rendering with ReportLab."""
    import re
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
    """Generate AI interpretation using Groq."""
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
            location_block = f"""LOCATION DATA (use these to identify the region):
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
            max_tokens=4096,
        )
        return _clean_ai_text(response.choices[0].message.content)
    except Exception:
        return _template_interpretation(grid, b, geo_loaded)


def _template_interpretation(grid, b, geo_loaded):
    """Fallback template-based interpretation."""
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

<b>Risk and Uncertainty</b"""

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


def generate_report(grid, b, geo_loaded=None, output_path=None):
    """Generate multi-page PDF report."""
    if geo_loaded is None:
        geo_loaded = set()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    styles = _styles()
    story = []

    # ═══ PAGE 1: COVER ═══
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph('NickelScope v3', styles['CoverTitle']))
    story.append(Paragraph('Nickel Laterite Prospectivity Analysis Report', styles['CoverSub']))
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width='80%', thickness=2, color=PRIMARY))
    story.append(Spacer(1, 1*cm))

    area_km = (b[2] - b[0]) * 111 * abs(np.cos(np.radians(b[1]))) * (b[3] - b[1]) * 111
    cover_data = [
        ['Study Area', f'{area_km:.1f} km\u00B2'],
        ['Coordinates', f'({b[0]:.4f}, {b[1]:.4f}) to ({b[2]:.4f}, {b[3]:.4f})'],
        ['Generated', datetime.now().strftime('%B %d, %Y %H:%M')],
        ['Model', 'Random Forest (400 trees)'],
        ['Features', '8 spectral + terrain indices'],
    ]
    if geo_loaded:
        cover_data.append(['Geology', ', '.join(list(geo_loaded)[:3])])

    t = Table(cover_data, colWidths=[5*cm, 11*cm])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('TEXTCOLOR', (0, 0), (0, -1), PRIMARY),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)

    story.append(Spacer(1, 3*cm))
    story.append(Paragraph('ANTAM Hackathon 2026', styles['CoverSub']))
    story.append(Paragraph('AI-GIS Nickel Laterite Prospectivity Tool', styles['SmallText']))
    story.append(PageBreak())

    # ═══ PAGE 2: AOI OVERVIEW ═══
    story.append(Paragraph('1. Area of Interest (AOI) Overview', styles['SectionTitle']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Spacer(1, 0.5*cm))

    lat_center = (b[1] + b[3]) / 2
    lon_center = (b[0] + b[2]) / 2
    lat_span = b[3] - b[1]
    lon_span = b[2] - b[0]

    story.append(Paragraph(
        f'The study area covers <b>{area_km:.1f} km\u00B2</b> of terrain located in the Indonesian archipelago, '
        f'centered at approximately <b>{lat_center:.4f}\u00B0N, {lon_center:.4f}\u00B0E</b>. '
        f'The rectangular analysis window spans <b>{lon_span:.4f}\u00B0</b> in longitude '
        f'({b[0]:.4f}\u00B0 to {b[2]:.4f}\u00B0) and <b>{lat_span:.4f}\u00B0</b> in latitude '
        f'({b[1]:.4f}\u00B0 to {b[3]:.4f}\u00B0).',
        styles['BodyText2']
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        '<b>Data Sources:</b> The analysis integrates multi-source remote sensing and geospatial data: '
        '(1) Sentinel-2 Level-2A surface reflectance imagery for spectral index computation, '
        '(2) SRTM 30m digital elevation model for terrain derivatives, and '
        '(3) MERIT Hydro dataset for topographic wetness index. '
        'A grid of sample points was generated across the AOI and processed through a Random Forest classifier '
        'trained on known nickel laterite occurrences.',
        styles['BodyText2']
    ))
    story.append(Spacer(1, 0.3*cm))

    if geo_loaded:
        story.append(Paragraph(
            f'<b>Geological Context:</b> Geology overlay data was loaded for the following provinces: '
            f'<b>{", ".join(list(geo_loaded)[:5])}</b>. '
            f'Rock formations were classified into lithological categories (ultramafic, mafic, felsic, '
            f'sedimentary, metamorphic, igneous) to assess their potential as nickel laterite host rocks.',
            styles['BodyText2']
        ))
        story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph(
        '<b>Methodology:</b> The prospectivity mapping workflow involves: (a) extraction of 8 spectral and '
        'terrain features at each grid point, (b) classification of geological units from shapefile data, '
        '(c) prediction of nickel laterite probability using a trained Random Forest model with 400 decision trees, '
        'and (d) uncertainty estimation based on prediction variance across individual trees.',
        styles['BodyText2']
    ))
    story.append(Spacer(1, 0.5*cm))
    story.append(_make_heatmap(grid, b))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph('<i>Figure 1: Nickel prospectivity heatmap of the study area. '
                           'Red colors indicate high probability zones. Blue indicates low prospectivity areas.</i>',
                           styles['SmallText']))
    story.append(PageBreak())

    # ═══ PAGE 3: PROSPECTIVITY ANALYSIS ═══
    story.append(Paragraph('2. Prospectivity Analysis', styles['SectionTitle']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph(
        f'The machine learning model analyzed <b>{len(grid)} sample points</b> across the study area. '
        f'The probability distribution shows the likelihood of nickel laterite mineralization at each point.',
        styles['BodyText2']
    ))
    story.append(Spacer(1, 0.3*cm))
    story.append(_make_prob_chart(grid))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph('<i>Figure 2: Distribution of prospectivity probabilities across sample points.</i>',
                           styles['SmallText']))
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph('<b>Summary Statistics</b>', styles['SubTitle']))
    story.append(_build_summary_table(grid, b))
    story.append(PageBreak())

    # ═══ PAGE 4: GEOLOGICAL ANALYSIS ═══
    story.append(Paragraph('3. Geological Analysis', styles['SectionTitle']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Spacer(1, 0.5*cm))

    if 'rock_type' in grid.columns:
        story.append(Paragraph(
            'The geological context of the study area was assessed using the Indonesia Geological Survey '
            'shapefile database covering 25 provinces. Each sample point was classified based on the dominant '
            'lithological unit at its location. Rock types were then grouped into six categories according to '
            'their relevance as nickel laterite host rocks.',
            styles['BodyText2']
        ))
        story.append(Spacer(1, 0.3*cm))

        rock_counts = grid.rock_type.value_counts()
        dominant_rock = rock_counts.index[0]
        dominant_pct = rock_counts.iloc[0] / len(grid) * 100

        story.append(Paragraph(
            f'The dominant lithology in the study area is <b>{dominant_rock}</b>, comprising '
            f'<b>{dominant_pct:.1f}%</b> of the analyzed points. '
            f'Ultramafic rocks (serpentinite, peridotite, dunite) are the primary host rocks for nickel laterite '
            f'deposits, as they contain elevated concentrations of nickel, cobalt, and chromium that become '
            f'concentrated during tropical weathering processes. Mafic rocks (basalt, gabbro) serve as secondary '
            f'hosts with generally lower nickel grades.',
            styles['BodyText2']
        ))
        story.append(Spacer(1, 0.3*cm))
        story.append(_make_rock_chart(grid))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph('<i>Figure 3: Distribution of rock types within the study area. '
                               'Ultramafic and mafic rocks have the highest prospectivity.</i>',
                               styles['SmallText']))
        story.append(Spacer(1, 0.5*cm))

        from nickelscope.geology import ROCK_COLORS
        rock_data = [['Rock Type', 'Count', 'Percentage', 'Prospectivity Rating']]
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
            rock_data.append([rock, str(count), f'{pct:.1f}%', prospect])

        t = Table(rock_data, colWidths=[4*cm, 3*cm, 3*cm, 4*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, HexColor('#CCCCCC')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.3*cm))

        n_ultra = rock_counts.get('ULTRAMAFIC', 0)
        n_mafic = rock_counts.get('MAFIC', 0)
        story.append(Paragraph(
            f'<b>Exploration Significance:</b> A total of <b>{n_ultra + n_mafic}</b> points '
            f'({(n_ultra + n_mafic)/len(grid)*100:.1f}%) are located on ultramafic or mafic lithologies, '
            f'which are the most favorable host rocks for nickel laterite mineralization. '
            f'Of these, {n_ultra} points ({n_ultra/len(grid)*100:.1f}%) are on ultramafic units, '
            f'representing the primary exploration targets.',
            styles['BodyText2']
        ))
    else:
        story.append(Paragraph('Geological data not available for this area.', styles['BodyText2']))
    story.append(PageBreak())

    # ═══ PAGE 5: UNCERTAINTY ANALYSIS ═══
    story.append(Paragraph('4. Uncertainty Analysis', styles['SectionTitle']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Spacer(1, 0.5*cm))
    mean_u = grid.uncertainty.mean()
    max_u = grid.uncertainty.max()
    std_u = grid.uncertainty.std()

    story.append(Paragraph(
        f'Model uncertainty was estimated as the standard deviation of probability predictions across '
        f'400 individual decision trees in the Random Forest ensemble. This metric quantifies the model\'s '
        f'confidence in its predictions at each sample point.',
        styles['BodyText2']
    ))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph(
        f'The mean uncertainty across all sample points is <b>{mean_u:.3f}</b>, with a standard deviation '
        f'of <b>{std_u:.3f}</b> and maximum value of <b>{max_u:.3f}</b>. '
        f'Low uncertainty values indicate areas where the model is confident in its prediction, while high '
        f'uncertainty suggests mixed geological signals or data gaps.',
        styles['BodyText2']
    ))
    story.append(Spacer(1, 0.3*cm))

    if mean_u > 0.15:
        story.append(Paragraph(
            '<b>Note:</b> The relatively high mean uncertainty (>0.15) suggests that the study area '
            'contains mixed geological units or transition zones between different lithologies. '
            'This may indicate: (1) areas with complex geological contacts, '
            '(2) regions with limited ground-truth data, or '
            '(3) areas where sedimentary cover obscures underlying bedrock. '
            'Field verification is strongly recommended for high-probability, high-uncertainty zones.',
            styles['Highlight']
        ))
    else:
        story.append(Paragraph(
            '<b>Note:</b> The relatively low mean uncertainty indicates that the model is generally '
            'confident in its predictions across the study area. This suggests consistent geological '
            'signals and adequate training data coverage.',
            styles['BodyText2']
        ))

    story.append(Spacer(1, 0.3*cm))
    story.append(_make_uncertainty_chart(grid))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph('<i>Figure 4: Distribution of model uncertainty across sample points. '
                           'Higher values indicate lower model confidence.</i>',
                           styles['SmallText']))
    story.append(Spacer(1, 0.5*cm))

    n_high_u = int((grid.uncertainty > 0.15).sum())
    story.append(Paragraph(
        f'<b>Uncertainty Classification:</b> Of {len(grid)} sample points, <b>{n_high_u}</b> '
        f'({n_high_u/len(grid)*100:.1f}%) have uncertainty > 0.15, indicating areas where predictions '
        f'may be less reliable. These points should be prioritized for field verification.',
        styles['BodyText2']
    ))
    story.append(PageBreak())

    # ═══ PAGE 6: RECOMMENDATIONS ═══
    story.append(Paragraph('5. AI Interpretation & Recommendations', styles['SectionTitle']))
    story.append(HRFlowable(width='100%', thickness=1, color=PRIMARY))
    story.append(Spacer(1, 0.5*cm))

    interpretation = _generate_ai_interpretation(grid, b, geo_loaded)
    for para in interpretation.split('\n\n'):
        para = para.strip()
        if para:
            story.append(Paragraph(para, styles['BodyText2']))
            story.append(Spacer(1, 0.3*cm))

    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width='100%', thickness=1, color=HexColor('#CCCCCC')))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        '<i>This report was automatically generated by NickelScope v3 — AI-GIS Nickel Laterite '
        'Prospectivity Tool. Results should be validated with field investigation.</i>',
        styles['SmallText']
    ))

    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
