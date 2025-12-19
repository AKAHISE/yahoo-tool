import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

import pandas as pd
import time
import random
import re
from urllib.parse import unquote
import os

# --- Selenium関連 ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# --- 設定: 監視ターゲット ---
QA_DOMAINS = ["detail.chiebukuro.yahoo.co.jp"]
BLOG_DOMAINS = [
    "ameblo.jp", "hatenablog.com", "hatenablog.jp", "hatena.blog",
    "note.com", "note.mu"
]

# --- ブラウザ設定関数（クラウド対応版） ---
def get_driver():
    options = Options()
    
    # ★ここが追加ポイント！「画面なし」で動かす設定
    options.add_argument("--headless") 
    
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument("--window-size=1280,1080")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- 解析ロジック ---
def analyze_yahoo_selenium(keyword, driver):
    result = {
        "keyword": keyword,
        "allintitle": None,
        "qa_flag": False,
        "blog_flag": False,
        "debug_titles": [] 
    }
    try:
        # 1. allintitle
        driver.get(f"https://search.yahoo.co.jp/search?p=allintitle:{keyword}&ei=UTF-8")
        time.sleep(random.uniform(1.5, 2.5))
        try:
            body_text = driver.find_element(By.TAG_NAME, "body").text
            match = re.search(r'([\d,]+)\s*件', body_text)
            if match:
                result["allintitle"] = int(match.group(1).replace(',', ''))
            elif "一致する情報は" in body_text:
                result["allintitle"] = 0
        except:
            pass

        # 2. 通常検索
        driver.get(f"https://search.yahoo.co.jp/search?p={keyword}&ei=UTF-8")
        time.sleep(random.uniform(2.5, 4.0))
        
        try: main_area = driver.find_element(By.ID, "main")
        except: main_area = driver
        
        cards = main_area.find_elements(By.CSS_SELECTOR, "div.sw-CardBase")
        if len(cards) == 0: cards = main_area.find_elements(By.CSS_SELECTOR, "div.algo")
        if len(cards) == 0: cards = main_area.find_elements(By.XPATH, "//h3/ancestor::div[contains(@class, 'sw-CardBase') or position()=1]")

        valid_count = 0
        for card in cards:
            try:
                if not card.is_displayed(): continue
                
                title_link = None
                try: title_link = card.find_element(By.CSS_SELECTOR, "h3 a")
                except: pass
                if not title_link:
                    try: title_link = card.find_element(By.CSS_SELECTOR, "div[class*='Title'] a")
                    except: pass
                if not title_link:
                    try: 
                        links = card.find_elements(By.TAG_NAME, "a")
                        if links: title_link = links[0]
                    except: pass

                if title_link:
                    raw_url = title_link.get_attribute("href")
                    title_text = title_link.text.strip().replace("\n", "")
                    card_text = card.text
                    
                    if raw_url:
                        url = unquote(raw_url)
                        if "search.yahoo.co.jp" in url: continue
                        if "help.yahoo.co.jp" in url: continue
                        if "http" in url:
                            valid_count += 1
                            detected_qa = False
                            detected_blog_name = ""
                            
                            for qa_domain in QA_DOMAINS:
                                if qa_domain in url: detected_qa = True
                            if "Yahoo!知恵袋" in card_text: detected_qa = True
                            if detected_qa: result["qa_flag"] = True
                            
                            for blog in BLOG_DOMAINS:
                                if blog in url:
                                    result["blog_flag"] = True
                                    detected_blog_name = blog
                            
                            log_text = f"【{valid_count}位】{title_text[:15]}..."
                            if detected_blog_name: log_text += f" [検知: {detected_blog_name}]"
                            elif detected_qa: log_text += " [検知: 知恵袋]"
                            else: log_text += f" ({url[:20]}...)"
                            result["debug_titles"].append(log_text)
            except: continue
            if valid_count >= 10: break
    except Exception as e:
        st.error(f"エラー: {e}")
    return result

# --- メイン画面 ---
def main():
    st.set_page_config(page_title="Yahoo! KW分析ツール SaaS版", layout="wide")

    # --- 1. ユーザー台帳の読み込み ---
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)

    # --- 2. 認証オブジェクトの作成 ---
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        preauthorized=config['preauthorized']
    )

    # --- 3. ログイン画面の表示 (Ver 0.4.x対応) ---
    # ここが変わりました！戻り値を受け取らず、内部処理させます
    authenticator.login()

    # --- 4. 認証結果による分岐 ---
    # st.session_stateを使って判定します
    if st.session_state["authentication_status"]:
        # === ログイン成功 ===
        
        with st.sidebar:
            st.write(f'ようこそ **{st.session_state["name"]}** さん')
            authenticator.logout() # ログアウトボタン
            st.divider()
            st.info("プラン: スタンダード")

        # アプリ本体
        st.title("Yahoo! KW分析ツール (会員専用)")
        
        col1, col2 = st.columns([1, 2])
        with col1:
            st.success("ログイン認証済み")
            st.markdown("""
            **🔐 セキュリティ保護中**
            会員専用ページへようこそ。
            機能はフルパワーで使用可能です。
            """)

        with col2:
            raw_text = st.text_area("キーワード貼り付け", height=300)
            target_list = [line.strip() for line in raw_text.split('\n') if line.strip()]
            
            if st.button("調査開始"):
                if not target_list: return
                
                st.success("ブラウザ起動中...")
                try:
                    driver = get_driver()
                    results = []
                    bar = st.progress(0)
                    
                    for i, kw in enumerate(target_list):
                        data = analyze_yahoo_selenium(kw, driver)
                        results.append(data)
                        bar.progress((i + 1) / len(target_list))
                        time.sleep(1.0)
                    
                    st.success("完了！")
                    df = pd.DataFrame(results)
                    
                    if not df.empty:
                        df['allintitle'] = df['allintitle'].astype('Int64')
                        df['知恵袋'] = df['qa_flag'].apply(lambda x: 'あり' if x else '')
                        df['無料ブログ'] = df['blog_flag'].apply(lambda x: 'あり' if x else '')
                        
                        st.dataframe(
                            df[['keyword', 'allintitle', '知恵袋', '無料ブログ']], 
                            use_container_width=True,
                            column_config={"allintitle": st.column_config.NumberColumn(format="%d")}
                        )
                        
                        with st.expander("【答え合わせ】検出タイトル"):
                            st.dataframe(df[['keyword', 'debug_titles']])
                finally:
                    driver.quit()

    elif st.session_state["authentication_status"] is False:
        st.error('ユーザー名またはパスワードが間違っています')
    elif st.session_state["authentication_status"] is None:
        st.warning('ユーザー名とパスワードを入力してください')

if __name__ == "__main__":
    main()