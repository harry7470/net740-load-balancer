"""
Generate all 7 paper figures from sim_results.json (v2 — includes rejection breakdown).
Outputs: /tmp/aalb_final/figures/fig[1-7].[pdf|png]
"""
import json, os, math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

FIG_DIR = '/tmp/aalb_final/figures'
os.makedirs(FIG_DIR, exist_ok=True)

with open('/tmp/aalb_sim/sim_results.json') as f:
    D = json.load(f)

ea = D['a']   # Exp A: admission vs lambda benign
eb = D['b']   # Exp B: throughput/CPU under attack
ec = D['c']   # Exp C: delay benign
ed = D['d']   # Exp D: saturation CPU util
ee = D['e']   # Exp E: reconfig traces
ef = D['f']   # Exp F: hysteresis

METHODS = ['AALB', 'RR', 'LC', 'OrigAALB']
LABELS  = {'AALB':'AALB', 'RR':'RR-SFC', 'LC':'LC-SFC', 'OrigAALB':'Orig-AALB'}
COLORS  = {'AALB':'#1a73e8', 'RR':'#e53935', 'LC':'#43a047', 'OrigAALB':'#fb8c00'}
MARKERS = {'AALB':'o', 'RR':'s', 'LC':'^', 'OrigAALB':'D'}
LS      = {'AALB':'-', 'RR':'--', 'LC':':', 'OrigAALB':'-.'}

plt.rcParams.update({
    'font.family':'serif', 'font.size':9,
    'axes.linewidth':0.8, 'axes.grid':True,
    'grid.linewidth':0.4, 'grid.alpha':0.5,
    'lines.linewidth':1.5, 'lines.markersize':4.5,
})

def savefig(name):
    for ext in ['pdf','png']:
        plt.savefig(f'{FIG_DIR}/{name}.{ext}', dpi=180, bbox_inches='tight')
    plt.close()
    print(f'  Saved {name}')

# ── Fig 1: Admission Rate vs λ (benign) ─────────────────────────────────────
fig, ax = plt.subplots(figsize=(3.3, 2.6))
for m in METHODS:
    xs = [r['lambda_legit'] for r in ea[m]]
    ys = [r['admission_rate']*100 for r in ea[m]]
    ax.plot(xs, ys, color=COLORS[m], marker=MARKERS[m], ls=LS[m], label=LABELS[m])
ax.set_xlabel('Arrival rate λ_ℓ (req/s)')
ax.set_ylabel('Admission rate (%)')
ax.set_title('Admission Rate vs. Load (η = 0)')
ax.legend(fontsize=7, loc='upper right')
ax.set_ylim(0, 105)
savefig('fig1')

# ── Fig 2: Throughput vs λ (attack η=0.4) ───────────────────────────────────
fig, ax = plt.subplots(figsize=(3.3, 2.6))
for m in METHODS:
    xs = [r['lambda_legit'] for r in eb[m]]
    ys = [r['throughput'] for r in eb[m]]
    ax.plot(xs, ys, color=COLORS[m], marker=MARKERS[m], ls=LS[m], label=LABELS[m])
ax.set_xlabel('Arrival rate λ_ℓ (req/s)')
ax.set_ylabel('Throughput (req/s)')
ax.set_title('Legitimate Throughput (η = 0.4 attack)')
ax.legend(fontsize=7)
savefig('fig2')

# ── Fig 3: Mean E2E Delay vs λ (benign) ─────────────────────────────────────
fig, ax = plt.subplots(figsize=(3.3, 2.6))
for m in METHODS:
    xs = [r['lambda_legit'] for r in ec[m]]
    ys = [r['mean_delay_ms'] for r in ec[m]]
    ax.plot(xs, ys, color=COLORS[m], marker=MARKERS[m], ls=LS[m], label=LABELS[m])
ax.axhline(100, color='black', lw=1.0, ls='--', label='SLA (100 ms)')
ax.set_xlabel('Arrival rate λ_ℓ (req/s)')
ax.set_ylabel('Mean E2E delay (ms)')
ax.set_title('End-to-End Delay (η = 0)')
ax.legend(fontsize=7)
savefig('fig3')

# ── Fig 4: CPU Utilisation, saturation zone ──────────────────────────────────
fig, ax = plt.subplots(figsize=(3.3, 2.6))
for m in METHODS:
    xs = [r['lambda_legit'] for r in ed[m]]
    ys = [r['mean_cpu_util']*100 for r in ed[m]]
    ax.plot(xs, ys, color=COLORS[m], marker=MARKERS[m], ls=LS[m], label=LABELS[m])
ax.set_xlabel('Arrival rate λ_ℓ (req/s)')
ax.set_ylabel('Mean CPU utilisation (%)')
ax.set_title('CPU Utilisation — Saturation Zone (η = 0)')
ax.legend(fontsize=7)
ax.set_ylim(0, 100)
savefig('fig4')

# ── Fig 5: Reconfigs bar chart (Trace A and B) ───────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(5.5, 2.4), sharey=True)
for ax, tn in zip(axes, ['A','B']):
    vals = [round(ee[tn][m]['total_reconfigs']) for m in METHODS]
    bars = ax.bar([LABELS[m] for m in METHODS], vals,
                  color=[COLORS[m] for m in METHODS], width=0.5, edgecolor='white')
    ax.set_title(f'Trace {tn}')
    ax.set_ylabel('Total reconfigurations' if tn=='A' else '')
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.05, str(v),
                ha='center', va='bottom', fontsize=7)
fig.suptitle('Profile Reconfigurations per Method (τ_H = 10 s)', fontsize=9)
plt.tight_layout()
savefig('fig5')

# ── Fig 6: Hysteresis — reconfigs + admission ────────────────────────────────
taus    = [r['tau_H'] for r in ef]
reconfigs = [round(r['total_reconfigs']) for r in ef]
admissions= [r['admission_rate']*100 for r in ef]

fig, ax1 = plt.subplots(figsize=(3.3, 2.6))
ax2 = ax1.twinx()
l1, = ax1.plot(taus, reconfigs,  color='#1a73e8', marker='o', label='Reconfigs')
l2, = ax2.plot(taus, admissions, color='#e53935', marker='s', ls='--', label='Admission %')
ax1.set_xlabel('Hysteresis window τ_H (s)')
ax1.set_ylabel('Reconfigurations', color='#1a73e8')
ax2.set_ylabel('Admission rate (%)', color='#e53935')
ax1.set_xticks(taus)
ax1.legend(handles=[l1,l2], fontsize=7, loc='center right')
ax1.set_title('Hysteresis Sensitivity (AALB, λ_ℓ = 300)')
savefig('fig6')

# ── Fig 7: Rejection Breakdown @ λ=600 (benign, Exp A) ──────────────────────
fig, ax = plt.subplots(figsize=(4.5, 2.6))
categories = ['CPU', 'Memory', 'BW', 'Delay']
x = np.arange(len(METHODS))
w = 0.18
row600 = {m: min(ea[m], key=lambda r: abs(r['lambda_legit']-600)) for m in METHODS}

bars_cpu   = [row600[m]['blocked_cpu']   for m in METHODS]
bars_mem   = [row600[m]['blocked_mem']   for m in METHODS]
bars_bw    = [row600[m]['blocked_bw']    for m in METHODS]
bars_delay = [row600[m]['blocked_delay'] for m in METHODS]

offsets = [-1.5, -0.5, 0.5, 1.5]
cat_colors = ['#e53935','#fb8c00','#43a047','#1a73e8']
for vals, lbl, col, off in zip(
        [bars_cpu, bars_mem, bars_bw, bars_delay],
        categories, cat_colors, offsets):
    ax.bar(x + off*w, vals, w, label=lbl, color=col, edgecolor='white')

ax.set_xticks(x)
ax.set_xticklabels([LABELS[m] for m in METHODS])
ax.set_ylabel('Blocked requests')
ax.set_title('Rejection Breakdown by Constraint (λ_ℓ = 600, η = 0)')
ax.legend(fontsize=7, ncol=2)
savefig('fig7')

print("All figures generated.")
