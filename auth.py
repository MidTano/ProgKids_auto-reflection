import customtkinter as ctk
import requests
import configparser
import os


class AuthWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Авторизация")
        self.geometry("300x200")
        self.resizable(False, False)

        self.session = requests.Session()

        self.config_file = 'config.ini'
        self.config = configparser.ConfigParser()

        if os.path.exists(self.config_file):
            self.config.read(self.config_file)
        else:
            self.config['login'] = {'username': '', 'password': ''}

        self.label_username = ctk.CTkLabel(self, text="Логин:")
        self.label_username.pack(pady=(10, 0))

        self.entry_username = ctk.CTkEntry(self)
        self.entry_username.pack(pady=(0, 5))
        self.entry_username.insert(0, self.config.get('login', 'username', fallback=''))

        self.label_password = ctk.CTkLabel(self, text="Пароль:")
        self.label_password.pack(pady=(0, 5))

        self.entry_password = ctk.CTkEntry(self, show="*")
        self.entry_password.pack(pady=(0, 0))
        self.entry_password.insert(0, self.config.get('login', 'password', fallback=''))

        self.login_button = ctk.CTkButton(self, text="Войти", command=self.login, fg_color='#3271a8')
        self.login_button.pack(pady=(5, 0))

    def reset_login_button(self):
        self.login_button.configure(text="Войти", fg_color='#3271a8')

    def login(self):
        username = self.entry_username.get()
        password = self.entry_password.get()

        user_info = self.authenticate(username, password)
        if user_info:
            self.config['login'] = {'username': username, 'password': password}
            with open(self.config_file, 'w') as configfile:
                self.config.write(configfile)
            self.master.user_info = user_info
            self.destroy()
        else:
            if 'login' in self.config:
                self.config.remove_section('login')
                with open(self.config_file, 'w') as configfile:
                    self.config.write(configfile)

            self.login_button.configure(text="Ошибка!", fg_color='red')
            self.after(1000, self.reset_login_button)

    def authenticate(self, username, password):
        url = "https://app.progkids.com/user/login"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "username": username,
            "password": password
        }
        response = self.session.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            user_info = self.check_logged_in()
            if user_info:
                user_info['username'] = username
                user_info['password'] = password
                return user_info
        print("Ошибка входа:", response.text)
        return None

    def check_logged_in(self):
        url = "https://app.progkids.com/user/profile"
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
            "Referer": "https://app.progkids.com/i/profile"
        }
        response = self.session.get(url, headers=headers)
        if response.status_code == 200:
            user_data = response.json()
            return {
                'firstName': user_data['firstName'],
                'lastName': user_data['lastName']
            }
        return None
