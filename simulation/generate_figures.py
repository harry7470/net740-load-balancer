"""
Generate all figures for Project 7 paper.
"""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# Load results
with open('/tmp/claude-0/-home-claude/8641c8f6-757f-517a-9271-1fc015db3b24/scratchpad/results.json') as f:
    data = json.load(f)

static = data['static']
reconfig = data['reconfig']

METHODS = ['aalb', 'rr_sfc', 'lc_sfc', 'original_aalb']
METHOD_LABELS = {
    'aalb':         'AALB (proposed)',
    'rr_sfc':       'RR-SFC',
    'lc_sfc':       'LC-SFC',
    'original_aalb':'Original AALB',
}
COLORS = {
    'aalb':          '#1f77b4',   # blue
    'rr_sfc':        '#d62728',   # red
    'lc_sfc':        '#2ca02c',   # green
    'original_aalb': '#ff7f0e',   # orange
}
MARKERS = {
    'aalb':          'o',
    'rr_sfc':        's',
    'lc_sfc':        '^',
    'original_aalb': 'D',
}
LINESTYLES = {
    'aalb':          '-',
    'rr_sfc':        '--',
    'lc_sfc':        '-.',
    'original_aalb': ':',
}

REQ_RATES   = [50, 100, 150, 200, 250]
ATTACK_ETAS = [0.0, 0.2, 0.4, 0.7, 0.8]

OUTDIR = '/tmp/claude-0/-home-claude/8641c8f6-757f-517a-9271-1fc015db3b24/scratchpad'

def fig_path(name):
    return f'{OUTDIR}/{name}'

plt.rcParams.update({
    'font.family': 'serif',
    'font.size': 11,
    'axes.titlesize': 12,
    'axes.labelsize': 11,
    'legend.fontsize': 9,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.dpi': 150,
    'lines.linewidth': 1.8,
    'lines.markersize': 6,
})

# ── Figure 1: Success Rate vs Request Rate (η = 0.4) ──────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 3.8))
eta = '0.4'
for m in METHODS:
    yvals = [static[m][eta][str(r)]['success_rate'] for r in REQ_RATES]
    ax.plot(REQ_RATES, yvals, color=COLORS[m], marker=MARKERS[m],
            linestyle=LINESTYLES[m], label=METHOD_LABELS[m])

ax.set_xlabel('Request Rate (req/s)')
ax.set_ylabel('Request Success Rate')
ax.set_title('Success Rate vs. Request Rate (η = 0.4)')
ax.set_xlim(40, 260)
ax.set_ylim(0, 1.05)
ax.set_xticks(REQ_RATES)
ax.legend(loc='lower left')
ax.grid(True, linestyle=':', alpha=0.5)
fig.tight_layout()
fig.savefig(fig_path('fig1_success_rate_vs_rate.pdf'), bbox_inches='tight')
fig.savefig(fig_path('fig1_success_rate_vs_rate.png'), bbox_inches='tight')
plt.close()
print("Fig 1 saved")

# ── Figure 2: Mean Delay vs Request Rate (η = 0.4) ────────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 3.8))
eta = '0.4'
for m in METHODS:
    yvals = [static[m][eta][str(r)]['mean_delay'] for r in REQ_RATES]
    ax.plot(REQ_RATES, yvals, color=COLORS[m], marker=MARKERS[m],
            linestyle=LINESTYLES[m], label=METHOD_LABELS[m])

ax.set_xlabel('Request Rate (req/s)')
ax.set_ylabel('Mean Delay (ms)')
ax.set_title('Mean E2E Delay vs. Request Rate (η = 0.4)')
ax.set_xlim(40, 260)
ax.set_xticks(REQ_RATES)
ax.legend(loc='upper left')
ax.grid(True, linestyle=':', alpha=0.5)
fig.tight_layout()
fig.savefig(fig_path('fig2_delay_vs_rate.pdf'), bbox_inches='tight')
fig.savefig(fig_path('fig2_delay_vs_rate.png'), bbox_inches='tight')
plt.close()
print("Fig 2 saved")

# ── Figure 3: Success Rate vs Attack Ratio (rate = 150) ───────────────────────
fig, ax = plt.subplots(figsize=(5.5, 3.8))
rate = '150'
for m in METHODS:
    yvals = [static[m][str(e)][rate]['success_rate'] for e in ATTACK_ETAS]
    ax.plot(ATTACK_ETAS, yvals, color=COLORS[m], marker=MARKERS[m],
            linestyle=LINESTYLES[m], label=METHOD_LABELS[m])

ax.set_xlabel('Attack Ratio η')
ax.set_ylabel('Request Success Rate')
ax.set_title('Success Rate vs. Attack Ratio (rate = 150 req/s)')
ax.set_xlim(-0.02, 0.85)
ax.set_ylim(0, 1.05)
ax.set_xticks(ATTACK_ETAS)
ax.legend(loc='upper right')
ax.grid(True, linestyle=':', alpha=0.5)
fig.tight_layout()
fig.savefig(fig_path('fig3_success_rate_vs_eta.pdf'), bbox_inches='tight')
fig.savefig(fig_path('fig3_success_rate_vs_eta.png'), bbox_inches='tight')
plt.close()
print("Fig 3 saved")

# ── Figure 4: Mean Delay vs Attack Ratio (rate = 150) ─────────────────────────
fig, ax = plt.subplots(figsize=(5.5, 3.8))
rate = '150'
for m in METHODS:
    yvals = [static[m][str(e)][rate]['mean_delay'] for e in ATTACK_ETAS]
    ax.plot(ATTACK_ETAS, yvals, color=COLORS[m], marker=MARKERS[m],
            linestyle=LINESTYLES[m], label=METHOD_LABELS[m])

ax.set_xlabel('Attack Ratio η')
ax.set_ylabel('Mean Delay (ms)')
ax.set_title('Mean E2E Delay vs. Attack Ratio (rate = 150 req/s)')
ax.set_xlim(-0.02, 0.85)
ax.set_xticks(ATTACK_ETAS)
ax.legend(loc='upper left')
ax.grid(True, linestyle=':', alpha=0.5)
fig.tight_layout()
fig.savefig(fig_path('fig4_delay_vs_eta.pdf'), bbox_inches='tight')
fig.savefig(fig_path('fig4_delay_vs_eta.png'), bbox_inches='tight')
plt.close()
print("Fig 4 saved")

# ── Figure 5: Reconfig counts – Trace A vs Trace B ────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(9, 3.8))

x = np.arange(len(METHODS))
width = 0.35

for ax_idx, (trace_key, trace_label) in enumerate([('trace_a', 'Trace A (mild)'), ('trace_b', 'Trace B (severe)')]):
    ax = axes[ax_idx]
    upgrades   = [reconfig[trace_key][m]['upgrades']   for m in METHODS]
    downgrades = [reconfig[trace_key][m]['downgrades'] for m in METHODS]

    b1 = ax.bar(x - width/2, upgrades,   width, label='Upgrades',   color='#e74c3c', alpha=0.85)
    b2 = ax.bar(x + width/2, downgrades, width, label='Downgrades', color='#3498db', alpha=0.85)

    ax.set_xlabel('Method')
    ax.set_ylabel('Reconfigurations')
    ax.set_title(f'Reconfiguration Count – {trace_label}')
    ax.set_xticks(x)
    ax.set_xticklabels([METHOD_LABELS[m].replace(' (proposed)', '\n(proposed)').replace(' AALB', '\nAALB') for m in METHODS],
                       fontsize=8)
    ax.legend(fontsize=8)
    ax.grid(True, axis='y', linestyle=':', alpha=0.5)

    for bar in b1:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.5, f'{h:.0f}', ha='center', va='bottom', fontsize=7)
    for bar in b2:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.5, f'{h:.0f}', ha='center', va='bottom', fontsize=7)

fig.tight_layout()
fig.savefig(fig_path('fig5_reconfig_counts.pdf'), bbox_inches='tight')
fig.savefig(fig_path('fig5_reconfig_counts.png'), bbox_inches='tight')
plt.close()
print("Fig 5 saved")

# ── Figure 6: P95 delay and throughput at rate=150 ────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))

# P95 delay
ax = axes[0]
rate = '150'
for m in METHODS:
    yvals = [static[m][str(e)][rate]['p95_delay'] for e in ATTACK_ETAS]
    ax.plot(ATTACK_ETAS, yvals, color=COLORS[m], marker=MARKERS[m],
            linestyle=LINESTYLES[m], label=METHOD_LABELS[m])
ax.set_xlabel('Attack Ratio η')
ax.set_ylabel('95th-Percentile Delay (ms)')
ax.set_title('P95 Delay vs. Attack Ratio (rate = 150 req/s)')
ax.set_xlim(-0.02, 0.85)
ax.set_xticks(ATTACK_ETAS)
ax.legend(loc='upper left', fontsize=8)
ax.grid(True, linestyle=':', alpha=0.5)

# Throughput
ax = axes[1]
for m in METHODS:
    yvals = [static[m][str(e)][rate]['throughput'] for e in ATTACK_ETAS]
    ax.plot(ATTACK_ETAS, yvals, color=COLORS[m], marker=MARKERS[m],
            linestyle=LINESTYLES[m], label=METHOD_LABELS[m])
ax.set_xlabel('Attack Ratio η')
ax.set_ylabel('Throughput (req/s)')
ax.set_title('Throughput vs. Attack Ratio (rate = 150 req/s)')
ax.set_xlim(-0.02, 0.85)
ax.set_xticks(ATTACK_ETAS)
ax.legend(loc='upper right', fontsize=8)
ax.grid(True, linestyle=':', alpha=0.5)

fig.tight_layout()
fig.savefig(fig_path('fig6_p95_throughput.pdf'), bbox_inches='tight')
fig.savefig(fig_path('fig6_p95_throughput.png'), bbox_inches='tight')
plt.close()
print("Fig 6 saved")

print("\nAll figures saved to:", OUTDIR)
