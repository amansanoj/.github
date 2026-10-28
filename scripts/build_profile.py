#!/usr/bin/env python3
"""Generate self-contained profile SVGs using only Python's standard library.

python3 scripts/build_profile.py --fetch   # fresh public GitHub data
python3 scripts/build_profile.py          # render the committed snapshot offline
"""
import argparse
from datetime import date, datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USER = 'amansanoj'
THEMES = {
    'dark': dict(bg='#050505', fg='#e6e6e6', muted='#8d8d92', line='#26272b',
                 panel='#101113', blue='#afbdd9', gold='#f0a133',
                 ramp=['#17191d', '#2a3858', '#465f9a', '#7f94c4', '#c6d2ec']),
    'light': dict(bg='#fafafa', fg='#1a1a1a', muted='#62626a', line='#dcdde0',
                  panel='#f0f1f3', blue='#263450', gold='#9b5c0a',
                  ramp=['#e8eaee', '#c3cde3', '#8199c6', '#4a639a', '#263450']),
}


# ---------------------------------------------------------------- data

class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.cells = {}
        self.tips = {}
        self.tip_id = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'data-date' in a and 'data-level' in a:
            self.cells[a['id']] = {'date': a['data-date'], 'level': int(a['data-level'])}
        if tag == 'tool-tip':
            self.tip_id = a.get('for')
            if self.tip_id:
                self.tips[self.tip_id] = ''

    def handle_data(self, data):
        if self.tip_id:
            self.tips[self.tip_id] += data

    def handle_endtag(self, tag):
        if tag == 'tool-tip':
            self.tip_id = None


def parse_calendar(html):
    parser = CalendarParser()
    parser.feed(html)
    days = []
    for cell_id, cell in parser.cells.items():
        label = parser.tips.get(cell_id, '').strip()
        match = re.match(r'(No|[\d,]+) contributions?\b', label)
        if not match:
            raise ValueError(f'Missing or changed contribution count for {cell["date"]}')
        count = 0 if match[1] == 'No' else int(match[1].replace(',', ''))
        days.append({**cell, 'count': count})
    days.sort(key=lambda d: d['date'])
    validate_days(days)
    return days


def validate_days(days):
    if not 350 <= len(days) <= 371:
        raise ValueError(f'Expected a full annual calendar, got {len(days)} days')
    previous = None
    for day in days:
        current = date.fromisoformat(day['date'])
        if previous is not None and current != previous + timedelta(days=1):
            raise ValueError('Calendar dates are duplicated or discontinuous')
        if type(day['count']) is not int or day['count'] < 0 or day['level'] not in range(5):
            raise ValueError('Invalid daily count or level')
        if (day['count'] == 0) != (day['level'] == 0):
            raise ValueError('Contribution count and shade disagree')
        previous = current


def fetch_snapshot():
    url = f'https://github.com/users/{USER}/contributions'
    request = Request(url, headers={'User-Agent': 'amansanoj-profile/1.0', 'Accept': 'text/html'})
    with urlopen(request, timeout=30) as response:
        days = parse_calendar(response.read().decode('utf-8'))
    today = datetime.now(timezone.utc).date()
    if not today - timedelta(days=1) <= date.fromisoformat(days[-1]['date']) <= today + timedelta(days=1):
        raise ValueError('GitHub returned an outdated contribution calendar')
    return {'username': USER, 'source': url, 'snapshot_date': today.isoformat(), 'days': days}


def longest_streak(days):
    best = run = 0
    for d in days:
        run = run + 1 if d['count'] else 0
        best = max(best, run)
    return best


def pretty(d):
    return f'{d.day} {d.strftime("%b")} {d.year}'


def plural(n, word):
    return f'{n:,} {word}{"" if n == 1 else "s"}'


# ---------------------------------------------------------------- svg helpers

def text(x, y, value, size=16, color='fg', extra=''):
    return f'<text x="{x}" y="{y}" class="{color}" font-size="{size}" {extra}>{escape(str(value))}</text>'


def line(x1, y1, x2, y2, extra=''):
    d = f'M{x1} {y1}H{x2}' if y1 == y2 else f'M{x1} {y1}L{x2} {y2}'
    return f'<path d="{d}" class="rule" {extra}/>'


def svg(body, theme, height, title, desc, defs=''):
    t = THEMES[theme]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {height}" width="1200" height="{height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>
<defs>{defs}</defs>
<style>
text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }}
.fg {{fill:{t['fg']}}} .muted {{fill:{t['muted']}}} .blue {{fill:{t['blue']}}} .gold {{fill:{t['gold']}}}
.mono {{font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;letter-spacing:1.2px}}
.rule {{fill:none;stroke:{t['line']};stroke-width:1}}
.trace {{fill:none;stroke:{t['gold']};stroke-width:2;stroke-linejoin:round;stroke-linecap:round;stroke-dasharray:1 1;animation:draw 1.8s ease-out backwards}}
.sweep {{fill:none;stroke:{t['gold']};stroke-width:2;stroke-linejoin:round;stroke-linecap:round;stroke-dasharray:1 1;animation:draw 1.8s ease-out backwards}}
.reveal {{animation:arrive .55s ease-out backwards}}
.led {{animation:blink 2.6s ease-in-out infinite}}
@keyframes draw {{from {{stroke-dashoffset:1;opacity:0}} to {{stroke-dashoffset:0;opacity:1}}}}
@keyframes arrive {{from {{opacity:0;transform:translateY(5px)}} to {{opacity:1;transform:translateY(0)}}}}
@keyframes blink {{0%,100% {{opacity:1}} 50% {{opacity:.25}}}}
@media (prefers-reduced-motion:reduce) {{.trace,.reveal,.sweep,.led {{animation:none!important}}}}
</style>
<rect x=".5" y=".5" width="1199" height="{height - 1}" rx="12" fill="{t['bg']}" stroke="{t['line']}"/>
{body}
</svg>\n'''


# ---------------------------------------------------------------- hero

def hero(theme):
    t = THEMES[theme]
    b = text(44, 142, 'Aman', 124, 'fg', 'font-weight="700" letter-spacing="-5"')
    b += text(44, 254, 'Sanoj.', 124, 'fg', 'font-weight="700" letter-spacing="-5"')
    b += text(48, 314, 'Software, down to the pins.', 26, 'blue', 'letter-spacing="-.4"')
    b += text(48, 350, 'Web apps. Terminal interfaces. Connected hardware.', 18, 'muted')

    # Three equal cards on one grid, joined by a single signal bus on the left.
    # Original vector drawing: no JavaScript, no external image requests.
    cx, cw, ch, gap, top = 792, 360, 84, 30, 60
    ys = [top + i * (ch + gap) for i in range(3)]
    mid = [y + ch // 2 for y in ys]
    bus = cx - 30

    b += f'<path d="M{cx} {mid[0]}H{bus}V{mid[2]}H{cx}" pathLength="1" class="trace"/>'
    b += f'<path d="M{bus} {mid[1]}H{cx}" pathLength="1" class="trace" style="animation-delay:.9s"/>'
    b += f'<circle cx="{bus}" cy="{mid[1]}" r="3.5" fill="{t["gold"]}" class="reveal" style="animation-delay:.9s"/>'

    cards = [
        ('01 / WEB', 'interface', 'view → event → request'),
        ('02 / TUI', 'logic', 'input → state → output'),
        ('03 / HARDWARE', 'ESP32', 'pin → signal → light'),
    ]
    for i, (idx, title, sub) in enumerate(cards):
        y = ys[i]
        chip = i == 2
        b += f'<g class="reveal" style="animation-delay:{.1 + i * .3:.2f}s">'
        if chip:  # DIP-style pins on top and bottom edges
            for px in range(cx + 20, cx + cw - 10, 20):
                b += f'<path d="M{px} {y - 7}v7M{px} {y + ch}v7" stroke="{t["blue"]}" stroke-width="2.5"/>'
        b += f'<rect x="{cx}" y="{y}" width="{cw}" height="{ch}" rx="{5 if chip else 8}" fill="{t["panel"]}" stroke="{t["blue"] if chip else t["line"]}"/>'
        b += text(cx + 22, y + 28, idx, 11, 'muted', 'letter-spacing="1.2"')
        b += text(cx + 22, y + 53, title, 21, 'blue', 'font-weight="600" letter-spacing="1"' if chip else 'font-weight="600"')
        b += text(cx + 22, y + 75, sub, 13, 'muted')
        if i == 0:  # window chrome
            for k in range(3):
                b += f'<circle cx="{cx + cw - 56 + k * 14}" cy="{y + 24}" r="3" fill="{t["muted"]}" opacity=".6"/>'
        elif i == 1:  # prompt
            b += text(cx + cw - 22, y + 30, '>_', 16, 'gold mono', 'text-anchor="end" font-weight="700"')
        else:  # status LED
            b += f'<circle cx="{cx + cw - 26}" cy="{y + 24}" r="4" fill="{t["gold"]}" class="led"/>'
        b += '</g>'

    return svg(b, theme, 440, 'Aman Sanoj — software, down to the pins.',
               'Developer in Dubai, UAE. Web apps, terminal interfaces, and connected hardware. '
               'A browser, terminal, and ESP32 joined by an animated signal bus.')


# ---------------------------------------------------------------- activity

def activity(snapshot, theme):
    t = THEMES[theme]
    days = snapshot['days']
    total = sum(d['count'] for d in days)
    active = sum(d['count'] > 0 for d in days)
    streak = longest_streak(days)
    first = date.fromisoformat(days[0]['date'])
    last = date.fromisoformat(days[-1]['date'])
    sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    n_weeks = (last - sunday).days // 7 + 1
    busiest = max(days, key=lambda d: d['count'])

    # Grid geometry: square cells on a shared pitch, with a gutter for weekday labels.
    x0, x1, top = 84, 1152, 226
    pitch = (x1 - x0) / n_weeks
    cell = min(17, pitch - 4)
    grid_bottom = top + 6 * pitch + cell

    # Header: title left, three stats right.
    b = text(48, 70, 'A year at the workbench.', 30, 'fg', 'font-weight="600" letter-spacing="-.7"')
    b += text(48, 96, 'Public GitHub contributions, one square per day.', 14, 'muted')
    stats = [(1152, f'{total:,}', 'Contributions', 44, 'blue'),
             (968, f'{active}', 'Active days', 30, 'fg'),
             (812, f'{streak}', 'Best streak (days)', 30, 'fg')]
    for x, value, label, size, color in stats:
        b += text(x, 70, value, size, color, 'text-anchor="end" font-weight="600" letter-spacing="-1"')
        b += text(x, 94, label, 12, 'muted', 'text-anchor="end"')

    # Weekly totals sparkline, aligned to the grid columns.
    weeks = [0] * n_weeks
    for d in days:
        weeks[((date.fromisoformat(d['date']) - sunday).days) // 7] += d['count']
    peak = max(weeks) or 1
    peak_i = weeks.index(max(weeks))
    base, height = 190, 46
    pts = [(x0 + i * pitch + cell / 2, base - n / peak * height) for i, n in enumerate(weeks)]
    path = 'M' + ' L'.join(f'{x:.2f} {y:.2f}' for x, y in pts)
    area = f'{path} L{pts[-1][0]:.2f} {base} L{pts[0][0]:.2f} {base} Z'
    b += line(x0, base, x1, base)
    b += f'<path d="{area}" fill="url(#fade)" class="reveal" style="animation-delay:.4s"/>'
    b += f'<path d="{path}" pathLength="1" class="sweep"/>'
    px, py = pts[peak_i]
    b += f'<circle cx="{px:.2f}" cy="{py:.2f}" r="3.5" fill="{t["gold"]}" stroke="{t["bg"]}" stroke-width="2"/>'
    anchor_x = min(max(px, x0 + 90), x1 - 90)
    b += text(f'{anchor_x:.2f}', f'{py - 12:.2f}', f'Peak week: {peak:,}', 12, 'muted', 'text-anchor="middle"')
    # Caption goes on whichever side the peak is not.
    if px < (x0 + x1) / 2:
        b += text(x1, 134, 'Weekly totals', 12, 'muted', 'text-anchor="end"')
    else:
        b += text(x0, 134, 'Weekly totals', 12, 'muted')

    # Month labels (first full week of each month) and weekday labels.
    previous = -99
    for i in range(n_weeks):
        start = sunday + timedelta(weeks=i)
        if start.day <= 7 and i - previous > 2 and i < n_weeks - 1:
            b += text(f'{x0 + i * pitch:.2f}', top - 12, start.strftime('%b'), 12, 'muted')
            previous = i
    for row, name in ((1, 'Mon'), (3, 'Wed'), (5, 'Fri')):
        b += text(48, f'{top + row * pitch + cell / 2 + 4:.2f}', name, 12, 'muted')

    # Heatmap.
    for d in days:
        day = date.fromisoformat(d['date'])
        col, row = divmod((day - sunday).days, 7)
        x, y = x0 + col * pitch, top + row * pitch
        ring = f' stroke="{t["gold"]}" stroke-width="1.5"' if d is busiest and d['count'] else ''
        tip = f'{pretty(day)}: {plural(d["count"], "contribution")}'
        b += (f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell:.2f}" height="{cell:.2f}" rx="3" '
              f'fill="{t["ramp"][d["level"]]}"{ring} class="reveal" '
              f'style="animation-delay:{col * .015 + row * .025:.3f}s"><title>{escape(tip)}</title></rect>')

    # Footer: provenance left, legend right.
    fy = grid_bottom + 34
    b += line(48, fy - 26, x1, fy - 26)
    b += text(48, fy, f'{pretty(first)} to {pretty(last)}  ·  updated {snapshot["snapshot_date"]}', 12, 'muted')
    b += text(x1, fy, 'More', 12, 'muted', 'text-anchor="end"')
    for i, color in enumerate(t['ramp']):
        b += f'<rect x="{x1 - 46 - (5 - i) * 17:.0f}" y="{fy - 11}" width="12" height="12" rx="3" fill="{color}"/>'
    b += text(x1 - 46 - 5 * 17 - 6, fy, 'Less', 12, 'muted', 'text-anchor="end"')

    height_total = int(fy + 28)
    defs = (f'<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{t["gold"]}" stop-opacity=".28"/>'
            f'<stop offset="1" stop-color="{t["gold"]}" stop-opacity="0"/></linearGradient>')
    desc = (f'{total:,} contributions across {active} active days, from {pretty(first)} through {pretty(last)}. '
            f'Longest streak {streak} days. Busiest day {pretty(date.fromisoformat(busiest["date"]))} '
            f'with {busiest["count"]}. Weekly totals are drawn above the calendar. '
            f'Snapshot {snapshot["snapshot_date"]}.')
    return svg(b, theme, height_total, 'A year at the workbench — public GitHub activity', desc, defs)


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true')
    parser.add_argument('--html', type=Path, help='Parse a saved public calendar HTML file')
    args = parser.parse_args()
    target = ROOT / 'data/contributions.json'
    if args.html:
        snapshot = {'username': USER, 'source': f'https://github.com/users/{USER}/contributions',
                    'snapshot_date': datetime.now(timezone.utc).date().isoformat(),
                    'days': parse_calendar(args.html.read_text())}
    elif args.fetch:
        snapshot = fetch_snapshot()
    else:
        snapshot = json.loads(target.read_text())
    validate_days(snapshot['days'])
    # Render everything before writing: a parsing/rendering failure preserves the last good artwork.
    output = {}
    for theme in THEMES:
        output[f'hero-{theme}.svg'] = hero(theme)
        output[f'activity-{theme}.svg'] = activity(snapshot, theme)
    (ROOT / 'assets').mkdir(exist_ok=True)
    target.parent.mkdir(exist_ok=True)
    for name, content in output.items():
        path = ROOT / 'assets' / name
        path.with_suffix('.tmp').write_text(content)
        path.with_suffix('.tmp').replace(path)
    target.with_suffix('.tmp').write_text(json.dumps(snapshot, indent=2) + '\n')
    target.with_suffix('.tmp').replace(target)
    print(f'Rendered {len(output)} SVGs from {len(snapshot["days"])} verified days; {sum(d["count"] for d in snapshot["days"]):,} contributions.')


if __name__ == '__main__':
    main()
