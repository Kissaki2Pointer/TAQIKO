#!/usr/bin/env python3

import jpholiday
import time
import sys
from datetime import datetime

import os
from time import sleep
import random
import pandas as pd
from io import StringIO

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.alert import Alert
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from urllib.parse import urlparse, parse_qs
import re

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

def get_race_list():
	get_driver()

	print("本日のレースを取得します。")

	now = datetime.now()
	now_datetime = now.strftime("%Y%m%d")
	url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={now_datetime}'
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

def main():
	print("TAQIKOを起動します。")
	# レース情報一覧を引っ張ってくる。
	racelist, urllist = get_race_list()
	# print(urllist)
	# 第9Rの競馬場の名前を取得する。
	ba_name = get_venue_name(urllist[8])   # 中山競馬場
	print(ba_name)

if __name__ == "__main__":    
	main()
	print("TAQIKOを終了します。\n")
	sys.exit(1)