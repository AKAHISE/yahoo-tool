import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import urllib.parse

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

# Yahooから件数を取得する関数
def get_allintitle_count(keyword):
    search_query = f"allintitle:\"{keyword}\""
    encoded_query = urllib.parse.quote(search_query)
    url = f"https://search.yahoo.co.jp/search?p={encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Yahooの件数が表示される箇所を探す
        span_tags = soup.find_all("span")
        for span in span_tags:
            if "件" in span.text and ("約" in span.text or "1" in span.text):
                return span.text
        return "0件または取得失敗"
    except:
        return "エラー"

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
        keywords = st.text_area("キーワードを1行ずつ入力してください", height=200)
        
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
                    
                    # 負荷軽減とブロック防止のために少し待機
                    time.sleep(2)
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
