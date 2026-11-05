
import json
import re
import socket
from datetime import datetime, timezone

import requests
import urllib3.util.connection
from bs4 import BeautifulSoup

# Используем IPv4 для подключения к сайту
urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET

SOURCE_URL = (
    "https://xn--j1afhm.xn--p1ai/"
    "raspisanie-zanyatiy/raspisanie-nemirovicha/www/cg38.htm"
)

GROUP = "МТ-24/9"
OUT = "schedule.json"
HTML_OUT = "source.html"

DAYS = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье"
]


def clean(value):
    return re.sub(r"\s+", " ", value or "").strip()


def main():
    print("Загружаем расписание...")

    response = requests.get(
        SOURCE_URL,
        timeout=60,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()

    # Сохраняем оригинальную HTML-страницу
    with open(HTML_OUT, "w", encoding="utf-8") as file:
        file.write(response.text)

    response.encoding = (
        response.apparent_encoding or response.encoding
    )

    soup = BeautifulSoup(response.text, "html.parser")

    tables = soup.find_all("table")

    group_tables = [
        table for table in tables
        if GROUP.lower() in clean(
            table.get_text(" ", strip=True)
        ).lower()
    ]

    candidates = group_tables or tables

    days = [
        {"name": day, "lessons": []}
        for day in DAYS
    ]

    total = 0

    for table in candidates:
        for row in table.find_all("tr"):
            cells = [
                clean(cell.get_text(" ", strip=True))
                for cell in row.find_all(["td", "th"])
            ]

            cells = [cell for cell in cells if cell]

            if not cells:
                continue

            line = " | ".join(cells)

            # Определяем день по русскому названию или сокращению
            day_match = re.search(
                r"\b(пн|вт|ср|чт|пт|сб|вс)\b",
                line.lower()
            )

            if day_match:
                abbreviations = {
                    "пн": 0,
                    "вт": 1,
                    "ср": 2,
                    "чт": 3,
                    "пт": 4,
                    "сб": 5,
                    "вс": 6
                }
                day_index = abbreviations[day_match.group(1)]
            else:
                day_index = 0

            # Сохраняем строку целиком, не теряя данные
            days[day_index]["lessons"].append({
                "time": "",
                "subject": line,
                "teacher": "",
                "room": "",
                "text": line
            })

            total += 1

    result = {
        "group": GROUP,
        "source": SOURCE_URL,
        "updated": datetime.now(timezone.utc).isoformat(),
        "days": days
    }

    if total == 0:
        result["message"] = (
            "Не удалось распознать таблицу расписания."
        )

    with open(OUT, "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"Расписание сохранено. Строк: {total}")
    print(f"Найдено таблиц группы: {len(group_tables)}")

    if total == 0:
        raise RuntimeError("Расписание не найдено")


if __name__ == "__main__":
    main()
