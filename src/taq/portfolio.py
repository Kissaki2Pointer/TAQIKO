from logger import slog
import os
import datetime

def read_capital():
    """capital.txtから発注可能枠を読み込む"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    capital_file_path = os.path.join(project_root, 'db', 'capital.txt')
    
    try:
        with open(capital_file_path, 'r') as f:
            capital = int(float(f.read().strip()))
        slog("INFO", f"発注可能枠を読み込み: {capital:,}円")
        return capital
    except FileNotFoundError:
        slog("ERROR", f"capital.txtが見つかりませ")
        return 0
    except ValueError:
        slog("ERROR", "capital.txtの内容が正しくありません")
        return 0

def write_capital(amount):
    """capital.txtに発注可能枠を書き込む"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    capital_file_path = os.path.join(project_root, 'db', 'capital.txt')
    
    try:
        with open(capital_file_path, 'w') as f:
            f.write(str(int(amount)))
        slog("INFO", f"発注可能枠を更新: {int(amount):,}円")
        return True
    except Exception as e:
        slog("ERROR", f"capital.txtの書き込みでエラーが発生: {e}")
        return False

def save_execution_to_position_file(symbol, qty, execution_price, transaction_type='buy'):
    """
    約定価格をdb/positions/{銘柄コード}.posファイルに記録する
    
    Args:
        symbol: 銘柄コード（文字列）
        qty: 約定数量
        execution_price: 約定価格
        transaction_type: 取引種類（'buy' または 'sell'）
    
    Returns:
        bool: 記録成功かどうか
    """
    try:
        # スクリプトのディレクトリからプロジェクトルートを取得
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        positions_dir = os.path.join(project_root, 'db', 'positions')
        position_file = os.path.join(positions_dir, f'{symbol}.pos')
        
        # positionsディレクトリが存在しない場合は作成
        os.makedirs(positions_dir, exist_ok=True)
        
        current_time = datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')
        
        # 既存のポジションファイルを確認
        if os.path.exists(position_file):
            # 既存ファイルを読み込んで更新
            existing_data = {}
            with open(position_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        existing_data[key] = value
            
            # 既存データから現在の平均単価と数量を取得
            current_qty = int(existing_data.get('qty', 0))
            current_avg_cost = float(existing_data.get('avg_cost', execution_price))
            
            if transaction_type == 'buy':
                # 買い注文の場合：数量加算、平均単価を再計算
                new_qty = current_qty + qty
                new_avg_cost = ((current_qty * current_avg_cost) + (qty * execution_price)) / new_qty
                slog("INFO", f"既存ポジション更新: {symbol} {current_qty}株 → {new_qty}株, 平均単価: {current_avg_cost:.2f}円 → {new_avg_cost:.2f}円")
            else:
                # 売り注文の場合：数量減算、損益計算、平均単価は維持
                if current_qty >= qty:
                    new_qty = current_qty - qty
                    new_avg_cost = current_avg_cost if new_qty > 0 else 0
                    
                    # 売却損益を計算（売却価格 - 平均取得価格）× 売却数量
                    profit_loss = (execution_price - current_avg_cost) * qty
                    
                    slog("INFO", f"既存ポジション売却: {symbol} {current_qty}株 → {new_qty}株")
                    slog("INFO", f"売却損益: ({execution_price:.2f} - {current_avg_cost:.2f}) × {qty}株 = {profit_loss:+,.0f}円")
                else:
                    # 保有数量より多く売却しようとした場合
                    over_sell_qty = qty - current_qty
                    new_qty = 0
                    new_avg_cost = 0
                    
                    # 保有分の売却損益
                    profit_loss = (execution_price - current_avg_cost) * current_qty
                    slog("WARNING", f"保有数量超過売却: {symbol} 保有{current_qty}株に対し{qty}株売却")
                    slog("INFO", f"保有分売却損益: ({execution_price:.2f} - {current_avg_cost:.2f}) × {current_qty}株 = {profit_loss:+,.0f}円")
                    slog("WARNING", f"超過分{over_sell_qty}株は空売り扱い")
        else:
            # ポジションファイルが存在しない場合
            if transaction_type == 'buy':
                new_qty = qty
                new_avg_cost = execution_price
                slog("INFO", f"新規ポジション作成: {symbol} {new_qty}株, 平均単価: {new_avg_cost:.2f}円")
            else:
                # 売り注文で既存ポジションがない場合はエラー
                slog("ERROR", f"売却対象のポジションが存在しません: {symbol}")
                return False
        
        # 数量が0になった場合はファイルを削除
        if new_qty == 0:
            if os.path.exists(position_file):
                os.remove(position_file)
                slog("INFO", f"ポジション完売により削除: {position_file}")
            return True
        
        # ファイルに書き込み
        with open(position_file, 'w', encoding='utf-8') as f:
            f.write(f'symbol={symbol}\n')
            f.write(f'qty={new_qty}\n')
            f.write(f'avg_cost={new_avg_cost:.2f}\n')
            f.write(f'last_update={current_time}\n')
        
        slog("INFO", f"ポジションファイル更新完了: {position_file}")
        return True
        
    except Exception as e:
        slog("ERROR", f"ポジションファイル更新でエラー: {symbol} - {e}")
        return False

def calculate_commission(execution_amount):
    """
    約定金額に基づいて手数料を計算する
    
    Args:
        execution_amount: 約定金額（円）
    
    Returns:
        int: 手数料（円）
    """
    if execution_amount <= 50000:
        return 55
    elif execution_amount <= 100000:
        return 99
    elif execution_amount <= 200000:
        return 115
    elif execution_amount <= 500000:
        return 275
    elif execution_amount <= 1000000:
        return 535
    else:
        # 100万円超: 約定金額×0.099% + 99円（上限4,059円）
        commission = int(execution_amount * 0.00099) + 99
        return min(commission, 4059)

def get_all_positions():
    """
    db/positions内の全ての.posファイルを読み込んでポジション情報を取得する

    Returns:
        list: [(銘柄コード, 銘柄名または銘柄コード), ...] のリスト
    """
    positions = []

    try:
        # スクリプトのディレクトリからプロジェクトルートを取得
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        positions_dir = os.path.join(project_root, 'db', 'positions')

        if not os.path.exists(positions_dir):
            slog("WARNING", f"ポジションディレクトリが存在しません: {positions_dir}")
            return positions

        # .posファイルを検索
        for filename in os.listdir(positions_dir):
            if filename.endswith('.pos'):
                symbol = filename.replace('.pos', '')
                position_file = os.path.join(positions_dir, filename)

                # ポジションファイルの内容を確認
                try:
                    with open(position_file, 'r', encoding='utf-8') as f:
                        data = {}
                        for line in f:
                            line = line.strip()
                            if '=' in line:
                                key, value = line.split('=', 1)
                                data[key] = value

                    # 数量が0より大きい場合のみ追加
                    qty = int(data.get('qty', 0))
                    if qty > 0:
                        # 銘柄名は現時点では銘柄コードを使用（必要に応じて後で拡張）
                        positions.append((symbol, symbol))
                        slog("INFO", f"ポジション検出: {symbol} ({qty}株)")

                except Exception as e:
                    slog("ERROR", f"ポジションファイル読み込みエラー: {position_file} - {e}")
                    continue

        slog("INFO", f"ポジション数: {len(positions)}銘柄")

    except Exception as e:
        slog("ERROR", f"ポジション取得でエラー: {e}")

    return positions

def get_stock_price_from_liquidity_data(symbol):
    """
    liquidity_data.txtから指定銘柄の現在値を取得する

    Args:
        symbol: 銘柄コード（文字列）

    Returns:
        float: 現在値、見つからない場合はNone
    """
    try:
        # スクリプトのディレクトリからプロジェクトルートを取得
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        data_file = os.path.join(project_root, 'db', 'liquidity_data.txt')

        if not os.path.exists(data_file):
            slog("WARNING", f"liquidity_data.txtが見つかりません: {data_file}")
            return None

        with open(data_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 銘柄コードと現在値を検索
        import re

        # 銘柄コードのパターンを検索
        code_pattern = f'銘柄コード: {re.escape(symbol)}'
        code_match = re.search(code_pattern, content)

        if code_match:
            # 銘柄コードが見つかった場合、その後の現在値を検索
            start_pos = code_match.end()
            # 現在値パターン: "現在値: 1,234円"
            price_pattern = r'現在値: ([0-9,]+)円'
            price_match = re.search(price_pattern, content[start_pos:start_pos+200])  # 200文字以内で検索

            if price_match:
                price_str = price_match.group(1).replace(',', '')  # カンマを除去
                price = float(price_str)
                slog("INFO", f"liquidity_data.txtから取得: {symbol} = {price}円")
                return price

        slog("WARNING", f"liquidity_data.txtに銘柄が見つかりません: {symbol}")
        return None

    except Exception as e:
        slog("ERROR", f"liquidity_data.txt読み込みエラー: {e}")
        return None

def get_stocks_from_liquidity_data():
    """
    liquidity_data.txtから全銘柄のリストを取得する

    Returns:
        list: [(銘柄コード, 銘柄名), ...] のリスト
    """
    stocks = []

    try:
        # スクリプトのディレクトリからプロジェクトルートを取得
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(script_dir))
        data_file = os.path.join(project_root, 'db', 'liquidity_data.txt')

        if not os.path.exists(data_file):
            slog("WARNING", f"liquidity_data.txtが見つかりません: {data_file}")
            return stocks

        with open(data_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 銘柄名と銘柄コードを抽出するパターン
        import re

        # 銘柄名: "銘柄名: データセクション(株)"
        # 銘柄コード: "銘柄コード: 3905"
        name_pattern = r'銘柄名: (.+)'
        code_pattern = r'銘柄コード: ([^\s]+)'

        names = re.findall(name_pattern, content)
        codes = re.findall(code_pattern, content)

        # 名前とコードをペアにする
        if len(names) == len(codes):
            stocks = list(zip(codes, names))
            slog("INFO", f"liquidity_data.txtから{len(stocks)}銘柄を取得")
        else:
            slog("ERROR", f"銘柄名({len(names)})と銘柄コード({len(codes)})の数が一致しません")

    except Exception as e:
        slog("ERROR", f"liquidity_data.txt解析エラー: {e}")

    return stocks









