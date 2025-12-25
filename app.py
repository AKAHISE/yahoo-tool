import yaml
import streamlit as st
import pandas as pd
import time
import random
import re
from urllib.parse import unquote, urlparse, parse_qs

def load_cfg(path="config.yaml"):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

CFG = load_cfg()

RULES = (CFG.get("rules") or {})
SEARCH = ((CFG.get("search") or {}).get("yahoo") or {})

QA_DOMAINS = RULES.get("qa_domains", ["detail.chiebukuro.yahoo.co.jp"])
BLOG_DOMAINS = RULES.get("blog_domains", ["ameblo.jp","hatenablog.com","hatenablog.jp","hatena.blog","note.com","note.mu"])
EXCLUDE_DOMAINS = RULES.get("exclude_domains", ["search.yahoo.co.jp","help.yahoo.co.jp"])

TOP_N = int(SEARCH.get("top_n", 10))
SLEEP_MIN = float(SEARCH.get("sleep_min", 0.6))
SLEEP_MAX = float(SEARCH.get("sleep_max", 1.2))
ALLINTITLE_N = int(SEARCH.get("allintitle_n", 100))


# --- Selenium関連 ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ★追加：Wait系
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# --- 設定: 監視ターゲット ---
QA_DOMAINS = ["detail.chiebukuro.yahoo.co.jp"]
BLOG_DOMAINS = [
    "ameblo.jp",
    "hatenablog.com", "hatenablog.jp", "hatena.blog",
    "note.com", "note.mu"
]


# --- ブラウザ設定（Mac偽装・クラウド対応版） ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,1080")

    options.add_argument(
        "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    service = Service(executable_path="/usr/bin/chromedriver")
    options.binary_location = "/usr/bin/chromium"

    driver = webdriver.Chrome(service=service, options=options)
    return driver


# ===== ここから精度改善用のユーティリティ =====
def _normalize_host(url: str) -> str:
    try:
        p = urlparse(url)
        host = (p.netloc or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host
    except:
        return ""


def _extract_real_url(href: str) -> str:
    """
    YahooのリダイレクトURL (search.yahoo.co.jp/r/...) から実URLを復元する。
    取れなければ元を返す。
    """
    if not href:
        return href

    href = unquote(href)

    # すでに通常URL
    if "search.yahoo.co.jp/r/" not in href:
        return href

    # 例： .../RU=<encoded_url>/...
    m = re.search(r"RU=([^/]+)", href)
    if m:
        cand = unquote(m.group(1))
        if cand.startswith("http"):
            return cand

    # クエリパラメータ型
    try:
        qs = parse_qs(urlparse(href).query)
        for k in ("RU", "ru", "u", "url"):
            if k in qs and qs[k]:
                cand = unquote(qs[k][0])
                if cand.startswith("http"):
                    return cand
    except:
        pass

    return href


def _host_matches(host: str, domain_list: list[str]) -> bool:
    for d in domain_list:
        d = d.lower().lstrip(".")
        if host == d or host.endswith("." + d):
            return True
    return False


def _get_allintitle_count(driver) -> str:
    """
    allintitle件数を安定取得（候補領域→fallback）
    """
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )

    candidates = []
    selectors = ["#main", "div#main", "div.contents"]
    for sel in selectors:
        try:
            candidates.append(driver.find_element(By.CSS_SELECTOR, sel).text)
        except:
            pass

    try:
        candidates.append(driver.find_element(By.TAG_NAME, "body").text)
    except:
        pass

    joined = "\n".join([c for c in candidates if c])

    if "一致するウェブページは見つかりませんでした" in joined:
        return "0"

    m = re.search(r"約?\s*([\d,]+)\s*件", joined)
    if m:
        return m.group(1).replace(",", "")

    m2 = re.search(r"([\d,]+)\s*件", joined)
    if m2:
        return m2.group(1).replace(",", "")

    return "0"
# ===== ユーティリティここまで =====


# --- 解析ロジック ---
def analyze_yahoo(keyword, driver):
    result = {
        "keyword": keyword,
        "allintitle": "0",
        "qa_flag": False,
        "blog_flag": False,
        "debug_titles": []
    }

    try:
        wait = WebDriverWait(driver, 12)

        # --- 1) allintitle検索 ---
        driver.get(f'https://search.yahoo.co.jp/search?p=allintitle:"{keyword}"&n=100')
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(random.uniform(0.6, 1.2))

        try:
            result["allintitle"] = _get_allintitle_count(driver)
        except:
            result["allintitle"] = "取得失敗"

        # --- 2) 通常検索（Top10） ---
        driver.get(f"https://search.yahoo.co.jp/search?p={keyword}&ei=UTF-8")
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(random.uniform(0.6, 1.2))

        try:
            main_area = driver.find_element(By.ID, "main")
        except:
            main_area = driver

        cards = main_area.find_elements(By.CSS_SELECTOR, "div.sw-CardBase")
        if not cards:
            cards = main_area.find_elements(By.CSS_SELECTOR, "div.algo")

        valid_count = 0

        for card in cards:
            if valid_count >= 10:
                break

            try:
                if not card.is_displayed():
                    continue

                card_text = (card.text or "")

                # 広告系除外（順位ズレの主因）
                if "広告" in card_text or "スポンサー" in card_text or "Sponsored" in card_text:
                    continue

                # 原則 h3 a を使う（自然検索の精度を上げる）
                try:
                    title_link = card.find_element(By.CSS_SELECTOR, "h3 a")
                except:
                    # UI差分の救済
                    try:
                        title_link = card.find_element(By.CSS_SELECTOR, "a")
                    except:
                        continue

                raw_href = title_link.get_attribute("href")
                title_text = (title_link.text or "").strip().replace("\n", "")
                if not raw_href:
                    continue

                url = _extract_real_url(raw_href)
                if not url.startswith("http"):
                    continue

                # ゴミ除外
                if "search.yahoo.co.jp" in url or "help.yahoo.co.jp" in url:
                    continue

                host = _normalize_host(url)

                valid_count += 1

                detected_qa = _host_matches(host, QA_DOMAINS) or ("Yahoo!知恵袋" in card_text)
                detected_blog = _host_matches(host, BLOG_DOMAINS)

                if detected_qa:
                    result["qa_flag"] = True
                if detected_blog:
                    result["blog_flag"] = True

                result["debug_titles"].append(
                    f"【{valid_count}位】{title_text[:30]} ({host})"
                )

            except:
                continue

    except Exception:
        result["allintitle"] = "エラー"

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

    st.title("🔍 Yahoo! 徹底攻略ツール (Mac偽装版)")

    raw_text = st.text_area("キーワードを1行ずつ入力", height=200)
    target_list = [line.strip() for line in raw_text.split('\n') if line.strip()]

    if st.button("調査開始"):
        if not target_list:
            return

        status = st.empty()
        status.info("🚀 エンジン起動中...")

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

            status.success("✅ 完了！")
            df = pd.DataFrame(results)

            df["知恵袋"] = df["qa_flag"].apply(lambda x: "あり" if x else "")
            df["無料ブログ"] = df["blog_flag"].apply(lambda x: "あり" if x else "")

            st.dataframe(
                df[["keyword", "allintitle", "知恵袋", "無料ブログ"]],
                use_container_width=True
            )

            with st.expander("【答え合わせ】検出タイトル"):
                st.dataframe(df[["keyword", "debug_titles"]])

        except Exception as e:
            st.error(f"エラー: {e}")
        finally:
            try:
                driver.quit()
            except:
                pass


if __name__ == "__main__":
    main()
