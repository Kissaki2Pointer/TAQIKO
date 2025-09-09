#!/usr/bin/env python3

from logger import slog
from datetime import datetime
from keiko.bet import web_login,payment,purchase
from taq.token_store import get_token

def main():
    slog("START", "TAQIKOを起動します。")
    
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    current_weekday = weekdays[datetime.now().weekday()]
    
    slog("INFO", f"今日は{current_weekday}曜日です。")
    
    if current_weekday in ["土", "日"]:
        slog("INFO", "競馬自動投票ツールを実行します。")
        # JRA WEBログイン
        ret = web_login()
        if ret == True:
            # 入金処理
            ret = payment()
            if ret == True:
                ret = purchase(current_weekday)
    else:
        slog("INFO", "株自動売買ツールを実行します。")
        # トークン取得
        ret = get_token()
        if ret:
            slog("INFO", "トークン取得に成功しました。")
        else:
            slog("ERROR", "トークン取得に失敗しました。")

    slog("END", "TAQIKOを終了します。")

if __name__ == "__main__":
    main()