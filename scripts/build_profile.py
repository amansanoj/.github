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
    'dark': dict(bg='#050505', fg='#e6e6e6', muted='#999999', line='#292929',
                 panel='#101113', blue='#afbdd9', gold='#f0a133',
                 ramp=['#202329', '#314368', '#5270ad', '#97a9ce', '#afbdd9']),
    'light': dict(bg='#fafafa', fg='#1a1a1a', muted='#666666', line='#dddddd',
                  panel='#f0f1f3', blue='#263450', gold='#9b5c0a',
                  ramp=['#e5e7eb', '#bac6de', '#748dbe', '#415a8b', '#263450']),
}


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


def text(x, y, value, size=16, color='fg', extra=''):
    return f'<text x="{x}" y="{y}" class="{color}" font-size="{size}" {extra}>{escape(str(value))}</text>'


def line(x1, y1, x2, y2, extra=''):
    return f'<path d="M{x1} {y1}H{x2}" class="rule" {extra}/>' if y1 == y2 else f'<path d="M{x1} {y1}L{x2} {y2}" class="rule" {extra}/>'


def svg(body, theme, height, title, desc):
    t = THEMES[theme]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {height}" width="1200" height="{height}" role="img" aria-labelledby="title desc">
<title id="title">{escape(title)}</title><desc id="desc">{escape(desc)}</desc>
<style>
text {{ font-family: Arial, Helvetica, sans-serif; }}
.fg {{fill:{t['fg']}}} .muted {{fill:{t['muted']}}} .blue {{fill:{t['blue']}}} .gold {{fill:{t['gold']}}}
.mono {{font-family:ui-monospace, SFMono-Regular, Consolas, monospace;letter-spacing:1.2px}}
.rule {{fill:none;stroke:{t['line']};stroke-width:1}}
.trace {{fill:none;stroke:{t['gold']};stroke-width:2;stroke-linejoin:round;stroke-linecap:round;stroke-dasharray:1000;animation:draw 2.2s ease-out backwards}}
.reveal {{animation:arrive .55s ease-out backwards}}
.sweep {{fill:none;stroke:{t['gold']};stroke-width:2;stroke-linejoin:round;stroke-dasharray:2000;animation:draw 2s ease-out backwards}}
@keyframes draw {{from {{stroke-dashoffset:2000;opacity:0}} to {{stroke-dashoffset:0;opacity:1}}}}
@keyframes arrive {{from {{opacity:0;transform:translateY(5px)}} to {{opacity:1;transform:translateY(0)}}}}
@media (prefers-reduced-motion:reduce) {{.trace,.reveal,.sweep {{animation:none!important}}}}
</style>
<rect width="1200" height="{height}" rx="12" fill="{t['bg']}"/>
{body}
</svg>\n'''


def hero(theme):
    t = THEMES[theme]
    b = text(48, 44, 'AMANSANOJ / PERSONAL WORK', 13, 'muted mono')
    b += text(1152, 44, 'DUBAI, UAE', 13, 'muted', 'text-anchor="end" letter-spacing="1.5"')
    b += line(48, 64, 1152, 64)
    b += text(42, 185, 'Aman', 124, 'fg', 'font-weight="700" letter-spacing="-7"')
    b += text(42, 299, 'Sanoj.', 124, 'fg', 'font-weight="700" letter-spacing="-7"')
    b += text(48, 359, 'Software, down to the pins.', 26, 'blue', 'letter-spacing="-.5"')
    b += text(48, 394, 'Web apps. Terminal interfaces. Connected hardware.', 18, 'muted')

    # Original vector drawing: a browser, terminal, and physical controller
    # connected by two traces. No JavaScript or external image requests.
    b += f'<g class="reveal" style="animation-delay:.1s"><rect x="778" y="100" width="332" height="83" rx="8" fill="{t["panel"]}" stroke="{t["line"]}"/>'
    for x in [795, 807, 819]:
        b += f'<circle cx="{x}" cy="115" r="2" fill="{t["muted"]}"/>'
    b += line(778, 129, 1110, 129)
    b += text(795, 161, 'interface', 19, 'blue')
    b += text(1093, 160, '01 / WEB', 11, 'muted', 'text-anchor="end" letter-spacing="1"') + '</g>'
    b += '<path d="M814 183V202H738V253H778" class="trace"/>'
    b += f'<g class="reveal" style="animation-delay:.35s"><rect x="778" y="215" width="332" height="82" rx="8" fill="{t["panel"]}" stroke="{t["line"]}"/>'
    b += text(795, 248, '>_', 22, 'gold')
    b += text(840, 248, 'logic', 19, 'blue')
    b += text(1093, 247, '02 / TUI', 11, 'muted', 'text-anchor="end" letter-spacing="1"')
    b += text(795, 278, 'input → state → output', 15, 'muted') + '</g>'
    b += '<path d="M1074 297V318H1140V374H1079" class="trace" style="animation-delay:.25s"/>'
    b += f'<g class="reveal" style="animation-delay:.6s"><rect x="814" y="335" width="265" height="81" rx="5" fill="{t["panel"]}" stroke="{t["blue"]}"/>'
    for x in range(832, 1070, 19):
        b += f'<path d="M{x} 328v7M{x} 416v7" stroke="{t["blue"]}" stroke-width="3"/>'
    b += text(838, 369, 'ESP32', 21, 'blue', 'font-weight="600" letter-spacing="2"')
    b += text(838, 393, '03 / HARDWARE', 11, 'muted', 'letter-spacing="1"')
    b += f'<circle cx="1054" cy="354" r="4" fill="{t["gold"]}"/>'
    b += '</g>'
    b += line(48, 452, 1152, 452)
    b += text(48, 481, 'TYPESCRIPT / GO / PYTHON / C++', 12, 'muted', 'letter-spacing="1.5"')
    b += text(1152, 481, 'FROM THE BROWSER TO THE BREADBOARD', 12, 'muted', 'text-anchor="end" letter-spacing="1"')
    return svg(b, theme, 508, 'Aman Sanoj — software, down to the pins.', 'Developer in Dubai, UAE. Web apps, terminal interfaces, and connected hardware. A browser, terminal, and ESP32 connected by animated traces.')


def activity(snapshot, theme):
    t = THEMES[theme]
    days = snapshot['days']
    total = sum(d['count'] for d in days)
    active = sum(d['count'] > 0 for d in days)
    first = date.fromisoformat(days[0]['date'])
    sunday = first - timedelta(days=(first.weekday() + 1) % 7)
    n_weeks = ((date.fromisoformat(days[-1]['date']) - sunday).days // 7) + 1
    step = 1104 / n_weeks
    size = min(15, step - 4)
    weeks = [0] * n_weeks
    b = text(48, 43, 'THE WORK LOG', 12, 'muted', 'letter-spacing="2"')
    b += text(48, 82, 'A year at the workbench.', 29, 'fg', 'font-weight="600" letter-spacing="-.7"')
    b += text(1152, 65, f'{total:,}', 42, 'blue', 'text-anchor="end" font-weight="600" letter-spacing="-1"')
    b += text(1152, 88, f'CONTRIBUTIONS / {active} ACTIVE DAYS', 11, 'muted', 'text-anchor="end" letter-spacing="1"')
    for d in days:
        offset = (date.fromisoformat(d['date']) - sunday).days
        col, row = divmod(offset, 7)
        weeks[col] += d['count']
        x, y = 48 + col * step, 190 + row * 20
        b += f'<rect x="{x:.2f}" y="{y}" width="{size:.2f}" height="15" rx="2.5" fill="{t["ramp"][d["level"]]}" class="reveal" style="animation-delay:{col*.015+row*.025:.3f}s"><title>{d["date"]}: {d["count"]} contributions</title></rect>'
    peak = max(weeks) or 1
    pts = [(48 + i * step + size/2, 158 - n/peak * 38) for i, n in enumerate(weeks)]
    path = 'M' + ' L'.join(f'{x:.2f} {y:.2f}' for x, y in pts)
    b += line(48, 161, 1152, 161)
    b += f'<path d="{path}" class="sweep"/>'
    b += text(48, 111, 'WEEKLY TOTALS', 9, 'muted', 'letter-spacing="1.4"')
    previous_label = -99
    for i in range(n_weeks):
        start = sunday + timedelta(weeks=i)
        # Label the first complete week of each month, avoiding edge collisions.
        if start.day <= 7 and i - previous_label > 2 and i < n_weeks - 1:
            b += text(round(48+i*step, 2), 180, start.strftime('%b'), 10, 'muted')
            previous_label = i
    b += text(1009, 341, 'LESS', 8, 'muted', 'text-anchor="end"')
    for i, color in enumerate(t['ramp']):
        b += f'<rect x="{1018+i*16}" y="333" width="11" height="9" rx="2" fill="{color}"/>'
    b += text(1102, 341, 'MORE', 8, 'muted')
    b += line(48, 349, 1152, 349)
    b += text(48, 376, f'{days[0]["date"]} — {days[-1]["date"]}  /  PUBLIC GITHUB CALENDAR', 11, 'muted', 'letter-spacing=".5"')
    b += text(1152, 376, f'UPDATED {snapshot["snapshot_date"]}', 11, 'muted', 'text-anchor="end" letter-spacing=".5"')
    desc = f'{total:,} contributions across {active} active days, from {days[0]["date"]} through {days[-1]["date"]}. Weekly totals are drawn above the calendar. Darker blue in light mode and lighter blue in dark mode indicate higher daily activity. Snapshot {snapshot["snapshot_date"]}.'
    return svg(b, theme, 404, 'A year at the workbench — public GitHub activity', desc)


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
