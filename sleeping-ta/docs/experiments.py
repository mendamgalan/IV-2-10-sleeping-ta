"""Experiments used in Report.md (sections 8-9).

Usage (from sleeping-ta/, after make):  python3 docs/experiments.py
Prints the Markdown tables and writes docs/images/chairs.svg.
"""
import hashlib
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from model import Model  # noqa: E402

CHAIRS = (0, 1, 2, 3, 5)
SEEDS = (1, 2, 3, 4, 5)
TICKS = 6000  # 10 model minutes
BASE = dict(n=6, amin=20, amax=80, hmin=10, hmax=30)  # 6 students, 2-8 s, 1-3 s


def chairs_sweep(model):
    rows = []
    for chairs in CHAIRS:
        rejected, wait, load, helps = [], [], [], []
        for seed in SEEDS:
            model.reset(chairs=chairs, seed=seed, **BASE)
            s = model.advance(TICKS)
            helped = s['completed'] + (s['current'] >= 0)
            rejected.append(100 * s['rejected'] / s['arrivals'])
            wait.append(s['wait_sum'] / helped / 10)
            load.append(100 * s['busy'] / s['tick'])
            helps.append(s['completed'] / (TICKS / 600))
        rows.append((chairs, *(statistics.mean(x) for x in (rejected, wait, load, helps))))
    return rows


def fairness(model, label, seed=42, **config):
    model.reset(seed=seed, **config)
    s = model.advance(1010)
    visits = [x['visits'] for x in s['students']]
    served = sum(1 for v in visits if v)
    return (label, served, len(visits), min(visits), statistics.median(visits), max(visits))


def journal_hash(model, free):
    model.reset(n=12, chairs=3, amin=5, amax=40, hmin=10, hmax=30, seed=42, free=free)
    model.advance(3000)
    return hashlib.sha256(model.events().encode()).hexdigest()[:12]


def svg_chart(rows, path):
    """Two panels with one y-axis each: percentages, and waiting time."""
    blue, orange, aqua = '#2a78d6', '#eb6834', '#1baf7a'
    ink, muted, grid, surface = '#0b0b0b', '#52514e', '#e4e3df', '#fcfcfb'
    width, height = 760, 300
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}" font-family="DejaVu Sans" font-size="12">',
           f'<rect width="{width}" height="{height}" fill="{surface}"/>']

    def panel(left, w, title, top_value, steps, unit, series):
        top, bottom, x0, x1 = 70, 250, left + 52, left + w - 46
        x_of = lambda chairs: x0 + chairs / CHAIRS[-1] * (x1 - x0)  # linear: 3 -> 5 is 2 chairs
        y_of = lambda v: bottom - v / top_value * (bottom - top)
        out.append(f'<text x="{left}" y="22" font-size="14" font-weight="bold" fill="{ink}">{title}</text>')
        for k in range(steps + 1):
            v = top_value * k / steps
            y = y_of(v)
            out.append(f'<line x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}" stroke="{grid}"/>')
            out.append(f'<text x="{x0 - 8}" y="{y + 4:.1f}" text-anchor="end" fill="{muted}">{v:g}{unit}</text>')
        for chairs in CHAIRS:
            out.append(f'<text x="{x_of(chairs):.1f}" y="{bottom + 18}" text-anchor="middle" fill="{muted}">{chairs}</text>')
        out.append(f'<text x="{(x0 + x1) / 2:.1f}" y="{bottom + 38}" text-anchor="middle" '
                   f'fill="{muted}">Сандлын тоо</text>')
        for name, color, values in series:
            d = ' '.join(f'{"M" if i == 0 else "L"} {x_of(c):.1f} {y_of(v):.1f}'
                         for i, (c, v) in enumerate(zip(CHAIRS, values)))
            out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"/>')
            for c, v in zip(CHAIRS, values):
                out.append(f'<circle cx="{x_of(c):.1f}" cy="{y_of(v):.1f}" r="4.5" fill="{color}" '
                           f'stroke="{surface}" stroke-width="2"/>')
            out.append(f'<text x="{x_of(CHAIRS[-1]) + 9:.1f}" y="{y_of(values[-1]) + 4:.1f}" '
                       f'fill="{ink}">{values[-1]:.0f}{unit}</text>')

    rejected = [r[1] for r in rows]
    load = [r[3] for r in rows]
    wait = [r[2] for r in rows]
    panel(10, 460, 'Буцалт ба TA-ийн ачаалал, %', 100, 4, '%',
          [('Буцалт', blue, rejected), ('TA ачаалал', orange, load)])
    # legend for the two-series panel, so identity is not colour-only
    out.append(f'<rect x="62" y="38" width="14" height="3" fill="{blue}"/>'
               f'<text x="82" y="44" fill="{ink}">Сандалгүй буцсан ирэлт</text>'
               f'<rect x="250" y="38" width="14" height="3" fill="{orange}"/>'
               f'<text x="270" y="44" fill="{ink}">TA завгүй байсан хугацаа</text>')
    top_wait = 2 * (int(max(wait) / 2) + 1)
    panel(490, 270, 'Дундаж хүлээлт, с', top_wait, top_wait // 2, ' с', [('Хүлээлт', aqua, wait)])
    out.append('</svg>')
    path.write_text('\n'.join(out) + '\n', encoding='utf-8')


def main():
    model = Model()
    rows = chairs_sweep(model)
    print('Сандлын туршилт: 6 оюутан, программчлах 2–8 с, тусламж 1–3 с, 10 мин, 5 seed-ийн дундаж\n')
    print('| Сандал | Буцалт, % | Дундаж хүлээлт, с | TA ачаалал, % | Тусламж / мин |')
    print('|---:|---:|---:|---:|---:|')
    for chairs, rej, wait, load, helps in rows:
        print(f'| {chairs} | {rej:.1f} | {wait:.2f} | {load:.1f} | {helps:.1f} |')
    svg_chart(rows, ROOT / 'docs' / 'images' / 'chairs.svg')

    print('\nТусламжийн хуваарилалт (1010 tick, seed 42)\n')
    print('| Тохиргоо | Тусламж авсан оюутан | Хамгийн бага / медиан / их |')
    print('|---|---:|---:|')
    for row in (fairness(model, 'Урт туршилт: 40 / 0, 0.1 с, 1 с', n=40, chairs=0, amin=1, amax=1, hmin=10, hmax=10),
                fairness(model, 'Ачаалал: 20 / 3, 0.1–0.2 с, 3–4 с', n=20, chairs=3, amin=1, amax=2, hmin=30, hmax=40),
                fairness(model, 'Ердийн: 8 / 3, 1–4 с, 1.5–3 с', n=8, chairs=3, amin=10, amax=40, hmin=15, hmax=30)):
        label, served, total, low, mid, high = row
        print(f'| {label} | {served} / {total} | {low} / {mid:g} / {high} |')

    seeded = {journal_hash(model, False) for _ in range(3)}
    free = {journal_hash(model, True) for _ in range(3)}
    print(f'\nЖурналын hash, 3 ажиллуулалт: seed горим {len(seeded)} ялгаатай {sorted(seeded)}, '
          f'чөлөөт горим {len(free)} ялгаатай')
    model.close()


if __name__ == '__main__':
    main()
