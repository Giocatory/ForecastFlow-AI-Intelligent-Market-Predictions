import streamlit as st
import hashlib
import json
import os

USERS_FILE = "users.json"

def init_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'username' not in st.session_state:
        st.session_state.username = ''
    if 'tokens' not in st.session_state:
        st.session_state.tokens = {}

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user(username, password):
    users = load_users()
    users[username] = {
        'password': hashlib.sha256(password.encode()).hexdigest()
    }
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

def authenticate(username, password):
    users = load_users()
    if username in users:
        return users[username]['password'] == hashlib.sha256(password.encode()).hexdigest()
    return False

def render_auth_sidebar():
    init_session_state()
    
    st.sidebar.title("🔐 Аутентификация")
    
    if not st.session_state.authenticated:
        tab1, tab2 = st.sidebar.tabs(["Вход", "Регистрация"])
        
        with tab1:
            username = st.text_input("Имя пользователя", key="login_user")
            password = st.text_input("Пароль", type="password", key="login_pass")
            
            if st.button("Войти", key="login_btn"):
                if username and password:
                    if authenticate(username, password):
                        st.session_state.authenticated = True
                        st.session_state.username = username
                        st.rerun()
                    else:
                        st.error("Неверные учетные данные")
                else:
                    st.error("Заполните все поля")
        
        with tab2:
            new_user = st.text_input("Новое имя пользователя", key="reg_user")
            new_pass = st.text_input("Новый пароль", type="password", key="reg_pass")
            confirm_pass = st.text_input("Подтвердите пароль", type="password", key="confirm_pass")
            
            if st.button("Зарегистрироваться", key="reg_btn"):
                if new_user and new_pass:
                    if new_pass == confirm_pass:
                        save_user(new_user, new_pass)
                        st.success("Регистрация успешна! Теперь войдите в систему.")
                    else:
                        st.error("Пароли не совпадают")
                else:
                    st.error("Заполните все поля")
    else:
        st.sidebar.success(f"👋 Добро пожаловать, {st.session_state.username}!")
        
        st.sidebar.subheader("🔑 Настройки API")
        avito_token = st.sidebar.text_input("Avito API Token", type="password")
        hh_token = st.sidebar.text_input("HH API Token", type="password")
        
        if avito_token:
            st.session_state.tokens['avito'] = avito_token
        if hh_token:
            st.session_state.tokens['hh'] = hh_token
        
        if st.sidebar.button("🚪 Выйти"):
            st.session_state.authenticated = False
            st.session_state.username = ''
            st.session_state.tokens = {}
            st.rerun()
    
    return st.session_state.authenticated