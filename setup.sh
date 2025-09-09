#!/bin/bash

# TAQIKO セットアップスクリプト

set -e  # エラーが発生した場合はスクリプトを終了

echo "========================================="
echo "TAQIKO セットアップを開始します..."
echo "========================================="

echo "システムパッケージを更新中..."
sudo apt-get update

echo "ビルドツールをインストール中..."
sudo apt-get install -y build-essential wget

# ta-libのダウンロードとインストール
echo "ta-libをダウンロード中..."
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.6.4-src.tar.gz

echo "ta-libを展開中..."
tar -xzvf ta-lib-0.6.4-src.tar.gz

echo "ta-libをコンパイル・インストール中..."
cd ta-lib
./configure --prefix=/usr
make
sudo make install

# 元のディレクトリに戻る
cd ..

# ライブラリパスを更新
sudo ldconfig

# クリーンアップ
echo "一時ファイルをクリーンアップ中..."
rm -rf ta-lib-0.6.4-src.tar.gz ta-lib

# Pythonライブラリのインストール
echo "Pythonライブラリをインストール中..."

echo "========================================="
echo "セットアップが完了しました。"
echo "========================================="