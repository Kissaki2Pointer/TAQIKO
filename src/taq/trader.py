from logger import slog
import pandas_datareader.data as pdr
import pandas as pd
import talib as ta
import numpy as np
from .portfolio import read_capital, write_capital, calculate_commission, save_execution_to_position_file, get_all_positions
from .broker import buy_stock_cash, sell_stock_cash, wait_for_execution_and_get_price
from .data_fetcher import fetch_yahoo_finance_data

def get_targets():
    """
    db/positions内の.posファイルから動的にターゲット銘柄リストを生成する

    Returns:
        list: [(銘柄コード, 銘柄名), ...] のリスト
    """
    positions = get_all_positions()
    if positions:
        slog("INFO", f"ポジションファイルから{len(positions)}銘柄を取得")
        return positions
    else:
        # フォールバック: 既存の固定リスト
        slog("WARNING", "ポジションファイルが見つからないため、固定リストを使用")
        return [
            ("6176", "ブランジスタ"),
            ("7792", "コラントッテ"),
            ("4424", "Amazia"),
            ("4260", "ハイブリッドテクノロジーズ"),
            ("5253", "カバー"),
            ("5262", "ヒューム"),
        ]

def update_capital_after_trading(buy_transactions, sell_transactions):
    """
    取引終了後にcapital.txtを更新する
    
    Args:
        buy_transactions: 買い注文のリスト [(symbol, qty, price), ...]
        sell_transactions: 売り注文のリスト [(symbol, qty, price), ...]
    
    Returns:
        bool: 更新成功かどうか
    """
    try:
        # 現在の残高を取得
        current_capital = read_capital()
        
        # 手数料合計を計算
        total_commission = 0
        
        # 買い注文の手数料を計算
        for symbol, qty, price in buy_transactions:
            execution_amount = qty * price
            commission = calculate_commission(execution_amount)
            total_commission += commission
            slog("INFO", f"買い手数料: {symbol} {execution_amount:,}円 → 手数料 {commission}円")
        
        # 売り注文の手数料を計算
        for symbol, qty, price in sell_transactions:
            execution_amount = qty * price
            commission = calculate_commission(execution_amount)
            total_commission += commission
            slog("INFO", f"売り手数料: {symbol} {execution_amount:,}円 → 手数料 {commission}円")
        
        # 実現損益を計算（売り注文の合計 - 買い注文の合計）
        buy_total = sum(qty * price for symbol, qty, price in buy_transactions)
        sell_total = sum(qty * price for symbol, qty, price in sell_transactions)
        realized_pnl = sell_total - buy_total
        
        # 新しい残高を計算
        # capital_new = capital_old + 実現損益合計 − 手数料合計
        new_capital = current_capital + realized_pnl - total_commission
        
        # ログ出力
        slog("INFO", f"=== 残高更新 ===")
        slog("INFO", f"前回残高: {current_capital:,}円")
        slog("INFO", f"買い合計: {buy_total:,}円")
        slog("INFO", f"売り合計: {sell_total:,}円")
        slog("INFO", f"実現損益: {realized_pnl:+,}円")
        slog("INFO", f"手数料合計: {total_commission:,}円")
        slog("INFO", f"新残高: {new_capital:,}円")
        
        # capital.txtに書き込み
        return write_capital(new_capital)
        
    except Exception as e:
        slog("ERROR", f"残高更新でエラーが発生: {e}")
        return False


def get_stock_data(code):
	df = pdr.DataReader("{}.JP".format(code), "stooq").sort_index()
	return df

def analyze_stock_with_moving_averages(code, company_name):
	"""
	株価データを取得し、短期・長期移動平均線およびゴールデンクロス・デッドクロスを計算
	"""
	slog("INFO", f"{company_name}（{code}）の分析を開始します。")
	
	# 株価データ取得
	df = get_stock_data(code)
	close = df['Close']
	
	# 移動平均線の計算（5日線と25日線）
	ma5 = ta.SMA(close, timeperiod=5)
	ma25 = ta.SMA(close, timeperiod=25)
	df['ma5'], df['ma25'] = ma5, ma25
	
	# ゴールデンクロス・デッドクロスの検出
	# 5日移動平均と25日移動平均を比較（5日 > 25日ならTrue）
	cross = ma5 > ma25
	
	# 前日と比較して状態が変わった日を検出
	cross_shift = cross.shift(1)
	# ゴールデンクロス：FalseからTrueに変わった日
	gc_flag = (cross != cross_shift) & (cross == True)
	# デッドクロス：TrueからFalseに変わった日  
	dc_flag = (cross != cross_shift) & (cross == False)
	
	# ゴールデンクロスの日には5日移動平均の値、デッドクロスの日には25日移動平均の値を保存
	gc = [m if g == True else np.nan for g, m in zip(gc_flag, ma5)]
	dc = [m if d == True else np.nan for d, m in zip(dc_flag, ma25)]
	df['gc'], df['dc'] = gc, dc
	
	# 結果の表示
	# slog("INFO", f"{company_name}（{code}）の最新データ:")
	# slog("INFO", df[['Close', 'ma5', 'ma25']].tail().to_string())
	
	# ゴールデンクロス・デッドクロスの最新発生を確認
	recent_gc = df[df['gc'].notna()].tail(1)
	recent_dc = df[df['dc'].notna()].tail(1)
	
	if not recent_gc.empty:
		gc_date = recent_gc.index[0].strftime('%Y-%m-%d')
		gc_value = recent_gc['gc'].iloc[0]
		slog("INFO", f"最新のゴールデンクロス: {gc_date} (価格: {gc_value:.2f}円)")
	
	if not recent_dc.empty:
		dc_date = recent_dc.index[0].strftime('%Y-%m-%d')
		dc_value = recent_dc['dc'].iloc[0]
		slog("INFO", f"最新のデッドクロス: {dc_date} (価格: {dc_value:.2f}円)")
	
	# 前日のゴールデンクロス・デッドクロスを確認
	yesterday_gc = False
	yesterday_dc = False
	
	if len(df) >= 2:
		# 最新から2番目（前日）のデータを取得
		yesterday_data = df.iloc[-2]
		yesterday_gc = not pd.isna(yesterday_data.get('gc', np.nan))
		yesterday_dc = not pd.isna(yesterday_data.get('dc', np.nan))
		
		if yesterday_gc:
			slog("INFO", f"前日にゴールデンクロス発生: {company_name}（{code}）")
		if yesterday_dc:
			slog("INFO", f"前日にデッドクロス発生: {company_name}（{code}）")
	
	return df, yesterday_gc, yesterday_dc

def analyze_all_targets():
	"""
	ポジションファイルから取得した全銘柄を分析し、buy_listとsell_listを作成
	"""
	slog("INFO", "全銘柄の移動平均線分析を開始します。")

	# 動的にターゲット銘柄を取得
	targets = get_targets()

	results = {}
	buy_list = []
	sell_list = []

	for code, company_name in targets:
		try:
			df, yesterday_gc, yesterday_dc = analyze_stock_with_moving_averages(code, company_name)
			results[code] = df
			
			# 前日にゴールデンクロスが発生した銘柄をbuy_listに追加
			if yesterday_gc:
				buy_list.append((code, company_name))
				slog("INFO", f"買いリストに追加: {company_name}（{code}）")
			
			# 前日にデッドクロスが発生した銘柄をsell_listに追加
			if yesterday_dc:
				sell_list.append((code, company_name))
				slog("INFO", f"売りリストに追加: {company_name}（{code}）")
				
		except Exception as e:
			slog("ERROR", f"{company_name}（{code}）の分析でエラーが発生: {e}")
	
	# 結果をログに出力
	slog("INFO", "=== 売買対象リスト ===")
	slog("INFO", f"買いリスト ({len(buy_list)}銘柄):")
	for code, name in buy_list:
		slog("INFO", f"  - {name}（{code}）")
	
	slog("INFO", f"売りリスト ({len(sell_list)}銘柄):")
	for code, name in sell_list:
		slog("INFO", f"  - {name}（{code}）")
	
	return results, buy_list, sell_list

def analyze_stock_data():
	slog("INFO", "売買リストを作成します。")

	results, buy_list, sell_list = analyze_all_targets()

	# capital.txtから今日の発注可能枠を取得
	daily_capital = read_capital()

	# targetsを1回だけ取得して使い回す
	targets = get_targets()

	# 入金処理はAPIでできない。

	# 現物余力 (ここで返ってきた額まで購入が可能)
	# url = 'http://localhost:18080/kabusapi/wallet/cash'
	# response = requests.get(url, headers={'X-API-KEY': get_api_token(),})
	# buyable = json.loads(response.text)

	# slog("INFO", "取引余力\t{}".format(buyable['StockAccountWallet']))

	# if int(buyable['StockAccountWallet']) < 100 * 1000:  # 例: 100株×概算1,000円
	# 	slog("ERROR", "資金がありません。入金してください。")
	# 	return False

	# テスト用: 強制的に2番目の銘柄を買いリストに追加
	if not buy_list and len(targets) > 1:
		test_stock = targets[1]  # 2番目の銘柄
		buy_list.append(test_stock)
		slog("INFO", f"テスト用に買いリストに追加: {test_stock[1]}（{test_stock[0]}）")

	# 買いリストの銘柄を100株ずつ成行で購入（検証用API使用）
	slog("INFO", "=== 購入処理開始 ===")
	successful_orders = 0
	total_orders = len(buy_list)
	buy_execution_results = []  # 約定価格を記録するリスト
	
	if daily_capital > 0 and total_orders > 0:
		for code, company_name in buy_list:
			try:
				slog("INFO", f"購入処理: {company_name}（{code}）100株 成行注文")
				result = buy_stock_cash(code, qty=100, price=0, use_test_api=True)
				
				if result:
					# 約定価格を取得
					execution_price = wait_for_execution_and_get_price(result, code, use_test_api=True)
					if execution_price:
						buy_execution_results.append((code, company_name, 100, execution_price))
						successful_orders += 1
						slog("INFO", f"購入成功: {company_name}（{code}）約定価格={execution_price}円")
						
						# ポジションファイルに約定情報を記録
						save_success = save_execution_to_position_file(code, 100, execution_price, 'buy')
						if not save_success:
							slog("WARNING", f"ポジションファイル記録失敗: {company_name}（{code}）")
					else:
						slog("WARNING", f"購入注文送信成功だが約定価格取得失敗: {company_name}（{code}）")
				else:
					slog("ERROR", f"購入失敗: {company_name}（{code}）")
					
			except Exception as e:
				slog("ERROR", f"購入処理でエラー: {company_name}（{code}） - {e}")
	
	else:
		if daily_capital <= 0:
			slog("WARNING", "発注可能枠が0円のため購入処理をスキップしました")
		if total_orders == 0:
			slog("INFO", "購入対象がないため購入処理をスキップしました")
	
	slog("INFO", f"購入処理完了: {successful_orders}/{total_orders}件成功")

	# テスト用: 強制的に最初の銘柄を売りリストに追加
	if not sell_list and targets:
		test_stock = targets[0]  # 最初の銘柄
		sell_list.append(test_stock)
		slog("INFO", f"テスト用に売りリストに追加: {test_stock[1]}（{test_stock[0]}）")

	# 売りリストの銘柄を100株ずつ成行で売却（検証用API使用）
	slog("INFO", "=== 売却処理開始 ===")
	sell_successful_orders = 0
	total_sell_orders = len(sell_list)
	sell_execution_results = []  # 約定価格を記録するリスト
	
	for code, company_name in sell_list:
		try:
			slog("INFO", f"売却処理: {company_name}（{code}）100株 成行注文")
			result = sell_stock_cash(code, qty=100, price=0, use_test_api=True)
			
			if result:
				# 約定価格を取得
				execution_price = wait_for_execution_and_get_price(result, code, use_test_api=True)
				if execution_price:
					sell_execution_results.append((code, company_name, 100, execution_price))
					sell_successful_orders += 1
					slog("INFO", f"売却成功: {company_name}（{code}）約定価格={execution_price}円")
					
					# ポジションファイルに約定情報を記録
					save_success = save_execution_to_position_file(code, 100, execution_price, 'sell')
					if not save_success:
						slog("WARNING", f"ポジションファイル記録失敗: {company_name}（{code}）")
				else:
					slog("WARNING", f"売却注文送信成功だが約定価格取得失敗: {company_name}（{code}）")
			else:
				slog("ERROR", f"売却失敗: {company_name}（{code}）")
				
		except Exception as e:
			slog("ERROR", f"売却処理でエラー: {company_name}（{code}） - {e}")
	
	if total_sell_orders == 0:
		slog("INFO", "売却対象がないため売却処理をスキップしました")
	
	slog("INFO", f"売却処理完了: {sell_successful_orders}/{total_sell_orders}件成功")

	# 取引終了後にcapital.txtを更新
	slog("INFO", "=== 残高更新処理開始 ===")
	
	# 実際の約定価格を使用して取引記録を作成
	buy_transactions = []
	for code, company_name, qty, execution_price in buy_execution_results:
		buy_transactions.append((code, qty, execution_price))
	
	sell_transactions = []
	for code, company_name, qty, execution_price in sell_execution_results:
		sell_transactions.append((code, qty, execution_price))
	
	if buy_transactions or sell_transactions:
		slog("INFO", "実際の約定価格に基づいて発注可能枠を更新します")
		update_success = update_capital_after_trading(buy_transactions, sell_transactions)
		
		if update_success:
			slog("INFO", "発注可能枠の更新が完了しました")
		else:
			slog("ERROR", "発注可能枠の更新に失敗しました")
	else:
		slog("INFO", "約定した取引がないため発注可能枠の更新をスキップしました")

	return True





# -------

def execute_trade():
    """
    株価データを取得して取引を実行する
    """
    slog("INFO", "株価データ取得・取引処理を開始します。")

    # 株価データをスクレイピング
    stock_data = fetch_yahoo_finance_data()

    if stock_data:
        slog("INFO", f"東証グロース出来高上位データ取得完了: {len(stock_data)}銘柄")

        # 取得したデータをログに出力
        for stock in stock_data[:10]:  # 上位10銘柄のみ表示
            slog("INFO", f"[{stock['rank']}位] {stock['name']}({stock['symbol']}): {stock['current_price']}円 ({stock['change']} {stock['change_rate']}) 出来高: {stock['volume']}")

        # テスト用: liquidity_data.txtにデータを出力
        # try:
        #     with open('../db/liquidity_data.txt', 'w', encoding='utf-8') as f:
        #         f.write("東証グロース出来高上位データ\n")
        #         f.write("=" * 50 + "\n")
        #         for stock in stock_data:
        #             f.write(f"順位: {stock['rank']}\n")
        #             f.write(f"銘柄名: {stock['name']}\n")
        #             f.write(f"銘柄コード: {stock['symbol']}\n")
        #             f.write(f"現在値: {stock['current_price']}円\n")
        #             f.write(f"前日比: {stock['change']}\n")
        #             f.write(f"前日比率: {stock['change_rate']}\n")
        #             f.write(f"出来高: {stock['volume']}\n")
        #             f.write("-" * 30 + "\n")

        #     slog("INFO", "取得データをliquidity_data.txtに出力しました。")
        # except Exception as e:
        #     slog("ERROR", f"liquidity_data.txtへの出力に失敗: {e}")

        analyze_stock_data()
        return True
    else:
        slog("ERROR", "株価データ取得に失敗したため、取引処理を中止します。")
        return False


