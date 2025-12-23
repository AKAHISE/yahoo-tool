import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

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

# メイン機能
def main():
    st.sidebar.title("MENU")
    menu = st.sidebar.radio("機能を選択", ["ホーム", "allintitle分析", "知恵袋リサーチ"])

    if menu == "ホーム":
        st.title("🏠 ホーム")
        st.success("ログイン成功！左メニューから機能を選んでください。")

    elif menu == "allintitle分析":
        st.title("🔍 allintitle分析")
        keywords = st.text_area("キーワードを1行ずつ入力してください")
        
        if st.button("分析開始"):
            if keywords:
                kw_list = keywords.split('\n')
                results = []
                bar = st.progress(0)
                
                for i, kw in enumerate(kw_list):
                    if kw.strip():
                        # ここでYahoo検索の件数を取得するシミュレーション
                        # ※実際のスクレイピングコードはここに記述
                        st.write(f"「{kw}」を調査中...")
                        time.sleep(1) # 負荷軽減
                        results.append({"キーワード": kw, "allintitle件数": "取得完了"})
                    bar.progress((i + 1) / len(kw_list))
                
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
