#!/usr/bin/env python3

from logger import slog
from datetime import datetime
from keiko.bet import web_login,payment,purchase
from taq.token_store import get_token
from taq.trader import analyze_stock_data
from utils import is_target_time
import jpholiday
import time
import sys

def test_holiday_function():
    """祝日判定関数の簡易テスト"""
    print("=== 祝日判定テスト ===")
    
    # テスト用の日付
    test_dates = [
        datetime(2024, 1, 1),   # 元日
        datetime(2024, 12, 31), # 大晦日（年末年始）
        datetime(2024, 1, 2),   # 1月2日（年末年始）
        datetime(2024, 5, 3),   # 憲法記念日
        datetime(2024, 7, 15),  # 平日
    ]
    
    for test_date in test_dates:
        # 一時的に現在時刻を変更してテスト
        original_datetime = datetime.now
        datetime.now = lambda: test_date
        
        try:
            is_holiday, holiday_name = is_holiday_today()
            status = "祝日" if is_holiday else "平日"
            name_info = f"({holiday_name})" if holiday_name else ""
            print(f"{test_date.strftime('%Y-%m-%d')}: {status}{name_info}")
        finally:
            # datetimeを元に戻す
            datetime.now = original_datetime
    
    print("===================")

def is_holiday_today():
    """今日が祝日かどうかを判定する
    
    Returns:
        tuple: (bool, str) - (祝日かどうか, 祝日名または空文字)
    """
    today = datetime.now().date()
    
    # jpholidayで祝日判定
    if jpholiday.is_holiday(today):
        holiday_name = jpholiday.is_holiday_name(today)
        return True, holiday_name
    
    # 年末年始の金融機関休日
    today_str = today.strftime("%m/%d")
    if today_str in ["12/31", "01/02", "01/03"]:
        return True, "年末年始"
    
    return False, ""

def main():
    slog("START", "TAQIKOを起動します。")
    
    weekdays = ["月", "火", "水", "木", "金", "土", "日"]
    current_weekday = weekdays[datetime.now().weekday()]
    
    slog("INFO", f"今日は{current_weekday}曜日です。")
    
    # 祝日判定
    is_holiday, holiday_name = is_holiday_today()
    
    if current_weekday in ["土", "日"]:
        slog("INFO", "8時30分まで待機します...")
        while not is_target_time("8:30"):
            time.sleep(60)  # 1分ごとにチェック
        slog("INFO", "競馬自動投票ツールを実行します。")

        # JRA WEBログイン
        ret = web_login()
        if ret == True:
            # 入金処理
            ret = payment()
            if ret == True:
                ret = purchase(current_weekday)
    elif is_holiday:
        slog("INFO", f"今日は祝日({holiday_name})です。")
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
        
        for attempt in range(max_retries):
            slog("INFO", f"トークン取得中...({attempt + 1}/{max_retries})")
            ret = get_token(use_test_api=True)
            if ret:
                slog("INFO", "トークン取得に成功しました。")
                break
            else:
                slog("ERROR", f"トークン取得に失敗しました。({attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:  # 最後の試行でない場合
                    slog("INFO", f"{retry_interval // 60}分後に再試行します。")
                    time.sleep(retry_interval)
        else:
            # 3回とも失敗した場合
            slog("ERROR", "トークン取得に3回失敗しました。")
            slog("END", "TAQIKOを終了します。")
            sys.exit(1)

        # 株価取得 & 解析
        analyze_stock_data()

    slog("END", "TAQIKOを終了します。\n")

if __name__ == "__main__":    
    main()
    sys.exit(1)