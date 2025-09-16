import os
from time import sleep
import random
import pandas as pd
from io import StringIO
import re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from urllib.parse import urlparse, parse_qs

from logger import slog
from utils import get_env_value

# TODO: 後でconfigに書く。
setmoney = 1000
waku_num = 6

# JRA 場番号
JRA_VENUE_CODES = {
    1: "札幌",
    2: "函館",
    3: "福島",
    4: "新潟",
    5: "東京",
    6: "中山",
    7: "中京",
    8: "京都",
    9: "阪神",
    10: "小倉",
}

def get_driver():
	global driver
	options = webdriver.ChromeOptions()
	# Webドライバ－の警告を出さないようにする。
	options.add_experimental_option('excludeSwitches', ['enable-logging'])
	# DOM読み込みまで
	options.set_capability('pageLoadStrategy', 'eager')
	# User Agentを設定
	options.add_argument("user-agent=Desired User Agent String")
	#headlessの指定をする場合、以下が必要。
	# options.add_argument('--headless')
	driver = webdriver.Chrome(options) #Chrome起動
	return None

def web_login():
	slog("INFO", f"WEBログインを実行します。")
	
	if not os.path.exists("../.env"):
		slog("ERROR", ".envファイルが存在しません。作成してください。")
		return False
	
	get_driver()
	driver.get('https://www.ipat.jra.go.jp/') #中央競馬
	# ログイン可能か判定
	try:
		number_inet = driver.find_element(By.NAME, 'inetid')
	except Exception as e:
		slog("ERROR", "WEBログインができませんでした。")
		driver.quit() 
		return False

	number_inet.send_keys(get_env_value("INETID")) #INET-ID
	sleep(1)
	#ログインボタン
	driver.find_element(By.CLASS_NAME, 'button').click()
	number_kanyu = driver.find_element(By.NAME, 'i')
	number_kanyu.send_keys(get_env_value("SUBNUM"))
	number_ansho = driver.find_element(By.NAME, 'p')
	number_ansho.send_keys(get_env_value("KPASS"))
	number_pars = driver.find_element(By.NAME, 'r')
	number_pars.send_keys(get_env_value("PARS"))

	driver.find_element(By.CLASS_NAME, 'buttonModern').click()
	sleep(5)
	slog("INFO", f"WEBログイン完了しました。")
	return True

def payment():
	slog("INFO", f"JRA 入金処理を実行します。")

	try:
		genmoney = driver.find_element(By.XPATH, "//td[@class='text-lg text-right ng-binding']").text
	except Exception as e: # ここでお知らせある場合、OK押してから入金へ進む。
			driver.find_element(By.XPATH,"//button[@class='btn btn-default btn-lg btn-ok' and starts-with(@ui-sref, 'home')]").click()
			sleep(2)
			genmoney = driver.find_element(By.XPATH,"//td[@class='text-lg text-right ng-binding']").text

	slog("INFO", "現在の購入限度額は" + genmoney + "です。")
	if genmoney != "0円":
		slog("INFO", "既に入金されています。")
		# 整数型に変換
		genmoney = int(genmoney.replace("円", "").replace(",", ""))

		if genmoney < int(setmoney):
			slog("INFO", "残金が足りません。入金指示を実行します。")
			enter_payment(setmoney)
			slog("INFO", "入金処理を完了しました。\n")
	else:
		# 最初の入金処理
		slog("INFO", "入金されていません。入金指示を実行します。")
		enter_payment(setmoney)
		slog("INFO", "入金処理を完了しました。\n")

	return True


def enter_payment(setmoney):
	driver.find_element(By.XPATH, "//button[@ng-click='vm.clickPayment()']").click()
	sleep(2)
	# 全てのウィンドウハンドルを取得
	window_handles = driver.window_handles
	# 最後に開いたタブに移動
	driver.switch_to.window(window_handles[-1])

	driver.find_element(By.XPATH, "//a[@onclick=\"javascript:submitForm(menuForm, 'nyukin');\"]").click()
	driver.find_element(By.ID, "NYUKIN_ID").send_keys(setmoney)
	driver.find_element(By.XPATH, "//a[@onclick=\"javascript:submitForm(nyukinForm, 'CNFRM');\"]").click()
	sleep(2)
	# 入金指示 最終確認
	driver.find_element(By.ID, "PASS_WORD_ID").send_keys(get_env_value("KPASS"))
	driver.find_element(By.XPATH, "//a[@onclick=\"javascript:submitForm(this, nyukinForm, 'EXEC');\"]").click()
	# ポップアップ "入金します。よろしいですか？"
	Alert(driver).accept()
	sleep(1)
	driver.find_element(By.XPATH, "//a[@onclick=\"javascript:submitGoLogoff();\"]")
	# 全てのウィンドウハンドルを取得
	window_handles = driver.window_handles
	# 最初のタブに移動
	driver.switch_to.window(window_handles[0])
	# 最初のタブ以外を閉じる
	for handle in window_handles[1:]:
		driver.switch_to.window(handle)
		driver.close()

	# コントロールを最初のタブに戻す
	driver.switch_to.window(window_handles[0])
	# 入金待ち時間
	sleep(5)
	# 更新ボタンを押す。
	driver.find_element(By.XPATH,"//button[@class='btn btn-default btn-lg pull-right' and starts-with(@ng-click, 'vm.getBalanceData()')]").click()

	return True

def get_race_list():
	global driver

	print("本日のレースを取得します。")

	now = datetime.now()
	now_datetime = now.strftime("%Y%m%d")
	url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={now_datetime}'

	# 新しいタブでnetkeibaを開く（JRAセッションを維持するため）
	driver.execute_script("window.open('');")
	window_handles = driver.window_handles
	driver.switch_to.window(window_handles[-1])  # 新しいタブに移動
	driver.get(url)
	sleep(3)
	rs = driver.find_elements(by=By.CLASS_NAME, value='RaceList_DataList')
	rsnames = [rsn.find_element(by=By.CLASS_NAME, value='RaceList_DataTitle').text for rsn in rs ]

	racelist = [] # レースデータリスト
	urllist = [] # netkeibaのURLリスト
	for rss in rs:
		rsname = rss.find_element(by=By.CLASS_NAME, value='RaceList_DataTitle').text
		rsis = rss.find_elements(by=By.CLASS_NAME, value='RaceList_DataItem')
		for rsi in rsis:
			rsia = rsi.find_element(by=By.TAG_NAME, value='a')
			rsin = rsi.find_element(by=By.CLASS_NAME, value='Race_Num')
			rsi2 = rsi.find_element(by=By.CLASS_NAME, value='RaceList_ItemContent')
			rsi2t = rsi2.find_element(by=By.CLASS_NAME, value='ItemTitle')
			rsi2gradebk = rsi2.find_elements(by=By.CLASS_NAME, value='Icon_GradeType')
			if len(rsi2gradebk) > 0 and 'Icon_GradeType ' in rsi2gradebk[0].get_attribute('class'):
				classes = rsi2gradebk[0].get_attribute('class').split(" ")
			else:
				rsi2grade = "未勝利"
			rsi2d = rsi2.find_element(by=By.CLASS_NAME, value='RaceData')
			rsi2d2 = rsi2d.find_element(by=By.CLASS_NAME, value='RaceList_Itemtime')
			rsi2d3 = rsi2d.find_elements(by=By.CLASS_NAME, value='RaceList_ItemLong')
			if rsi2d3 is not None and rsi2d3 != []:
				rsi2d3 = rsi2d3[0].text # コース情報
			else:
				rsi2d3 = rsi2d.find_elements(by=By.TAG_NAME, value='span')[1].text
			rurl = rsia.get_attribute('href')
			urllist.append(rurl) # netkeiba URL
			racelist.append((rsname,rsin.text, rsi2t.text, rsi2d2.text, rsi2d3, rsi2grade))
	return racelist, urllist


def get_venue_name(race_id_or_url: str) -> str:
    # race_id を抽出
    qs = parse_qs(urlparse(race_id_or_url).query)
    if "race_id" in qs and qs["race_id"]:
        race_id = qs["race_id"][0]
    else:
        race_id = race_id_or_url

    # 数字だけにして12桁 race_id を取得
    race_id = "".join(re.findall(r"\d", race_id))[:12]

    # 5〜6桁目が場番号
    venue_code = int(race_id[4:6])
    return JRA_VENUE_CODES.get(venue_code, "不明な競馬場")


def purchase(current_weekday):
	slog("INFO", f"購入処理を実行します。")
	sleep(1)

	# レース情報一覧を引っ張ってくる。
	racelist, urllist = get_race_list()

	# 第10Rの競馬場の名前を取得する。
	# ba_name = get_venue_name(urllist[9])   # 中山 10R
	race_number = 9
	betmoney = 100
	select_race = urllist[9]
	ba_name = get_venue_name(select_race)

	coursebutton_text = f"{ba_name}（{current_weekday}）" # 中山（土）
	print(coursebutton_text)

	# 初期位置はボタンが押された状態から始まる。
	if coursebutton_text == "中山":
		on_button = "btn btn-default btn-lg btn-block on"
	else:
		on_button = "btn btn-default btn-lg btn-block"

	# 現在の状況をデバッグ
	window_handles = driver.window_handles

	# netkeibaのウィンドウを閉じてJRAのメインウィンドウに戻る
	if len(window_handles) > 1:
		# 現在のウィンドウ（netkeiba）を閉じる
		driver.close()
		# JRAのメインウィンドウ（最初のウィンドウ）に切り替え
		driver.switch_to.window(window_handles[0])
	else:
		slog("INFO", "ウィンドウは1つのみです。")

	sleep(2)

	# try:
	# 	driver.find_element(By.XPATH, "//a[@ui-sref='home']").click()
	# 	sleep(2)
	# except:
	# 	slog("INFO", "ホームボタンが見つかりません。")

	# オッズ投票ボタン
	try:
		driver.find_element(By.XPATH, "//button[@ui-sref='bet.odds.type']").click()
	except Exception as e:
		slog("ERROR", f"オッズボタンが見つかりません: {e}")
		return False
	sleep(2)
	# オッズ投票（人気順）ボタン
	driver.find_element(By.LINK_TEXT, 'オッズ投票（人気順）').click()
	sleep(2)
	# 場をクリック
	driver.find_element(By.XPATH, f"//span[contains(text(), '{coursebutton_text}')]").click()
	sleep(2)
	# レース番号をクリック
	try:
		driver.find_element(By.XPATH, "//button[contains(@class, 'btn btn-default btn-lg btn-block ng-scope')]//*[contains(., '" + str(race_number) + "')]/..").click()
	except Exception as e:
		# 間に合わなかった場合
		print("The race is over.")
		# 投票メニューをクリック
		driver.find_element(By.XPATH,"//a[@ui-sref='home']").click()
		return False

	sleep(2)

	# 間に合わなかった場合
	# 式別 複勝を選択
	select_element = Select(driver.find_element(By.ID, 'bet-odds-populate-type'))
	sleep(2)
	select_element.select_by_visible_text('複勝')
	sleep(2)
	# 馬を選択
	# 'btn-odds'クラスを持つすべてのボタンをリストとして取得
	# horse_buttons = driver.find_elements(By.CLASS_NAME, "btn-odds")
	# horse_buttons[waku_num].click()
	driver.find_element(By.XPATH, "//button[@class='btn-odds' and starts-with(@ng-click, 'vm.selectOdds(oOdds)')]").click() # 一番人気ボタン

	sleep(2)
	# 金額を入力
	input_money = WebDriverWait(driver, 10).until(
		EC.element_to_be_clickable((By.XPATH, "//*[@id='main']/ui-view/div[2]/ui-view/ui-view/main/div/div[3]/select-list/div/div/div[3]/div[1]/input"))
	)
	input_money.send_keys(betmoney // 100) # 100円
	# <input type="text" maxlength="4" class="form-control text-right ng-pristine ng-valid ng-isolate-scope ng-empty ng-valid-maxlength ng-touched" ng-model="vm.nUnit" model-pattern="^\d{0,4}$" ng-disabled="vm.isRaceUnselected()" ng-blur="vm.checkAmount()" aria-labelledby="select-list-amount-unit" aria-invalid="false" style="">
	# //*[@id="main"]/ui-view/div[2]/ui-view/ui-view/main/div/div[3]/select-list/div/div/div[3]/div[1]/input

	sleep(1)
	# セットをクリック
	driver.find_element(By.XPATH, "//button[@class='btn btn-lg btn-set btn-primary' and starts-with(@ng-click, 'vm.onSet()')]").click()
	sleep(1)
	# 入力終了をクリック
	driver.find_element(By.XPATH, "//button[@class='btn btn-lg btn-default' and starts-with(@ng-click, 'vm.onShowBetList()')]").click()
	sleep(1)

	# 合計金額を取得
	money = driver.find_element(By.CSS_SELECTOR, ".number.ng-binding").text
	# 合計金額を入力
	driver.find_element(By.CSS_SELECTOR, "input[ng-model^='vm.cAmountTotal']").send_keys(100)
	sleep(1)
	# 購入するを入力
	driver.find_element(By.XPATH, "//button[@class='btn btn-lg btn-primary' and starts-with(@ng-click, 'vm.clickPurchase()')]").click()
	sleep(1)
	# 購入処理を完了させる(特殊ボタン)
	element = WebDriverWait(driver, 10).until(
		EC.visibility_of_element_located((By.CSS_SELECTOR, ".btn.btn-default.btn-lg.btn-ok.ng-binding"))
	)
	element.click()
	sleep(2)

	# 実際に購入した馬番を取得する。
	try:
		horse_number_element = driver.find_element(By.CSS_SELECTOR, ".set-heading.ng-binding")
		purchased_horse_number = horse_number_element.text
		# グローバル変数waku_numを更新
		global waku_num
		waku_num = int(purchased_horse_number)
	except Exception as e:
		slog("ERROR", f"馬番の取得に失敗しました: {e}")
		slog("INFO", f"設定値の馬番{waku_num}を使用します。")

	# 続けて購入するをクリック
	element = WebDriverWait(driver, 10).until(
		EC.element_to_be_clickable((By.XPATH, '//button[@ng-click="vm.clickContinue();"]'))
	)
	sleep(5)
	# 投票メニューをクリックして戻る
	driver.find_element(By.XPATH,"//a[@ui-sref='home']").click()
	# ウィンドウは閉じずにセッションを維持

	slog("INFO", f"{coursebutton_text}の第{race_number}Rで{waku_num}番の複勝を購入しました。")
	slog("INFO", select_race)

	return select_race

def get_race_result(url):
	global driver

	# セッションが無効な場合は新しいドライバーを作成
	try:
		driver.current_url  # セッションが有効かテスト
	except:
		slog("INFO", "Seleniumセッションが無効です。新しいドライバーを作成します。")
		get_driver()

	try:
		driver.get(url)
		sleep(2)
		data = pd.read_html(StringIO(driver.page_source))
		result_table = data[0] # 結果
		payment1 = data[1] # 払い戻し１
		payment2 = data[2] # 払い戻し２
		return result_table, pd.concat([payment1, payment2])
	except Exception as e:
		slog("ERROR", f"レース結果の取得に失敗しました: {e}")
		# 新しいドライバーで再試行
		slog("INFO", "新しいドライバーで再試行します。")
		get_driver()
		driver.get(url)
		sleep(2)
		data = pd.read_html(StringIO(driver.page_source))
		result_table = data[0] # 結果
		payment1 = data[1] # 払い戻し１
		payment2 = data[2] # 払い戻し２
		return result_table, pd.concat([payment1, payment2])

def result_check(url):
	slog("INFO", f"レース結果を取得します。")

	result_url = url.replace("race/shutuba.html", "race/result.html").replace("&rf=race_list", "&rf=race_submenu")
	result_table, payment = get_race_result(result_url) # 実行
	slog("INFO", result_table)
	slog("INFO", "\n")
	# slog("INFO", payment)

	is_waku_in_top3 = result_table[(result_table["着 順"].isin([1, 2, 3])) & (result_table["馬 番"] == waku_num)].shape[0] > 0
	slog("INFO", is_waku_in_top3)

	if is_waku_in_top3:
		# 複勝の行を見つける
		fukusho_row = payment.loc[payment[0] == "複勝"].iloc[0]

		# 馬番の文字列を分割（例: "14 6 7" -> ["14", "6", "7"]）
		horse_numbers_str = str(fukusho_row[1]).strip()
		horse_numbers = horse_numbers_str.split()

		# 配当金の文字列を分割（例: "480円 130円 130円" -> ["480円", "130円", "130円"]）
		odds_str = str(fukusho_row[2]).strip()
		odds_list = odds_str.split()

		slog("INFO", f"複勝馬番: {horse_numbers}")
		slog("INFO", f"複勝配当: {odds_list}")

		# 対象馬番が複勝圏内にあるかチェック
		if str(waku_num) in horse_numbers:
			index_of_waku = horse_numbers.index(str(waku_num))
			odds_amount_str = odds_list[index_of_waku]
			odds_amount = float(odds_amount_str.replace("円", "").replace(",", ""))
			slog("INFO", f"対象馬番{waku_num}の複勝配当: {odds_amount}円")
			dividend = odds_amount # 100円賭けに対する配当金
			slog("INFO", f"配当金: {dividend}円")
		else:
			slog("INFO", f"馬番{waku_num}は複勝圏外でした")
			dividend = 0
	else:
		dividend = 0

	# 賭け金額（100円固定）
	bet_amount = 100

	# 損益計算
	profit_loss = dividend - bet_amount

	# 現在の資金を読み込み
	capital_file_path = "../db/capital.txt"
	try:
		with open(capital_file_path, 'r') as f:
			current_capital = int(f.read().strip())
	except FileNotFoundError:
		slog("ERROR", f"capital.txtファイルが見つかりません: {capital_file_path}")
		current_capital = 0
	except ValueError:
		slog("ERROR", "capital.txtの内容が不正です")
		current_capital = 0

	# 新しい資金を計算
	new_capital = current_capital + profit_loss

	# 資金を更新
	try:
		with open(capital_file_path, 'w') as f:
			f.write(str(int(new_capital)))
		slog("INFO", f"資金更新: {current_capital}円 → {int(new_capital)}円 (損益: {int(profit_loss):+d}円)")
	except Exception as e:
		slog("ERROR", f"資金更新に失敗しました: {e}")

	# 処理完了後、ドライバーを終了
	try:
		driver.quit()
	except:
		pass

	return dividend

























