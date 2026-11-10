"""Copy only public calendar text; never execute or republish source HTML."""
import argparse
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = 'https://lich.hatinh.gov.vn/halinh/plugin_working/show_calendar_week'

class CalendarParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.rows = []
        self.row = None
        self.cell = None
        self.skip = 0
        self.found = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'table':
            if self.depth:
                self.depth += 1
            elif 'daily-schedule-table' in attrs.get('class', '').split():
                self.depth = 1
                self.found = True
        if not self.depth:
            return
        if tag in ('script', 'style'):
            self.skip += 1
        if self.depth == 1 and not self.skip:
            if tag == 'tr':
                self.row = []
            elif tag in ('td', 'th'):
                if attrs.get('rowspan', '1') != '1' or attrs.get('colspan', '1') != '1':
                    raise ValueError('Unexpected merged calendar cells; retain previous data')
                self.cell = []
            elif tag in ('br', 'div', 'p') and self.cell is not None:
                self.cell.append(' ')

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag in ('script', 'style'):
            self.skip = max(0, self.skip - 1)
        if self.depth == 1 and not self.skip:
            if tag in ('td', 'th') and self.cell is not None:
                if self.row is not None:
                    self.row.append(' '.join(''.join(self.cell).split()))
                self.cell = None
            elif tag == 'tr' and self.row is not None:
                self.rows.append(self.row)
                self.row = None
            elif tag in ('div', 'p') and self.cell is not None:
                self.cell.append(' ')
        if tag == 'table':
            self.depth -= 1

    def handle_data(self, data):
        if self.depth == 1 and not self.skip and self.cell is not None:
            self.cell.append(data)

def parse_calendar(html):
    if not re.search(r'HÀ\s+LINH', html, re.I):
        raise ValueError('Source is not the Ha Linh calendar')
    parser = CalendarParser()
    parser.feed(html)
    if not parser.found or not parser.rows or parser.rows[0][:3] != ['Ngày bắt đầu', 'Giờ bắt đầu', 'Nội dung']:
        raise ValueError('Calendar structure changed; retain previous data')
    events = []
    for row in parser.rows[1:]:
        if len(row) != 8:
            raise ValueError('Incomplete calendar row')
        match = re.search(r'\b(\d{2}/\d{2}/\d{4})\b', row[0])
        if not match or not row[2]:
            raise ValueError('Invalid event date or content')
        date = datetime.strptime(match[1], '%d/%m/%Y').date().isoformat()
        events.append(dict(zip(['date', 'time', 'content', 'chair', 'participants', 'location', 'transport'], [date] + row[1:7])))
    # A sudden empty response must not erase the last successful calendar.
    if not events:
        raise ValueError('No events returned; retain previous data')
    return sorted(events, key=lambda event: (event['date'], event['time']))

def main():
    cli = argparse.ArgumentParser()
    cli.add_argument('--input', type=Path)
    cli.add_argument('--output', type=Path, default=Path('calendar.json'))
    args = cli.parse_args()
    if args.input:
        html = args.input.read_text(encoding='utf-8')
    else:
        request = Request(SOURCE, headers={'User-Agent': 'HaLinh-PublicCalendar/1.0', 'Accept': 'text/html'})
        with urlopen(request, timeout=45) as response:
            if response.status != 200:
                raise ValueError('Calendar source unavailable')
            html = response.read(5_000_001).decode('utf-8')
            if len(html) > 5_000_000:
                raise ValueError('Calendar response too large')
    events = parse_calendar(html)
    data = {'source': SOURCE, 'updatedAt': datetime.now(timezone.utc).isoformat(), 'events': events}
    temp = args.output.with_suffix('.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(args.output)
    print(f'Updated {len(events)} public events')

if __name__ == '__main__':
    main()