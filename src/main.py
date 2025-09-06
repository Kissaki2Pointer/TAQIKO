#!/usr/bin/env python3

from logger import slog
from datetime import datetime
from keiko.bet import web_login

def main():
    slog("START", "TAQIKOを起動します。")
    
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    current_weekday = weekdays[datetime.now().weekday()]
    
    slog("INFO", f"今日は{current_weekday}曜日です。")
    
    if current_weekday in ["土", "日"]:
        slog("INFO", "競馬自動投票ツールを実行します。")
        web_login()
    else:
        slog("INFO", "株自動売買ツールを実行します")

    slog("END", "TAQIKOを終了します。")

if __name__ == "__main__":
    main()