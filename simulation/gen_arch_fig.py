"""
Generate system architecture figure for Section III.
Shows: Traffic Sources → Ingress Fog Node (with Monitor) → Fog Network → Destination
Controller sits above, connected to Ingress.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import numpy as np

fig, ax = plt.subplots(figsize=(10, 5.5))
ax.set_xlim(0, 10)
ax.set_ylim(0, 5.5)
ax.axis('off')

# ── Colors ──────────────────────────────────────────────────────────────────
C_SRC    = '#4A90D9'   # blue — traffic sources
C_ING    = '#E67E22'   # orange — ingress fog node
C_FOG    = '#27AE60'   # green — fog nodes
C_DEST   = '#8E44AD'   # purple — destination
C_CTRL   = '#C0392B'   # red — controller
C_MON    = '#F39C12'   # amber — monitor
C_ARROW  = '#555555'
C_ATK    = '#E74C3C'   # attack arrow color
BG       = '#F8F9FA'

fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)

def box(ax, x, y, w, h, color, label, sublabel=None, fontsize=9):
    rect = FancyBboxPatch((x - w/2, y - h/2), w, h,
                          boxstyle="round,pad=0.08",
                          facecolor=color, edgecolor='white',
                          linewidth=1.5, zorder=3)
    ax.add_patch(rect)
    dy = 0.12 if sublabel else 0
    ax.text(x, y + dy, label, ha='center', va='center',
            fontsize=fontsize, fontweight='bold', color='white', zorder=4)
    if sublabel:
        ax.text(x, y - 0.22, sublabel, ha='center', va='center',
                fontsize=7.5, color='white', zorder=4, style='italic')

def arrow(ax, x1, y1, x2, y2, color=C_ARROW, style='->', lw=1.5, label=None, label_offset=(0,0.18)):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle=style, color=color, lw=lw),
                zorder=2)
    if label:
        mx, my = (x1+x2)/2 + label_offset[0], (y1+y2)/2 + label_offset[1]
        ax.text(mx, my, label, ha='center', va='center',
                fontsize=7.5, color=color, zorder=5,
                bbox=dict(facecolor=BG, edgecolor='none', pad=1))

def dashed_arrow(ax, x1, y1, x2, y2, color=C_CTRL, lw=1.4, label=None, label_offset=(0,0.18)):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                linestyle='dashed',
                                connectionstyle='arc3,rad=0'),
                zorder=2)
    if label:
        mx, my = (x1+x2)/2 + label_offset[0], (y1+y2)/2 + label_offset[1]
        ax.text(mx, my, label, ha='center', va='center',
                fontsize=7.5, color=color, zorder=5,
                bbox=dict(facecolor=BG, edgecolor='none', pad=1))

# ── Title band ───────────────────────────────────────────────────────────────
ax.text(5, 5.2, 'Attack-Aware Adaptive Security Service Orchestration Architecture',
        ha='center', va='center', fontsize=10, fontweight='bold', color='#2C3E50')

# ── Traffic Sources (left) ───────────────────────────────────────────────────
# Legitimate traffic source
box(ax, 0.9, 3.2, 1.3, 0.55, C_SRC, 'Legitimate', 'Traffic Source')
# Attack traffic source
box(ax, 0.9, 1.8, 1.3, 0.55, C_ATK, 'DDoS', 'Attack Source')

# ── Ingress Fog Node ─────────────────────────────────────────────────────────
box(ax, 3.3, 2.5, 1.6, 2.2, C_ING, 'Ingress', 'Fog Node', fontsize=9)

# Monitor sub-box inside ingress
rect_mon = FancyBboxPatch((2.7, 1.25), 1.2, 0.65,
                           boxstyle="round,pad=0.05",
                           facecolor=C_MON, edgecolor='white', linewidth=1, zorder=4)
ax.add_patch(rect_mon)
ax.text(3.3, 1.58, 'Monitor', ha='center', va='center',
        fontsize=8, fontweight='bold', color='white', zorder=5)

# SFC label inside ingress
ax.text(3.3, 2.85, 'Active SFC', ha='center', va='center',
        fontsize=8, color='white', zorder=5)
ax.text(3.3, 2.55, '⟨FW, RF, LB⟩', ha='center', va='center',
        fontsize=8, color='white', zorder=5, style='italic')

# ── Controller (top center) ───────────────────────────────────────────────────
box(ax, 5.0, 4.6, 2.0, 0.65, C_CTRL, 'Controller', fontsize=9)

# ── Fog Network (center) ──────────────────────────────────────────────────────
# 3 fog nodes representing the distributed network
fog_positions = [(5.4, 2.9), (6.5, 1.8), (5.4, 1.2)]
fog_labels    = ['Fog Node\n(FW-VNF)', 'Fog Node\n(RF-VNF)', 'Fog Node\n(LB-VNF)']
for (fx, fy), fl in zip(fog_positions, fog_labels):
    rect_f = FancyBboxPatch((fx - 0.65, fy - 0.38), 1.3, 0.76,
                             boxstyle="round,pad=0.06",
                             facecolor=C_FOG, edgecolor='white', linewidth=1.2, zorder=3)
    ax.add_patch(rect_f)
    ax.text(fx, fy, fl, ha='center', va='center',
            fontsize=7.5, fontweight='bold', color='white', zorder=4)

# Links between fog nodes (mesh)
fog_links = [(0,1),(1,2),(0,2)]
for i,j in fog_links:
    fx1,fy1 = fog_positions[i]
    fx2,fy2 = fog_positions[j]
    ax.plot([fx1,fx2],[fy1,fy2], color='#95A5A6', lw=1.2, zorder=1, linestyle='--')

# ── Destination ───────────────────────────────────────────────────────────────
box(ax, 8.8, 2.0, 1.3, 0.6, C_DEST, 'Destination', 'Service', fontsize=9)

# ── Arrows ───────────────────────────────────────────────────────────────────
# Legit traffic → ingress
arrow(ax, 1.55, 3.2, 2.5, 2.8, color=C_SRC, label='Legitimate\ntraffic', label_offset=(0, 0.28))
# Attack traffic → ingress
arrow(ax, 1.55, 1.8, 2.5, 2.1, color=C_ATK, label='Attack\ntraffic', label_offset=(0, -0.28))

# Ingress → fog node 0 (FW)
arrow(ax, 4.1, 2.7, 4.75, 2.9, color=C_FOG, lw=1.4)
# Fog node ordering (SFC path)
arrow(ax, 5.75, 2.65, 6.2, 2.1, color=C_FOG, lw=1.2)
arrow(ax, 6.35, 1.55, 5.85, 1.35, color=C_FOG, lw=1.2)

# Last fog node → Destination
arrow(ax, 6.05, 1.2, 8.15, 1.85, color=C_FOG, label='Legitimate\ntraffic only', label_offset=(0,-0.28))

# Monitor → Controller (measurement report, dashed up)
dashed_arrow(ax, 3.6, 3.6, 4.0, 4.28, color=C_MON, label='η(t), a(t)', label_offset=(-0.55, 0))

# Controller → Ingress (reconfiguration command, dashed down)
dashed_arrow(ax, 4.2, 4.28, 3.9, 3.6, color=C_CTRL, label='K*(t), X*(t)', label_offset=(0.65, 0))

# Controller → Fog nodes (placement/steering)
dashed_arrow(ax, 5.5, 4.28, 5.4, 3.28, color=C_CTRL, label='VNF placement\n& steering', label_offset=(0.85, 0))

# ── Legend ────────────────────────────────────────────────────────────────────
legend_items = [
    mpatches.Patch(color=C_SRC,  label='Legitimate Source'),
    mpatches.Patch(color=C_ATK,  label='DDoS Attacker'),
    mpatches.Patch(color=C_ING,  label='Ingress Fog Node'),
    mpatches.Patch(color=C_MON,  label='Monitor'),
    mpatches.Patch(color=C_CTRL, label='Controller'),
    mpatches.Patch(color=C_FOG,  label='NFV Fog Node'),
    mpatches.Patch(color=C_DEST, label='Destination'),
]
ax.legend(handles=legend_items, loc='lower left', fontsize=7,
          framealpha=0.85, ncol=2, bbox_to_anchor=(0, 0))

plt.tight_layout(pad=0.3)
plt.savefig('/tmp/claude-0/-home-claude/8641c8f6-757f-517a-9271-1fc015db3b24/scratchpad/fig0_architecture.png',
            dpi=150, bbox_inches='tight', facecolor=BG)
print("Saved fig0_architecture.png")
