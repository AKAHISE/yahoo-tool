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

# Yahooから件数を取得する強化版関数
def get_allintitle_count(keyword):
    # クエリを作成（allintitle:"キーワード"）
    search_query = f'allintitle:"{keyword}"'
    encoded_query = urllib.parse.quote(search_query)
    url = f"https://search.yahoo.co.jp/search?p={encoded_query}"
    
    # 人間のブラウザを装うための詳細なヘッダー
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        "Referer": "https://www.yahoo.co.jp/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        # ページ全体のテキストから「約◯◯件」や「1件〜◯◯件」を探す
        full_text = soup.get_text()
        
        # 正規表現で「◯件」というパターンを抽出
        matches = re.findall(r'([0-9,]+)件', full_text)
        
        if matches:
            # 検索結果件数に近いもの（通常は最初の方に出てくる大きな数字）を返す
            # 「約」がついているものを優先
            found_count = "0"
            for m in matches:
                if len(m.replace(',', '')) > 0:
                    found_count = m
                    break
            return f"約 {found_count} 件"
        
        return "0件（または制限中）"
    except Exception as e:
        return f"エラー: {str(e)}"

# メイン機能
def main():
    st.sidebar.title("MENU")
    menu = st.sidebar.radio("機能を選択", ["ホーム", "allintitle分析", "知恵袋リサーチ"])

    if menu == "ホーム":
        st.title("🏠 ホーム")
        st.success("ログイン成功！左メニューから機能を選んでください。")

    elif menu == "allintitle分析":
        st.title("🔍 allintitle分析")
        st.info("Yahoo検索で 'allintitle:\"キーワード\"' の結果件数を調査します。")
        keywords = st.text_area("キーワードを1行ずつ入力してください", height=200, placeholder="例: ペルテック 電動自転車 修理")
        
        if st.button("分析開始"):
            if keywords:
                kw_list = [k.strip() for k in keywords.split('\n') if k.strip()]
                results = []
                bar = st.progress(0)
                status_text = st.empty()
                
                for i, kw in enumerate(kw_list):
                    status_text.write(f"🔎 調査中 ({i+1}/{len(kw_list)}): {kw}")
                    count = get_allintitle_count(kw)
                    results.append({"キーワード": kw, "allintitle件数": count})
                    
                    # 連続アクセスでブロックされないよう、少し長めに待機
                    time.sleep(3) 
                    bar.progress((i + 1) / len(kw_list))
                
                status_text.empty()
                df = pd.DataFrame(results)
                st.table(df)
                st.success("分析が完了しました！")
            else:
                st.warning("キーワードを入力してください")

    elif menu == "知恵袋リサーチ":
        st.title("🦉 知恵袋リサーチ")
        st.write("次にここを開発しましょう！")

if check_password():
    main()
