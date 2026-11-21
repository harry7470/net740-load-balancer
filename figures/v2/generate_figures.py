#!/usr/bin/env python3
"""
AALB Performance Figure Generator
NET 470 — DePaul University — November 2026
Generates Figures 1-7 from raw experimental results using matplotlib.

Usage:
    python generate_figures.py [--csv raw_per_run.csv] [--out figures/]
"""
import csv, argparse, os, math
from collections import defaultdict

# --- Matplotlib setup
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.lines as mlines
    import numpy as np
    HAS_MPL = True
except ImportError:
    HAS_MPL = False
    print("matplotlib not installed. Run: pip install matplotlib numpy")
    exit(1)

# ------------------------------------------------------------------ CONFIG
METHODS = ['aalb', 'rr_sfc', 'lc_sfc', 'original_aalb']
LABELS  = { 'aalb': 'AALB', 'rr_sfc': 'RR-SFC',
            'lc_sfc': 'LC-SFC', 'original_aalb': 'Orig-AALB' }
COLORS  = { 'aalb': '#0072B2', 'rr_sfc': '#E69F00',
            'lc_sfc': '#009E73', 'original_aalb': '#CC79A7' }
DASHES  = { 'aalb': '-', 'rr_sfc': '--', 'lc_sfc': '-.', 'original_aalb': ':' }
MARKERS = { 'aalb': 'o', 'rr_sfc': 's', 'lc_sfc': '^', 'original_aalb': 'D' }
RATES   = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]

# ------------------------------------------------------------------ DATA LOADING
def load_data(csv_path):
    rows = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    grouped = defaultdict(list)
    for r in rows:
        key = (int(r['legitimate_rate_req_s']), r['method'])
        grouped[key].append(r)

    METRICS = [
        'admission_rate_pct', 'completed_throughput_req_s', 'mean_e2e_delay_ms',
        'cpu_utilization_pct', 'security_termination_rate_pct',
        'security_compliant_completion_rate_pct', 'mandatory_upgrade_success_rate_pct'
    ]

    def safe_float(v):
        try:
            f = float(v)
            return f if not math.isnan(f) else None
        except (ValueError, TypeError):
            return None

    data = {}
    for (rate, method), rlist in grouped.items():
        data[(rate, method)] = {}
        for m in METRICS:
            vals = [safe_float(r[m]) for r in rlist if safe_float(r[m]) is not None]
            data[(rate, method)][m] = sum(vals)/len(vals) if vals else None

    return data

# ------------------------------------------------------------------ PLOTTING
def get_series(data, metric, methods=None):
    if methods is None:
        methods = METHODS
    series = {}
    for m in methods:
        series[m] = [data.get((r, m), {}).get(metric) for r in RATES]
    return series

def setup_axes(ax, ylabel, ylim=None):
    ax.set_xlabel('Legitimate Request Arrival Rate (req/s)', fontsize=9, color='#555')
    ax.set_ylabel(ylabel, fontsize=9, color='#555')
    ax.set_xticks(RATES)
    ax.set_xticklabels([str(r) for r in RATES], fontsize=8)
    ax.tick_params(axis='y', labelsize=8)
    ax.grid(axis='y', color='#e0e0e0', linewidth=0.8, zorder=0)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#d0d0d0')
    ax.spines['bottom'].set_color('#d0d0d0')
    if ylim:
        ax.set_ylim(ylim)

def add_legend(ax, methods=None):
    if methods is None:
        methods = METHODS
    handles = []
    for m in methods:
        h = mlines.Line2D([], [], color=COLORS[m], linestyle=DASHES[m],
                          marker=MARKERS[m], markersize=5, linewidth=1.5,
                          label=LABELS[m])
        handles.append(h)
    ax.legend(handles=handles, fontsize=8, frameon=True, framealpha=0.9,
              edgecolor='#ddd', loc='best')

def plot_series(ax, series):
    for m, vals in series.items():
        x = [RATES[i] for i, v in enumerate(vals) if v is not None]
        y = [v for v in vals if v is not None]
        if not x:
            continue
        ax.plot(x, y, color=COLORS[m], linestyle=DASHES[m],
                marker=MARKERS[m], markersize=4.5, linewidth=1.8,
                markeredgecolor='white', markeredgewidth=0.8, zorder=3)

def save_fig(fig, path):
    fig.savefig(path, dpi=200, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    print(f'  Saved: {path}')

# ------------------------------------------------------------------ FIGURE FUNCTIONS
def fig1(data, out):
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.set_title('Fig. 1  Legitimate Admission Rate vs. Request Arrival Rate',
                 fontsize=9, fontweight='bold', pad=8)
    s = get_series(data, 'admission_rate_pct')
    plot_series(ax, s)
    setup_axes(ax, 'Legitimate Admission Rate (%)', ylim=(0, 110))
    add_legend(ax)
    save_fig(fig, os.path.join(out, 'fig1_admission_rate.pdf'))
    save_fig(fig, os.path.join(out, 'fig1_admission_rate.png')) if False else None
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.set_title('Fig. 1  Legitimate Admission Rate vs. Request Arrival Rate',
                 fontsize=9, fontweight='bold', pad=8)
    s = get_series(data, 'admission_rate_pct')
    plot_series(ax, s)
    setup_axes(ax, 'Legitimate Admission Rate (%)', ylim=(0, 110))
    add_legend(ax)
    save_fig(fig, os.path.join(out, 'fig1_admission_rate.png'))

def fig2(data, out):
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.set_title('Fig. 2  Completed Throughput vs. Request Arrival Rate',
                 fontsize=9, fontweight='bold', pad=8)
    s = get_series(data, 'completed_throughput_req_s')
    plot_series(ax, s)
    setup_axes(ax, 'Completed Throughput (req/s)', ylim=(0, None))
    add_legend(ax)
    save_fig(fig, os.path.join(out, 'fig2_throughput.png'))

def fig3(data, out):
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.set_title('Fig. 3  End-to-End Delay vs. Request Arrival Rate',
                 fontsize=9, fontweight='bold', pad=8)
    s = get_series(data, 'mean_e2e_delay_ms')
    plot_series(ax, s)
    # SLA line
    ax.axhline(y=20, color='#CC2929', linewidth=1.5, linestyle='--', zorder=2)
    ax.text(1000, 20.3, 'SLA 20 ms', fontsize=7.5, color='#CC2929', ha='right')
    setup_axes(ax, 'Mean E2E Delay (ms)', ylim=(8, 26))
    add_legend(ax)
    save_fig(fig, os.path.join(out, 'fig3_delay.png'))

def fig4(data, out):
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.set_title('Fig. 4  CPU Utilization vs. Request Arrival Rate',
                 fontsize=9, fontweight='bold', pad=8)
    s = get_series(data, 'cpu_utilization_pct')
    plot_series(ax, s)
    setup_axes(ax, 'Mean CPU Utilization (%)', ylim=(0, 100))
    add_legend(ax)
    save_fig(fig, os.path.join(out, 'fig4_cpu.png'))

def fig5(data, out):
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.set_title('Fig. 5  Security-Triggered Termination Rate vs. Request Arrival Rate',
                 fontsize=9, fontweight='bold', pad=8)
    s = get_series(data, 'security_termination_rate_pct')
    plot_series(ax, s)
    setup_axes(ax, 'Security Termination Rate (%)', ylim=(0, 0.6))
    add_legend(ax)
    save_fig(fig, os.path.join(out, 'fig5_security_termination.png'))

def fig6(data, out):
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.set_title('Fig. 6  Security-Compliant Completion Rate vs. Request Arrival Rate',
                 fontsize=9, fontweight='bold', pad=8)
    s = get_series(data, 'security_compliant_completion_rate_pct')
    plot_series(ax, s)
    setup_axes(ax, 'Security-Compliant Completion Rate (%)', ylim=(0, 110))
    add_legend(ax)
    save_fig(fig, os.path.join(out, 'fig6_compliant_completion.png'))

def fig7(data, out):
    fig, ax = plt.subplots(figsize=(5.5, 3.5))
    ax.set_title('Fig. 7  Mandatory Security-Upgrade Success Rate (AALB)',
                 fontsize=9, fontweight='bold', pad=8)
    s = get_series(data, 'mandatory_upgrade_success_rate_pct', methods=['aalb'])
    plot_series(ax, s)
    setup_axes(ax, 'Upgrade Success Rate (%)', ylim=(0, 100))
    ax.legend(handles=[mlines.Line2D([],[],color=COLORS['aalb'],linestyle='-',
              marker='o',markersize=5,linewidth=1.5,label='AALB')],
              fontsize=8, frameon=True, framealpha=0.9, edgecolor='#ddd', loc='best')
    save_fig(fig, os.path.join(out, 'fig7_upgrade_success.png'))

# ------------------------------------------------------------------ MAIN
def main():
    p = argparse.ArgumentParser()
    p.add_argument('--csv', default='raw_per_run.csv')
    p.add_argument('--out', default='figures')
    args = p.parse_args()

    os.makedirs(args.out, exist_ok=True)
    print(f'Loading data from {args.csv}...')
    data = load_data(args.csv)
    print(f'  {len(data)} (rate, method) combinations loaded')

    plt.rcParams.update({
        'font.family': 'DejaVu Sans',
        'font.size': 9,
        'figure.dpi': 150,
    })

    print('Generating figures...')
    fig1(data, args.out)
    fig2(data, args.out)
    fig3(data, args.out)
    fig4(data, args.out)
    fig5(data, args.out)
    fig6(data, args.out)
    fig7(data, args.out)
    print(f'\nDone — {len(os.listdir(args.out))} files in {args.out}/')

if __name__ == '__main__':
    main()
