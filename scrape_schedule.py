
import json
import re
import socket
from datetime import datetime, timezone

import requests
import urllib3.util.connection
from bs4 import BeautifulSoup

# Принудительно используем IPv4
urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET

SOURCE_URL = (
    'https://xn--j1afhm.xn--p1ai/'
    'raspisanie-zanyatiy/raspisanie-nemirovicha/www/cg38.htm'
)

GROUP = 'МТ-24/9'
OUT = 'schedule.json'

DAYS = [
    'Понедельник', 'Вторник', 'Среда',
    'Четверг', 'Пятница', 'Суббота',
    'Воскресенье'
]


def clean(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def main():
    response = requests.get(
        SOURCE_URL,
        timeout=40,
        headers={
            'User-Agent': 'Mozilla/5.0'
        }
    )

    response.raise_for_status()
    with open('source.html', 'w', encoding='utf-8') as f:
    f.write(response.text)
    response.encoding = response.apparent_encoding or response.encoding

    soup = BeautifulSoup(response.text, 'html.parser')

    tables = soup.find_all('table')

    group_tables = [
        table for table in tables
        if GROUP.lower() in clean(
            table.get_text(' ', strip=True)
        ).lower()
    ]

    candidates = group_tables or tables

    days = [
        {'name': name, 'lessons': []}
        for name in DAYS
    ]

    day_index = 0
    total = 0

    for table in candidates:
        for tr in table.find_all('tr'):
            cells = [
                clean(cell.get_text(' ', strip=True))
                for cell in tr.find_all(['th', 'td'])
            ]

            cells = [cell for cell in cells if cell]

            if not cells:
                continue

            line = ' | '.join(cells)

            for i, name in enumerate(DAYS):
                if name.lower() in line.lower():
                    day_index = i

            if len(cells) == 1 and len(cells[0]) < 3:
                continue

            time = ''
            subject = cells[0]
            teacher = ''
            room = ''

            for cell in cells:
                if re.search(r'\d{1,2}[:.]\d{2}', cell):
                    time = cell

            if len(cells) > 1:
                subject = cells[1]
            if len(cells) > 2:
                teacher = cells[2]
            if len(cells) > 3:
                room = cells[3]

            days[day_index]['lessons'].append({
                'time': time,
                'subject': subject,
                'teacher': teacher,
                'room': room,
                'text': line
            })

            total += 1

    result = {
        'group': GROUP,
        'source': SOURCE_URL,
        'updated': datetime.now(timezone.utc).isoformat(),
        'days': days
    }

    if total == 0:
        result['message'] = (
            'Расписание не удалось распознать.'
        )

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(
        f'Wrote {OUT}; rows={total}; '
        f'matching_tables={len(group_tables)}'
    )

    if total == 0:
        raise RuntimeError('Расписание не найдено')


if __name__ == '__main__':
    main()
