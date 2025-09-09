import os
from time import sleep

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from logger import slog
from utils import get_env_value

# TODO: 後でconfigに書く。
setmoney = 1000

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


def purchase(current_weekday):
	pass

