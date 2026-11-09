import importlib.util
from datetime import date, timedelta
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('profile', ROOT / 'scripts/build_profile.py')
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)


def fixture():
    parts = []
    for i in range(365):
        day = date(2025, 1, 1) + timedelta(days=i)
        count = '1,234 contributions' if i == 100 else 'No contributions'
        level = 4 if i == 100 else 0
        parts.append(f'<td id="d{i}" data-date="{day}" data-level="{level}"></td>'
                     f'<tool-tip for="d{i}">{count} on some date.</tool-tip>')
    return ''.join(reversed(parts))


class ProfileTests(unittest.TestCase):
    def test_parses_and_sorts_counts(self):
        days = profile.parse_calendar(fixture())
        self.assertEqual(days[0]['date'], '2025-01-01')
        self.assertEqual(days[100]['count'], 1234)
        self.assertEqual(sum(d['count'] for d in days), 1234)

    def test_rejects_missing_tooltips(self):
        with self.assertRaises(ValueError):
            profile.parse_calendar(fixture().replace('for="d5"', 'for="missing"'))

    def test_rejects_truncated_response(self):
        with self.assertRaises(ValueError):
            profile.parse_calendar('<html>Rate limit exceeded</html>')

    def test_rejects_date_gaps(self):
        days = profile.parse_calendar(fixture())
        days.pop(100)
        with self.assertRaises(ValueError):
            profile.validate_days(days)

    def test_rejects_inconsistent_levels(self):
        days = profile.parse_calendar(fixture())
        days[1]['level'] = 4
        with self.assertRaises(ValueError):
            profile.validate_days(days)

    def test_mobile_calendar_preserves_annual_stats_and_recent_dates(self):
        days = profile.parse_calendar(fixture())
        snapshot = {'days': days, 'snapshot_date': '2025-12-31'}
        last = date.fromisoformat(days[-1]['date'])
        cutoff = last - timedelta(days=(last.weekday() + 1) % 7, weeks=25)
        expected = [d for d in days if date.fromisoformat(d['date']) >= cutoff]
        for theme in profile.THEMES:
            root = ET.fromstring(profile.activity(snapshot, theme, mobile=True))
            ns = {'s': 'http://www.w3.org/2000/svg'}
            cells = root.findall('.//s:rect[s:title]', ns)
            self.assertEqual(root.attrib['width'], '600')
            self.assertEqual(len(cells), len(expected))
            self.assertEqual([cell.find('s:title', ns).text for cell in cells],
                             [f"{profile.pretty(date.fromisoformat(d['date']))}: "
                              f"{profile.plural(d['count'], 'contribution')}" for d in expected])
            labels = [node.text for node in root.findall('s:text', ns)]
            self.assertIn('1,234', labels)  # Annual activity predates the mobile window.
            self.assertIn('Recent 26 Weeks · Weekly Totals', labels)
            for cell in cells:
                self.assertGreaterEqual(float(cell.attrib['x']), 0)
                self.assertLessEqual(float(cell.attrib['x']) + float(cell.attrib['width']), 600)

    def test_zero_activity_and_svg_safety(self):
        days = profile.parse_calendar(fixture())
        for day in days:
            day.update(count=0, level=0)
        snapshot = {'days': days, 'snapshot_date': '2025-12-31'}
        for theme in profile.THEMES:
            for source in [profile.hero(theme), profile.hero(theme, mobile=True), profile.activity(snapshot, theme),
                           profile.activity(snapshot, theme, mobile=True)]:
                root = ET.fromstring(source)
                self.assertIn(root.attrib['width'], ('600', '1200'))
                self.assertIn('prefers-reduced-motion', source)
                for element in root.iter():
                    self.assertNotIn(element.tag.split('}')[-1], ['script', 'foreignObject', 'image'])
                    self.assertFalse(any(k.startswith('on') for k in element.attrib))


if __name__ == '__main__':
    unittest.main()
