#!/usr/bin/env python3
"""
50銘柄を500株ずつ購入するテスト用スクリプト
liquidity_data.txtから銘柄コードと価格を読み込み、
.posファイルを生成する処理

このスクリプトは実際の取引を行わず、テスト用のポジションファイルのみを生成します。
"""

import os
import re
import datetime
from taq.portfolio import save_execution_to_position_file

def parse_liquidity_data():
    """
    liquidity_data.txtから銘柄コードと価格を抽出する

    Returns:
        list: [(銘柄コード, 価格), ...] のリスト
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    data_file = os.path.join(project_root, 'db', 'liquidity_data.txt')

    stocks = []

    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 銘柄コードと現在値を抽出するパターン
        # 例: "銘柄コード: 3905" と "現在値: 2065円"
        code_pattern = r'銘柄コード: ([^\s]+)'
        price_pattern = r'現在値: ([0-9,]+)円'

        codes = re.findall(code_pattern, content)
        prices = re.findall(price_pattern, content)

        # カンマを除去して数値に変換
        prices = [int(p.replace(',', '')) for p in prices]

        # コードと価格をペアにする
        stocks = list(zip(codes, prices))

        print(f"抽出された銘柄数: {len(stocks)}")

    except FileNotFoundError:
        print(f"ERROR: {data_file} が見つかりません")
        return []
    except Exception as e:
        print(f"ERROR: データ解析でエラーが発生: {e}")
        return []

    return stocks

def bulk_purchase_test(stocks, quantity_per_stock=500):
    """
    複数銘柄を一括購入するテスト処理

    Args:
        stocks: [(銘柄コード, 価格), ...] のリスト
        quantity_per_stock: 1銘柄あたりの購入株数

    Returns:
        bool: 処理成功かどうか
    """
    if not stocks:
        print("ERROR: 購入対象の銘柄がありません")
        return False

    print(f"=== 一括購入テスト開始 ===")
    print(f"対象銘柄数: {len(stocks)}")
    print(f"1銘柄あたり購入株数: {quantity_per_stock}株")

    success_count = 0
    total_cost = 0

    for i, (symbol, price) in enumerate(stocks, 1):
        print(f"\n[{i}/{len(stocks)}] 銘柄: {symbol}, 価格: {price}円")

        # テスト用の約定処理（実際の取引は行わない）
        execution_price = price  # テストでは現在値をそのまま約定価格とする
        cost = quantity_per_stock * execution_price

        # ポジションファイルに記録
        success = save_execution_to_position_file(
            symbol=symbol,
            qty=quantity_per_stock,
            execution_price=execution_price,
            transaction_type='buy'
        )

        if success:
            success_count += 1
            total_cost += cost
            print(f"  ✓ 成功: {quantity_per_stock}株 × {execution_price}円 = {cost:,}円")
        else:
            print(f"  ✗ 失敗: ポジションファイル作成エラー")

    print(f"\n=== 一括購入テスト完了 ===")
    print(f"成功: {success_count}/{len(stocks)}銘柄")
    print(f"総投資額: {total_cost:,}円")

    return success_count == len(stocks)

def main():
    """メイン処理"""
    print("50銘柄一括購入テストスクリプト")
    print("=" * 50)

    # liquidity_data.txtから銘柄情報を読み込み
    stocks = parse_liquidity_data()

    if not stocks:
        print("銘柄データの読み込みに失敗しました")
        return

    # 最初の5銘柄を表示
    print("\n読み込まれた銘柄（最初の5件）:")
    for i, (symbol, price) in enumerate(stocks[:5], 1):
        print(f"  {i}. {symbol}: {price}円")

    if len(stocks) > 5:
        print(f"  ... 他{len(stocks) - 5}銘柄")

    # 実行確認
    answer = input(f"\n{len(stocks)}銘柄を500株ずつ購入するテストを実行しますか？ (y/N): ")
    if answer.lower() != 'y':
        print("テストを中止しました")
        return

    # 一括購入テスト実行
    success = bulk_purchase_test(stocks, quantity_per_stock=500)

    if success:
        print("\n✓ 全銘柄の購入テストが正常に完了しました")
    else:
        print("\n✗ 一部の銘柄で処理が失敗しました")

if __name__ == "__main__":
    main()