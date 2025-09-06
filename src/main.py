#!/usr/bin/env python3

from logger import slog
from datetime import datetime

def main():
    slog("START", "TAQIKOを起動します。")
    
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    current_weekday = weekdays[datetime.now().weekday()]
    
    slog("INFO", f"今日は{current_weekday}曜日です。")

    slog("END", "TAQIKOを終了します。")

if __name__ == "__main__":
    main()