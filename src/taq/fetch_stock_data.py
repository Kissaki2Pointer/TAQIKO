from logger import slog
import pandas_datareader.data as pdr
import talib as ta
import mplfinance as mpf
import json
import requests
import os

TARGETS = [
    ("6176", "ブランジスタ"),
    ("7792", "コラントッテ"),
    ("4424", "Amazia"),
    ("4260", "ハイブリッドテクノロジーズ"),
    ("5253", "カバー"),
]

def get_api_token():
    """tokenディレクトリからAPIトークンを取得"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    token_dir = os.path.join(script_dir, 'token')
    
    if not os.path.exists(token_dir):
        raise FileNotFoundError("tokenディレクトリが存在しません")
    
    token_files = [f for f in os.listdir(token_dir) if os.path.isfile(os.path.join(token_dir, f))]
    if not token_files:
        raise FileNotFoundError("トークンファイルが見つかりません")
    
    return token_files[0]  # 最初のファイル名をトークンとして返す

def get_stock_data(code):
	df = pdr.DataReader("{}.JP".format(code), "stooq").sort_index()
	return df

def analyze_stock_data():
	slog("INFO", "株価を取得します。")
	code = 5262 # ヒューム
	df = get_stock_data(code)
	# slog("INFO", df.tail())
	close = df['Close']
	macd, macdsignal, _ = ta.MACD(close, fastperiod=12, slowperiod=26, signalperiod=9)
	df['macd'] = macd
	df['macd_signal'] = macdsignal
	# slog("INFO", df.tail())

	# MDF 2つのシグナルで株価が上下する転換点を検出する。
	mdf = df.tail(100)
	apd  = [
	    mpf.make_addplot(mdf['macd'], panel=2, color='red'), # パネルの2番地に赤で描画
	    mpf.make_addplot(mdf['macd_signal'], panel=2, color='blue'), 
	]
	# mpf.plot(mdf, type='candle', volume=True, addplot=apd)

	# RSI 売られ過ぎか、買われ過ぎかの指標
	rsi14 = ta.RSI(close, timeperiod=14)
	rsi28 = ta.RSI(close, timeperiod=28)
	df['rsi14'], df['rsi28'] = rsi14, rsi28
	mdf = df.tail(100)
	apd  = [
	    mpf.make_addplot(mdf['rsi14'], panel=2, color='red'),
	    mpf.make_addplot(mdf['rsi28'], panel=2, color='blue')
	]
	# mpf.plot(mdf, type='candle', volume=True, addplot=apd)

	# 移動平均
	ma5, ma25, ma75  = ta.SMA(close, timeperiod=5), ta.SMA(close, timeperiod=25), ta.SMA(close, timeperiod=75)
	df['ma5'], df['ma25'], df['ma75'] = ma5, ma25, ma75
	mdf = df.tail(200)
	apd  = [
	    mpf.make_addplot(mdf['ma5'], panel=0, color='blue'),
	    mpf.make_addplot(mdf['ma25'], panel=0, color='purple'),
	    mpf.make_addplot(mdf['ma75'], panel=0, color='yellow'),
	]
	# mpf.plot(mdf, type='candle', volume=True, addplot=apd)

	# 結合グラフ
	mdf = df.tail(200)
	apd  = [
	    mpf.make_addplot(mdf['ma5'], panel=0, color='blue'),
	    mpf.make_addplot(mdf['ma25'], panel=0, color='purple'),
	    mpf.make_addplot(mdf['ma75'], panel=0, color='yellow'),
	    mpf.make_addplot(mdf['macd'], panel=2, color='red'),
	    mpf.make_addplot(mdf['macd_signal'], panel=2, color='blue'),
	    mpf.make_addplot(mdf['rsi14'], panel=3, color='red'),
	    mpf.make_addplot(mdf['rsi28'], panel=3, color='blue')
	]
	# mpf.plot(mdf, type='candle', volume=True, addplot=apd)


	# 入金処理はAPIでできない。

	# 現物余力 (ここで返ってきた額まで購入が可能)
	url = 'http://localhost:18080/kabusapi/wallet/cash'
	response = requests.get(url, headers={'X-API-KEY': get_api_token(),})
	buyable = json.loads(response.text)

	slog("INFO", "取引余力\t{}".format(buyable['StockAccountWallet']))

	if int(buyable['StockAccountWallet']) < 100 * 1000:  # 例: 100株×概算1,000円
		slog("ERROR", "資金がありません。入金してください。")
		return False

	return True
