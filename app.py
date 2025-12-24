import streamlit as st
import pandas as pd
import time
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- ブラウザ設定（クラウド環境・安定版） ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # 人間に見せかけるためのUser-Agent設定
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # クラウド上のChromiumとDriverを直接指定
    service = Service(executable_path="/usr/bin/chromedriver")
    options.binary_location = "/usr/bin/chromium"
    
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- 解析ロジック (超高精度・実数カウント版) ---
def analyze_yahoo(keyword, driver):
    result = {"キーワード": keyword, "allintitle件数": "0"}
    try:
        # allintitle検索を実行
        url = f"https://search.yahoo.co.jp/search?p=allintitle:\"{keyword}\""
        driver.get(url)
        time.sleep(random.uniform(4.0, 6.0)) # Yahooのブロックを避けるため慎重に待機

        # ページ全体のテキストを取得
        body_text = driver.find_element(By.TAG_NAME, "body").text
        
        # 1. 「一致するウェブページは見つかりませんでした」がある場合は0確定
        if "一致するウェブページは見つかりませんでした" in body_text:
            result["allintitle件数"] = "0"
            return result

        # 2. 検索結果の統計情報が表示されている場所を特定して数字を抜く
        # パターンA: 「約1,990件」のような形式
        # パターンB: 「1件〜10件 / 約153件」のような形式
        
        # 正規表現で「最後の数字 + 件」を狙い撃ちする（総件数は通常最後に表示されるため）
        counts = re.findall(r'([\d,]+)件', body_text)
        
        if counts:
            # 取得した「◯件」の中で、最も総件数らしいもの（通常はリストの最後の方）を選択
            # ただし、広告件数などを拾わないよう工夫
            candidate = "0"
            for c in reversed(counts):
                num = int(c.replace(',', ''))
                if num > 0:
                    candidate = c
                    break
            result["allintitle件数"] = candidate
        else:
            result["allintitle件数"] = "0"

    except Exception as e:
        result["allintitle件数"] = "取得失敗"
    return result

# --- メイン画面 ---
def main():
    st.set_page_config(page_title="Yahoo高精度分析", layout="wide")
    
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
                st.error("認証失敗")
        return

    st.title("🔍 Yahoo! allintitle分析 (高精度Selenium版)")
    
    raw_text = st.text_area("キーワードを1行ずつ入力", height=200)
    target_list = [line.strip() for line in raw_text.split('\n') if line.strip()]

    if st.button("調査開始"):
        if not target_list:
            st.warning("キーワードを入力してください")
            return

        status = st.empty()
        status.info("🚀 高精度エンジンを起動中...")
        
        try:
            driver = get_driver()
            results = []
            bar = st.progress(0)
            
            for i, kw in enumerate(target_list):
                status.info(f"🔎 調査中 ({i+1}/{len(target_list)}): {kw}")
                data = analyze_yahoo(kw, driver)
                results.append(data)
                bar.progress((i + 1) / len(target_list))
                time.sleep(random.uniform(2.0, 4.0))
            
            status.success("✅ 調査完了！")
            df = pd.DataFrame(results)
            st.table(df)
            
        except Exception as e:
            st.error(f"起動エラー: {e}")
        finally:
            if 'driver' in locals():
                driver.quit()

if __name__ == "__main__":
    main()
