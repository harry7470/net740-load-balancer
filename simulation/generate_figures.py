"""
Generate all figures and LaTeX tables for the NET470 report.
Figures saved to ../results/figures/
"""
import json, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── Load data ────────────────────────────────────────────────────────────────
data_path = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'results.json'))
with open(data_path) as f:
    data = json.load(f)

static    = data['static']
reconfig  = data['reconfig']
fig_dir   = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'results', 'figures'))
os.makedirs(fig_dir, exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────────
METHODS      = ['aalb', 'rr_sfc', 'lc_sfc', 'original_aalb']
METHOD_LABELS = {
    'aalb':          'AALB (proposed)',
    'rr_sfc':        'RR-SFC',
    'lc_sfc':        'LC-SFC',
    'original_aalb': 'Original AALB',
}
COLORS = {
    'aalb':          '#1a6faf',
    'rr_sfc':        '#e05c2a',
    'lc_sfc':        '#2e9c44',
    'original_aalb': '#9c2e9c',
}
MARKERS = {'aalb': 'o', 'rr_sfc': 's', 'lc_sfc': '^', 'original_aalb': 'D'}
REQ_RATES = [50,100,150,200,250,300,400,500,600,700,800]

def get_metric(method, eta, rate, metric):
    eta_key  = str(float(eta))
    rate_key = str(rate)
    row = static.get(method, {}).get(eta_key, {}).get(rate_key, {})
    return row.get(metric, float('nan'))

STYLE = dict(linewidth=1.8, markersize=5)

plt.rcParams.update({
    'font.size': 10,
    'axes.titlesize': 10,
    'axes.labelsize': 9,
    'xtick.labelsize': 8,
    'ytick.labelsize': 8,
    'legend.fontsize': 8,
    'grid.alpha': 0.35,
    'axes.grid': True,
})

# ══════════════════════════════════════════════════════════════════════════════
# Fig 1 — Admission Rate vs. λ for each η value
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), sharey=True)
eta_panels = [0.0, 0.4, 0.8]
for ax, eta in zip(axes, eta_panels):
    for m in METHODS:
        y = [get_metric(m, eta, r, 'admission_rate') for r in REQ_RATES]
        ax.plot(REQ_RATES, y, color=COLORS[m], marker=MARKERS[m],
                label=METHOD_LABELS[m], **STYLE)
    ax.set_title(f'η = {eta:.1f}')
    ax.set_xlabel('Request Rate (req/s)')
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, 850)
    ax.set_xticks([0,200,400,600,800])
axes[0].set_ylabel('Legitimate Admission Rate')
axes[0].legend(loc='lower left', framealpha=0.8)
fig.suptitle('Fig. 1 — Legitimate Admission Rate vs. Request Rate', fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'fig1_admission_rate.pdf'), bbox_inches='tight', dpi=150)
fig.savefig(os.path.join(fig_dir, 'fig1_admission_rate.png'), bbox_inches='tight', dpi=150)
plt.close(fig)
print('Saved fig1_admission_rate')

# ══════════════════════════════════════════════════════════════════════════════
# Fig 2 — Legitimate Throughput vs. λ
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(10, 3.2))
for ax, eta in zip(axes, eta_panels):
    for m in METHODS:
        y = [get_metric(m, eta, r, 'throughput') for r in REQ_RATES]
        ax.plot(REQ_RATES, y, color=COLORS[m], marker=MARKERS[m],
                label=METHOD_LABELS[m], **STYLE)
    ax.set_title(f'η = {eta:.1f}')
    ax.set_xlabel('Request Rate (req/s)')
    ax.set_xlim(0, 850)
    ax.set_xticks([0,200,400,600,800])
axes[0].set_ylabel('Legitimate Throughput (req/s)')
axes[0].legend(loc='upper left', framealpha=0.8)
fig.suptitle('Fig. 2 — Legitimate Throughput vs. Request Rate', fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'fig2_throughput.pdf'), bbox_inches='tight', dpi=150)
fig.savefig(os.path.join(fig_dir, 'fig2_throughput.png'), bbox_inches='tight', dpi=150)
plt.close(fig)
print('Saved fig2_throughput')

# ══════════════════════════════════════════════════════════════════════════════
# Fig 3 — Mean E2E Delay vs. λ (η=0.4)
# ══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(5, 3.2))
eta = 0.4
for m in METHODS:
    y = [get_metric(m, eta, r, 'mean_delay') for r in REQ_RATES]
    ax.plot(REQ_RATES, y, color=COLORS[m], marker=MARKERS[m],
            label=METHOD_LABELS[m], **STYLE)
ax.axhline(20, color='red', linestyle='--', linewidth=1.2, label='Delay bound (20 ms)')
ax.set_xlabel('Request Rate (req/s)')
ax.set_ylabel('Mean E2E Delay (ms)')
ax.set_title(f'Fig. 3 — Mean E2E Delay vs. Request Rate (η={eta})')
ax.set_xlim(0, 850)
ax.legend(framealpha=0.8, fontsize=7.5)
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'fig3_delay.pdf'), bbox_inches='tight', dpi=150)
fig.savefig(os.path.join(fig_dir, 'fig3_delay.png'), bbox_inches='tight', dpi=150)
plt.close(fig)
print('Saved fig3_delay')

# ══════════════════════════════════════════════════════════════════════════════
# Fig 4 — CPU/Memory/BW Utilization vs. λ (η=0.4)
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 3, figsize=(10, 3.2), sharey=True)
util_metrics = ['util_cpu', 'util_mem', 'util_bw']
util_labels  = ['CPU Utilization', 'Memory Utilization', 'BW Utilization']
eta = 0.4
for ax, metric, lbl in zip(axes, util_metrics, util_labels):
    for m in METHODS:
        y = [get_metric(m, eta, r, metric) for r in REQ_RATES]
        ax.plot(REQ_RATES, y, color=COLORS[m], marker=MARKERS[m],
                label=METHOD_LABELS[m], **STYLE)
    ax.set_title(lbl)
    ax.set_xlabel('Request Rate (req/s)')
    ax.set_xlim(0, 850)
    ax.set_ylim(0, 1.05)
    ax.set_xticks([0,200,400,600,800])
axes[0].set_ylabel('Utilization (fraction)')
axes[0].legend(loc='upper left', framealpha=0.8)
fig.suptitle('Fig. 4 — Resource Utilization vs. Request Rate (η=0.4)', fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'fig4_utilization.pdf'), bbox_inches='tight', dpi=150)
fig.savefig(os.path.join(fig_dir, 'fig4_utilization.png'), bbox_inches='tight', dpi=150)
plt.close(fig)
print('Saved fig4_utilization')

# ══════════════════════════════════════════════════════════════════════════════
# Fig 5 — Saturation curve: AALB admission rate & throughput vs λ
# ══════════════════════════════════════════════════════════════════════════════
fig, ax1 = plt.subplots(figsize=(5.5, 3.5))
ax2 = ax1.twinx()
for eta, ls in [(0.0, '-'), (0.4, '--'), (0.7, ':')]:
    ar = [get_metric('aalb', eta, r, 'admission_rate') for r in REQ_RATES]
    tp = [get_metric('aalb', eta, r, 'throughput')     for r in REQ_RATES]
    ax1.plot(REQ_RATES, ar, linestyle=ls, color='#1a6faf', marker='o',
             markersize=4, linewidth=1.6, label=f'Admission η={eta}')
    ax2.plot(REQ_RATES, tp, linestyle=ls, color='#e05c2a', marker='s',
             markersize=4, linewidth=1.6, label=f'Throughput η={eta}')
ax1.set_xlabel('Request Rate (req/s)')
ax1.set_ylabel('Legitimate Admission Rate', color='#1a6faf')
ax2.set_ylabel('Legitimate Throughput (req/s)', color='#e05c2a')
ax1.set_xlim(0, 850)
ax1.set_ylim(0, 1.05)
ax1.set_xticks([0,200,400,600,800])
lines1, labs1 = ax1.get_legend_handles_labels()
lines2, labs2 = ax2.get_legend_handles_labels()
ax1.legend(lines1+lines2, labs1+labs2, fontsize=7, loc='center left', framealpha=0.8)
ax1.set_title('Fig. 5 — AALB Saturation Curve', fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'fig5_saturation.pdf'), bbox_inches='tight', dpi=150)
fig.savefig(os.path.join(fig_dir, 'fig5_saturation.png'), bbox_inches='tight', dpi=150)
plt.close(fig)
print('Saved fig5_saturation')

# ══════════════════════════════════════════════════════════════════════════════
# Fig 6 — Reconfiguration: upgrades/downgrades/blocked per method
# ══════════════════════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(9, 3.5))
for ax, trace_name, title in [
        (axes[0], 'trace_a', 'Trace A (moderate η swings)'),
        (axes[1], 'trace_b', 'Trace B (severe η swings)'),
]:
    tr = reconfig.get(trace_name, {})
    x     = np.arange(len(METHODS))
    width = 0.25
    up_v  = [tr.get(m, {}).get('upgrades',   0) for m in METHODS]
    dn_v  = [tr.get(m, {}).get('downgrades', 0) for m in METHODS]
    bl_v  = [tr.get(m, {}).get('blocked',    0) for m in METHODS]
    ax.bar(x - width, up_v, width, label='Upgrades',   color='#1a6faf', alpha=0.85)
    ax.bar(x,         dn_v, width, label='Downgrades', color='#2e9c44', alpha=0.85)
    ax.bar(x + width, bl_v, width, label='Blocked reqs', color='#e05c2a', alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([METHOD_LABELS[m].replace(' (proposed)','') for m in METHODS],
                       rotation=15, ha='right', fontsize=8)
    ax.set_ylabel('Count')
    ax.set_title(title)
    ax.legend(fontsize=8)
fig.suptitle('Fig. 6 — Reconfiguration Events', fontsize=10)
fig.tight_layout()
fig.savefig(os.path.join(fig_dir, 'fig6_reconfig.pdf'), bbox_inches='tight', dpi=150)
fig.savefig(os.path.join(fig_dir, 'fig6_reconfig.png'), bbox_inches='tight', dpi=150)
plt.close(fig)
print('Saved fig6_reconfig')

# ══════════════════════════════════════════════════════════════════════════════
# LaTeX Table 1 — Admission Rate by Method × η (rate=150)
# ══════════════════════════════════════════════════════════════════════════════
etas_table = [0.0, 0.2, 0.4, 0.7, 0.8]
rate_ref   = 150

tex = []
tex.append(r"\begin{table}[t]")
tex.append(r"\centering")
tex.append(r"\caption{Legitimate Admission Rate (\%) at $\lambda=150$ req/s for varying attack intensity $\eta$.}")
tex.append(r"\label{tab:admission_rate}")
tex.append(r"\begin{tabular}{lrrrrr}")
tex.append(r"\toprule")
tex.append(r"Method & $\eta=0.0$ & $\eta=0.2$ & $\eta=0.4$ & $\eta=0.7$ & $\eta=0.8$ \\")
tex.append(r"\midrule")
for m in METHODS:
    row = [METHOD_LABELS[m]]
    for e in etas_table:
        v = get_metric(m, e, rate_ref, 'admission_rate')
        row.append(f"{v*100:.1f}")
    tex.append(" & ".join(row) + r" \\")
tex.append(r"\bottomrule")
tex.append(r"\end{tabular}")
tex.append(r"\end{table}")

tbl1_path = os.path.join(fig_dir, 'table1_admission.tex')
with open(tbl1_path, 'w') as f:
    f.write('\n'.join(tex))
print('Saved table1_admission.tex')

# ══════════════════════════════════════════════════════════════════════════════
# LaTeX Table 2 — Resource Utilization by Method (rate=150, η=0.4)
# ══════════════════════════════════════════════════════════════════════════════
tex2 = []
tex2.append(r"\begin{table}[t]")
tex2.append(r"\centering")
tex2.append(r"\caption{Average resource utilisation at $\lambda=150$ req/s, $\eta=0.4$.}")
tex2.append(r"\label{tab:utilization}")
tex2.append(r"\begin{tabular}{lrrr}")
tex2.append(r"\toprule")
tex2.append(r"Method & CPU & Memory & Bandwidth \\")
tex2.append(r"\midrule")
for m in METHODS:
    cpu = get_metric(m, 0.4, 150, 'util_cpu')
    mem = get_metric(m, 0.4, 150, 'util_mem')
    bw  = get_metric(m, 0.4, 150, 'util_bw')
    tex2.append(f"{METHOD_LABELS[m]} & {cpu:.3f} & {mem:.3f} & {bw:.3f} \\\\")
tex2.append(r"\bottomrule")
tex2.append(r"\end{tabular}")
tex2.append(r"\end{table}")

tbl2_path = os.path.join(fig_dir, 'table2_utilization.tex')
with open(tbl2_path, 'w') as f:
    f.write('\n'.join(tex2))
print('Saved table2_utilization.tex')

# ══════════════════════════════════════════════════════════════════════════════
# LaTeX Table 3 — Reconfiguration summary
# ══════════════════════════════════════════════════════════════════════════════
tex3 = []
tex3.append(r"\begin{table}[t]")
tex3.append(r"\centering")
tex3.append(r"\caption{Profile reconfiguration events over 120\,s simulation.}")
tex3.append(r"\label{tab:reconfig}")
tex3.append(r"\begin{tabular}{llrrr}")
tex3.append(r"\toprule")
tex3.append(r"Trace & Method & Upgrades & Downgrades & Blocked reqs \\")
tex3.append(r"\midrule")
for tname in ['trace_a', 'trace_b']:
    label = 'Trace A' if tname == 'trace_a' else 'Trace B'
    for i, m in enumerate(METHODS):
        row = reconfig.get(tname, {}).get(m, {})
        up  = row.get('upgrades', 0)
        dn  = row.get('downgrades', 0)
        bl  = row.get('blocked', 0)
        prefix = label if i == 0 else ''
        tex3.append(f"{prefix} & {METHOD_LABELS[m]} & {up:.1f} & {dn:.1f} & {bl:.1f} \\\\")
    if tname == 'trace_a':
        tex3.append(r"\midrule")
tex3.append(r"\bottomrule")
tex3.append(r"\end{tabular}")
tex3.append(r"\end{table}")

tbl3_path = os.path.join(fig_dir, 'table3_reconfig.tex')
with open(tbl3_path, 'w') as f:
    f.write('\n'.join(tex3))
print('Saved table3_reconfig.tex')

print(f'\nAll figures and tables written to {fig_dir}/')
