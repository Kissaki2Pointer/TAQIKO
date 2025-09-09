#!/usr/bin/env python3

from logger import slog
from datetime import datetime
from keiko.bet import web_login,payment,purchase
from taq.token_store import get_token
from taq.fetch_stock_data import analyze_stock_data
import time
import sys

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
        max_retries = 3
        retry_interval = 5 * 60  # 5分
        
        # for attempt in range(max_retries):
        #     slog("INFO", f"トークン取得中...({attempt + 1}/{max_retries})")
        #     ret = get_token()
        #     if ret:
        #         slog("INFO", "トークン取得に成功しました。")
        #         break
        #     else:
        #         slog("ERROR", f"トークン取得に失敗しました。({attempt + 1}/{max_retries})")
        #         if attempt < max_retries - 1:  # 最後の試行でない場合
        #             slog("INFO", f"{retry_interval // 60}分後に再試行します。")
        #             time.sleep(retry_interval)
        # else:
        #     # 3回とも失敗した場合
        #     slog("ERROR", "トークン取得に3回失敗しました。")
        #     slog("END", "TAQIKOを終了します。")
        #     sys.exit(1)

        # 株価取得 & 解析
        analyze_stock_data()

    slog("END", "TAQIKOを終了します。")

if __name__ == "__main__":
    main()
    sys.exit(1)