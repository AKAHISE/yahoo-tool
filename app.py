import streamlit as st

# 1. ページ設定
st.set_page_config(page_title="Yahoo Tool", layout="wide")

# 2. ログイン機能
def check_password():
    """パスワード認証を行う関数"""
    if "auth" not in st.session_state:
        st.session_state.auth = False

    if not st.session_state.auth:
        # ログイン画面
        st.title("🔐 ログイン")
        st.write("パスワードを入力してツールを起動してください。")
        
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        
        if st.button("Log in"):
            # Secretsと照合
            if user == st.secrets["auth"]["username"] and pw == st.secrets["auth"]["password"]:
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("パスワードが違います")
        return False
    return True

# 3. メインアプリ機能
def main():
    # サイドバー（メニュー）の作成
    st.sidebar.title("MENU")
    menu = st.sidebar.radio(
        "機能を選択してください",
        ["ホーム", "allintitle分析", "知恵袋リサーチ", "ブログ記事作成"]
    )

    # メニューごとの画面表示
    if menu == "ホーム":
        st.title("🏠 ホーム")
        st.success("ログイン成功！メニューから使いたいツールを選んでください。")
        st.info("👈 左側のサイドバーで機能を切り替えられます。")

    elif menu == "allintitle分析":
        st.title("🔍 allintitle分析")
        st.write("ここに「allintitle分析」の機能を復活させます（工事中...）")
        
    elif menu == "知恵袋リサーチ":
        st.title("🦉 知恵袋リサーチ")
        st.write("ここに「知恵袋リサーチ」の機能を復活させます（工事中...）")

    elif menu == "ブログ記事作成":
        st.title("📝 ブログ記事作成")
        st.write("ここに「ブログ作成」の機能を復活させます（工事中...）")

# --- アプリ実行 ---
if check_password():
    main()
