import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import urllib.parse
import re

# ページ設定
st.set_page_config(page_title="Yahoo Tool", layout="wide")

# 認証機能
def check_password():
    if "auth" not in st.session_state:
        st.session_state.auth = False
    if not st.session_state.auth:
        st.title("🔐 ログイン")
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.button("Log in"):
            if user == st.secrets["auth"]["username"] and pw == st.secrets["auth"]["password"]:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        return False
    return True

# Yahooから「より正確な件数」を取得する高精度関数
def get_allintitle_precision(keyword):
    # 完全一致を狙うためダブルクォーテーションで囲む
    search_query = f'allintitle:"{keyword}"'
    encoded_query = urllib.parse.quote(search_query)
    # 検索結果を確実に100件表示させて計算のズレをなくす（n=100）
    url = f"https://search.yahoo.co.jp/search?p={encoded_query}&n=100"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.yahoo.co.jp/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 1. まず「約◯件」という表示を探す
        count_text = "0"
        target = soup.find(["span", "p"], text=re.compile(r'件'))
        if not target:
            # 別の場所（class名など）から探す
            target = soup.select_one(".SearchStatistics_item__Uu_vV")
        
        if target:
            # 数字だけを抽出
            nums = re.findall(r'[0-9,]+', target.text)
            if nums:
                count_text = nums[0]

        # 2. 【高精度化】実際に検索結果として並んでいる「記事のタイトル数」を数える
        # Yahooの検索結果の各タイトルには通常特定のクラスが付与されている
        search_results = soup.select("h3") # 検索結果のタイトルはh3タグが多い
        real_count = 0
        for res in search_results:
            # 広告や関連キーワードを除外するための簡易フィルタ
            if res.select_one("a"):
                real_count += 1

        # 3. 結果の判定
        # 「約1件」と出ても実際の結果が0なら「0」と判断する
        final_count = count_text
        if real_count == 0 and ("1" in count_text or "取得失敗" in count_text):
            return "0 (検索結果なし)"
        
        # 10件以下の場合は、実数カウントの数字を優先して表示
        if real_count <= 10 and real_count > 0:
            return f"{real_count} 件 (実数確定)"
            
        return f"約 {final_count} 件"

    except Exception as e:
        return f"エラー"

# メイン機能
def main():
    st.sidebar.title("MENU")
    menu = st.sidebar.radio("機能を選択", ["ホーム", "allintitle分析", "知恵袋リサーチ"])

    if menu == "ホーム":
        st.title("🏠 ホーム")
        st.success("ログイン成功！")

    elif menu == "allintitle分析":
        st.title("🔍 allintitle分析 (高精度版)")
        st.write("10件以下のキーワードを厳密に調査します。")
        keywords = st.text_area("調査キーワード", height=200)
        
        if st.button("分析開始"):
            if keywords:
                kw_list = [k.strip() for k in keywords.split('\n') if k.strip()]
                results = []
                bar = st.progress(0)
                
                for i, kw in enumerate(kw_list):
                    st.write(f"🔎 {kw} を詳細調査中...")
                    count = get_allintitle_precision(kw)
                    results.append({"キーワード": kw, "allintitle件数": count})
                    
                    time.sleep(4) # 精度維持とブロック回避のため長めに待機
                    bar.progress((i + 1) / len(kw_list))
                
                df = pd.DataFrame(results)
                st.table(df)
                st.success("高精度分析が完了しました！")

if check_password():
    main()
