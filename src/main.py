#!/usr/bin/env python3

import jpholiday
import time
import sys

from logger import slog
from datetime import datetime
from keiko.bet import web_login,payment,purchase,result_check
from taq.token_store import get_token
from taq.trader import analyze_stock_data
from utils import is_target_time

def is_holiday_today():
	"""今日が祝日かどうかを判定する
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
	
	if current_weekday in ["土", "日"] or is_holiday:
		if is_holiday:
			slog("INFO", f"今日は祝日({holiday_name})です。")

		slog("INFO", "競馬自動投票ツールを実行します。")

		# 投票可能時間の8時30分まで待機する。
		# slog("INFO", "8時30分まで待機します...")
		# while not is_target_time("8:30"):
		# 	time.sleep(60)  # 1分ごとにチェック

		# JRA WEBログイン
		if not web_login():
			return False

		# 入金処理
		if not payment():
			return False

		# 購入処理
		if not purchase(current_weekday):
			return False

		# 1時間待機
		slog("INFO", "待機を開始します。")
		time.sleep(1800) # 30分

		# 結果確認
		dividend = result_check()
		if dividend:
			# 勝ち
			slog("INFO", "★勝ち")
		else:
			# 負け
			slog("INFO", "負け")

		return True
	else:
		slog("INFO", "株自動売買ツールを実行します。")
		retry_interval = 60  # 1分
		
		for attempt in range(3):
			slog("INFO", f"トークン取得中...({attempt + 1}/3)")
			ret = get_token(use_test_api=True)
			if ret:
				slog("INFO", "トークン取得に成功しました。")
				break
			else:
				slog("ERROR", f"トークン取得に失敗しました。({attempt + 1}/3)")
				if attempt < 3 - 1:  # 最後の試行でない場合
					slog("INFO", f"{retry_interval}秒後に再試行します。")
					time.sleep(retry_interval)
		else:
			# 3回とも失敗した場合
			slog("ERROR", "トークン取得に3回失敗しました。")
			slog("END", "TAQIKOを終了します。")
			sys.exit(1)

		# 株価取得 & 解析
		analyze_stock_data()

	slog("END", "TAQIKOを終了します。\n")
	return True

if __name__ == "__main__":    
	main()
	sys.exit(1)