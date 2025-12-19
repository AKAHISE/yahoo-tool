import streamlit as st

# ページ設定
st.set_page_config(page_title="Yahoo Tool", page_icon="🛍️")

# ログイン機能
def check_password():
    def password_guessed():
        # Secretsからユーザー名とパスワードを照合
        if (st.session_state["username"] == st.secrets["auth"]["username"] and
            st.session_state["password"] == st.secrets["auth"]["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # セキュリティのため削除
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # 初回表示
        st.text_input("Username", key="username")
        st.text_input("Password", type="password", key="password")
        if st.button("Log in"):
            password_guessed()
            if not st.session_state.get("password_correct", False):
                st.error("😕 ユーザー名またはパスワードが違います")
                st.stop()
            st.rerun()
        return False
    else:
        return True

# ログイン後のメイン画面
if check_password():
    st.title("✅ Yahooツールへようこそ")
    st.success("ログインに成功しました！アプリは正常に稼働しています。")
    st.write("ここから自動化ツールを構築していきましょう。")