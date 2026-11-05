import json, re, os
from datetime import datetime, timezone
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

SOURCE_URL = 'https://xn--j1afhm.xn--p1ai/raspisanie-zanyatiy/raspisanie-nemirovicha/www/cg38.htm'
GROUP = 'МТ-24/9'
OUT = 'schedule.json'
DAYS = ['Понедельник','Вторник','Среда','Четверг','Пятница','Суббота','Воскресенье']

def clean(s):
    return re.sub(r'\s+', ' ', s or '').strip()

def main():
    response = requests.get(SOURCE_URL, timeout=30, headers={'User-Agent':'Mozilla/5.0 (compatible; MT249ScheduleBot/1.0)'})
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    soup = BeautifulSoup(response.text, 'html.parser')
    text = clean(soup.get_text(' ', strip=True))
    # Locate a table or section mentioning the requested group; otherwise use the page's tables.
    tables = soup.find_all('table')
    group_tables = [t for t in tables if GROUP.lower() in clean(t.get_text(' ', strip=True)).lower()]
    candidates = group_tables or tables
    rows = []
    for table in candidates:
        for tr in table.find_all('tr'):
            cells = [clean(c.get_text(' ', strip=True)) for c in tr.find_all(['th','td'])]
            cells = [c for c in cells if c]
            if cells:
                rows.append(cells)
    # Normalize table rows into seven weekday buckets. Source layouts vary, so preserve row text.
    days = [{'name': name, 'lessons': []} for name in DAYS]
    day_index = 0
    for cells in rows:
        line = ' | '.join(cells)
        low = line.lower()
        found = next((i for i,n in enumerate(DAYS) if n.lower() in low), None)
        if found is not None:
            day_index = found
            # Header-only row: skip if it contains just the weekday label.
            if len(cells) == 1 or all(c.lower() in [DAYS[found].lower(), DAYS[found][:2].lower()] for c in cells):
                continue
        # Skip unrelated tables when no matching group table was found and group is not on page.
        if not group_tables and GROUP.lower() not in text.lower():
            continue
        if len(cells) == 1 and len(cells[0]) < 3:
            continue
        # Common schedule cells: time, subject, teacher/room. Keep all data without guessing.
        time = cells[0] if re.search(r'\d{1,2}[:.]?\d{2}', cells[0]) else ''
        subject = cells[1] if len(cells) > 1 else cells[0]
        teacher = cells[2] if len(cells) > 2 else ''
        room = cells[3] if len(cells) > 3 else ''
        days[day_index]['lessons'].append({'time':time,'subject':subject,'teacher':teacher,'room':room,'text':line})
    # If the source has no tables, preserve readable page text as a fallback notice.
    total = sum(len(d['lessons']) for d in days)
    result = {'group':GROUP,'source':SOURCE_URL,'updated':datetime.now(timezone.utc).isoformat(),'days':days}
    if total == 0:
        result['message'] = 'Источник открылся, но структура расписания не распознана автоматически. Проверьте Actions; парсер может потребовать настройки под страницу колледжа.'
    with open(OUT,'w',encoding='utf-8') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
    print(f'Wrote {OUT}; rows={total}; matching_tables={len(group_tables)}')

if __name__ == '__main__':
    main()
