from logger import slog
import pandas_datareader.data as pdr
import talib as ta
import mplfinance as mpf

# API_BASE = "http://localhost:18080/kabusapi" # 本番
API_BASE_KENSHO = "http://localhost:18081/kabusapi" # 検証

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
	slog("INFO", df.tail())

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

	return True
