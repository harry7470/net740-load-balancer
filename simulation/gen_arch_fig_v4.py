"""
Architecture figure v4 — light blue / navy / dark gray color scheme, larger readable text
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

fig, ax = plt.subplots(figsize=(14, 8))
ax.set_xlim(0, 14)
ax.set_ylim(0, 8)
ax.axis('off')

# ── Color scheme: light blue / navy / dark gray ───────────────────────────────
BG      = '#F0F4F8'   # very light blue-gray background
C_SRC   = '#1565C0'   # navy blue — legitimate source
C_ATK   = '#B71C1C'   # dark red — DDoS attacker
C_ING   = '#0D47A1'   # deep navy — ingress fog node
C_MON   = '#1976D2'   # medium blue — monitor
C_CTRL  = '#37474F'   # dark blue-gray — controller
C_FOG   = '#455A64'   # steel blue-gray — fog nodes
C_DEST  = '#263238'   # darkest gray — destination
C_ARROW = '#37474F'   # dark gray arrows

fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

plt.rcParams['font.family'] = 'DejaVu Sans'

def rbox(ax, cx, cy, w, h, color, edgecolor='#B0BEC5', zorder=3):
    r = FancyBboxPatch((cx - w/2, cy - h/2), w, h,
                       boxstyle="round,pad=0.10",
                       facecolor=color, edgecolor=edgecolor,
                       linewidth=2.0, zorder=zorder)
    ax.add_patch(r)

def label(ax, x, y, txt, fs=11, fw='bold', color='white', style='normal', zorder=5):
    ax.text(x, y, txt, ha='center', va='center',
            fontsize=fs, fontweight=fw, color=color,
            style=style, zorder=zorder)

def arrow(ax, x1, y1, x2, y2, color=C_ARROW, lw=2.2,
          txt=None, tx=None, ty=None):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw), zorder=2)
    if txt:
        ax.text(tx, ty, txt, ha='center', va='center', fontsize=9,
                color=color, fontweight='bold', zorder=5,
                bbox=dict(facecolor=BG, edgecolor='none', pad=2))

def darrow(ax, x1, y1, x2, y2, color=C_CTRL, lw=1.8,
           txt=None, tx=None, ty=None):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                linestyle='dashed'), zorder=2)
    if txt:
        ax.text(tx, ty, txt, ha='center', va='center', fontsize=9,
                color=color, fontweight='bold', zorder=5,
                bbox=dict(facecolor=BG, edgecolor='none', pad=2))

# ── Title ─────────────────────────────────────────────────────────────────────
ax.text(7, 7.65, 'AALB: Attack-Aware Adaptive Load Balancing — System Architecture',
        ha='center', va='center', fontsize=14, fontweight='bold', color='#0D47A1')

# ── Legitimate source ─────────────────────────────────────────────────────────
rbox(ax, 1.3, 5.5, 1.75, 0.80, C_SRC)
label(ax, 1.3, 5.67, 'Legitimate', fs=11)
label(ax, 1.3, 5.32, 'Traffic Source', fs=9.5, fw='normal', style='italic')

# ── DDoS source ───────────────────────────────────────────────────────────────
rbox(ax, 1.3, 2.8, 1.75, 0.80, C_ATK)
label(ax, 1.3, 2.97, 'DDoS', fs=11)
label(ax, 1.3, 2.62, 'Attack Source', fs=9.5, fw='normal', style='italic')

# ── Ingress Fog Node ──────────────────────────────────────────────────────────
ING_CX, ING_CY, ING_W, ING_H = 4.2, 4.15, 2.65, 3.65
rbox(ax, ING_CX, ING_CY, ING_W, ING_H, C_ING, edgecolor='#90CAF9')

# Header
label(ax, ING_CX, ING_CY + ING_H/2 - 0.28, 'Ingress Fog Node', fs=12)

# Active profile header
label(ax, ING_CX, 4.90, 'Active Profile:', fs=10, fw='bold', color='#90CAF9')

# K0/K1/K2 rows
kx_lbl  = ING_CX - 1.1
kx_desc = ING_CX - 0.52
for ky, klbl, kdesc in [
    (4.50, 'K0:', 'LB only  (low η)'),
    (4.05, 'K1:', 'RF → LB  (moderate η)'),
    (3.60, 'K2:', 'FW → RF → LB  (high η)'),
]:
    ax.text(kx_lbl,  ky, klbl,  ha='left', va='center',
            fontsize=10.5, fontweight='bold', color='#E3F2FD', zorder=5)
    ax.text(kx_desc, ky, kdesc, ha='left', va='center',
            fontsize=9.5, color='#BBDEFB', zorder=5, style='italic')

# Separator line
ax.plot([ING_CX - 1.1, ING_CX + 1.1], [3.28, 3.28],
        color='#90CAF9', lw=1.0, linestyle='--', zorder=5, alpha=0.7)

# Monitor sub-box
MON_CX, MON_CY = ING_CX, 2.85
rbox(ax, MON_CX, MON_CY, 1.95, 0.75, C_MON, edgecolor='#90CAF9', zorder=4)
label(ax, MON_CX, MON_CY + 0.15, 'Monitor', fs=10.5)
label(ax, MON_CX, MON_CY - 0.18, 'η(t) estimator', fs=9, fw='normal', style='italic')

# Admission constraint note
ax.text(ING_CX, ING_CY - ING_H/2 - 0.30,
        'Admission: admit iff D ≤ 20 ms and resources available',
        ha='center', va='center', fontsize=9, color='#0D47A1', fontweight='bold',
        bbox=dict(facecolor='#E3F2FD', edgecolor='#1565C0', pad=5, boxstyle='round,pad=0.3',
                  linewidth=1.5))

# ── Controller ────────────────────────────────────────────────────────────────
rbox(ax, 7.0, 7.0, 2.65, 0.82, C_CTRL, edgecolor='#90A4AE')
label(ax, 7.0, 7.14, 'AALB Controller', fs=12)
label(ax, 7.0, 6.83, 'Profile selector + hysteresis', fs=9, fw='normal', style='italic')

# ── VNF Fog nodes ─────────────────────────────────────────────────────────────
fog_data = [
    (8.8, 5.6, 'Fog Node (FW-VNF)', 'Attack Filter'),
    (8.8, 4.1, 'Fog Node (RF-VNF)', 'Rate Limiter'),
    (8.8, 2.6, 'Fog Node (LB-VNF)', 'Load Balancer'),
]
for fx, fy, fl, fs_ in fog_data:
    rbox(ax, fx, fy, 2.15, 0.90, C_FOG, edgecolor='#90A4AE')
    label(ax, fx, fy + 0.19, fl, fs=10)
    label(ax, fx, fy - 0.21, fs_, fs=9, fw='normal', style='italic', color='#CFD8DC')

# SFC chain links
for (_, y1, _, _), (_, y2, _, _) in zip(fog_data[:-1], fog_data[1:]):
    ax.plot([8.8, 8.8], [y1 - 0.45, y2 + 0.45],
            color='#78909C', lw=1.6, linestyle='--', zorder=1)

# NSFNET annotation
ax.text(8.8, 1.52, 'NSFNET Topology — 14 nodes, 21 links',
        ha='center', va='center', fontsize=9, color='#263238', fontweight='bold',
        bbox=dict(facecolor='#ECEFF1', edgecolor='#455A64', pad=5,
                  boxstyle='round,pad=0.3', linewidth=1.5))

# ── Destination ───────────────────────────────────────────────────────────────
rbox(ax, 12.2, 4.1, 1.85, 0.82, C_DEST, edgecolor='#78909C')
label(ax, 12.2, 4.24, 'Destination', fs=11)
label(ax, 12.2, 3.94, 'Service', fs=9.5, fw='normal', style='italic')

# ── Arrows ────────────────────────────────────────────────────────────────────
arrow(ax, 2.18, 5.5, 2.88, 5.0, color=C_SRC, lw=2.2,
      txt='Legitimate traffic', tx=2.53, ty=5.42)
arrow(ax, 2.18, 2.8, 2.88, 3.3, color=C_ATK, lw=2.2,
      txt='Attack traffic', tx=2.53, ty=2.88)
arrow(ax, 5.52, 4.8, 7.75, 5.6, color='#546E7A', lw=1.8,
      txt='Classified traffic', tx=6.6, ty=5.38)
arrow(ax, 9.87, 2.6, 11.3, 3.85, color='#546E7A', lw=2.0,
      txt='Legitimate\ntraffic only', tx=10.55, ty=2.98)

darrow(ax, 4.85, 5.62, 5.7, 6.65, color='#1976D2', lw=1.8,
       txt='η(t), a(t)', tx=4.9, ty=6.3)
darrow(ax, 5.7, 6.65, 5.0, 5.82, color='#546E7A', lw=1.8,
       txt='K*(t), SFC\nconfig', tx=5.98, ty=6.06)
darrow(ax, 7.5, 6.62, 7.95, 6.0, color='#546E7A', lw=1.8,
       txt='VNF placement\n& steering', tx=8.68, ty=6.42)

# ── Legend ────────────────────────────────────────────────────────────────────
legend_items = [
    mpatches.Patch(color=C_SRC,  label='Legitimate Source'),
    mpatches.Patch(color=C_ATK,  label='DDoS Attacker'),
    mpatches.Patch(color=C_ING,  label='Ingress Fog Node'),
    mpatches.Patch(color=C_MON,  label='Monitor (η estimator)'),
    mpatches.Patch(color=C_CTRL, label='AALB Controller'),
    mpatches.Patch(color=C_FOG,  label='VNF Fog Node'),
    mpatches.Patch(color=C_DEST, label='Destination'),
]
ax.legend(handles=legend_items, loc='lower left', fontsize=9.5,
          framealpha=0.95, ncol=2, bbox_to_anchor=(0.0, 0.0),
          edgecolor='#B0BEC5')

plt.tight_layout(pad=0.4)
out_png = '/tmp/aalb_build/fig0_architecture.png'
out_pdf = '/tmp/aalb_build/fig0_architecture.pdf'
plt.savefig(out_png, dpi=250, bbox_inches='tight', facecolor=BG)
plt.savefig(out_pdf, bbox_inches='tight', facecolor=BG)
print(f"Saved {out_png}")
print(f"Saved {out_pdf}")
