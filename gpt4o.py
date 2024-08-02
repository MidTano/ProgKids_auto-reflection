import customtkinter as ctk
import threading
import configparser
import re


class GPT4o(ctk.CTkToplevel):
    def __init__(self, master, session, token, texbox):
        super().__init__(master)

        self.texbox = texbox

        self.title("GPT-4o")
        self.geometry("700x600")
        self.minsize(700, 350)
        self.resizable(True, True)

        self.session = session
        self.token = token
        self.conversation_id = None

        self.config = self.load_config()

        self.reflection_text = self.config.get('PROMPTS', 'reflection', fallback='')
        self.evaluate_text = self.config.get('PROMPTS', 'evaluate', fallback='')

        self.response_textbox = ctk.CTkTextbox(self, width=550, height=200, state="normal", wrap="word")
        self.response_textbox.pack(pady=(10, 5), padx=10, fill="both", expand=True)

        self.reflection_button = ctk.CTkButton(self, text="Создать рефлексию", command=self.create_reflection,
                                               fg_color='#2980b9')
        self.reflection_button.pack(pady=(5, 0), padx=10, side="left")

        self.evaluate_button = ctk.CTkButton(self, text="Оценить урок", command=self.evaluate_lesson,
                                             fg_color='#27ae60')
        self.evaluate_button.pack(pady=(5, 5), padx=10, side="right")

        self.query_input = ctk.CTkTextbox(self, width=300, height=50, wrap="word")
        self.query_input.pack(pady=(5, 0), padx=10)
        self.query_input.bind("<KeyRelease>", self.update_send_button_state)

        self.send_button = ctk.CTkButton(self, text="Отправить запрос", command=self.start_gpt_test, fg_color='#3271a8',
                                         state="disabled")
        self.send_button.pack(pady=(5, 5), padx=10, side="top")

        self.clear_button = ctk.CTkButton(self, text="Очистить чат", command=self.clear_chat, fg_color='#e74c3c')
        self.clear_button.pack(pady=(5, 10), padx=10)

    def load_config(self):
        config = configparser.ConfigParser()
        with open('config.ini', 'r', encoding='utf-8') as f:
            config.read_file(f)
        return config

    def filter_response(self, text):
        pattern = re.compile(r'---.*(?:\n.*)*$', re.DOTALL)
        cleaned_text = re.sub(pattern, '', text)
        result_text = cleaned_text.strip()
        return result_text

    def start_gpt_test(self):
        user_query = self.query_input.get("1.0", ctk.END).strip()
        if not user_query:
            return

        self.response_textbox.insert(ctk.END, f"Вы:\n {user_query}\n\n\n", ("user_query"))
        self.query_input.delete('1.0', ctk.END)

        self.send_button.configure(state="disabled")
        thread = threading.Thread(target=self.gpt_Test, args=(user_query,))
        thread.start()

    def gpt_Test(self, user_query):
        url = "https://df.progkids.com/api/chat-messages"
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/123.0.0.0 Safari/537.36 OPR/109.0.0.0",
            "Referer": "https://app.progkids.com/i/profile",
            "Authorization": f"Bearer {self.token}"
        }
        payload = {
            "inputs": {},
            "query": user_query,
        }
        if self.conversation_id:
            payload["conversation_id"] = self.conversation_id

        try:
            response = self.session.post(url, json=payload, headers=headers, stream=False)

            if response.status_code == 200:
                data = response.json()
                answer = data.get('answer', '')
                filtered_answer = self.filter_response(answer)
                self.response_textbox.insert(ctk.END, f"GPT-4o:\n {filtered_answer}\n\n\n", ("gpt_response"))

                if not self.conversation_id:
                    thread = threading.Thread(target=self.send_second_request)
                    thread.start()
            else:
                error_message = f"Error: {response.status_code}\n{response.text}"
                self.response_textbox.insert(ctk.END, f"Ошибка: {error_message}\n\n", ("gpt_response"))

            self.response_textbox.yview_moveto(1.0)

        except Exception as e:
            self.response_textbox.insert(ctk.END, f"Ошибка: {str(e)}\n\n", ("gpt_response"))

        finally:
            self.send_button.configure(state="normal")

    def send_second_request(self):
        url = "https://df.progkids.com/api/conversations?limit=100&pinned=false"
        headers = {
            "Accept": "*/*",
            "Authorization": f"Bearer {self.token}"
        }
        try:
            response = self.session.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data["data"]:
                    self.conversation_id = data["data"][0]["id"]
                else:
                    print("Нет данных в ответе.")
            else:
                print(f"Ошибка: {response.status_code}\n{response.text}")

        except Exception as e:
            print(f"Ошибка при выполнении запроса: {str(e)}")

    def update_send_button_state(self, event):
        text = self.query_input.get("1.0", ctk.END).strip()
        if text:
            self.send_button.configure(state="normal")
        else:
            self.send_button.configure(state="disabled")

    def clear_chat(self):
        self.response_textbox.delete('1.0', ctk.END)
        self.conversation_id = None

    def create_reflection(self):
        full_query = f"{self.reflection_text}\n\n{self.texbox.get_text()}"
        self.response_textbox.insert(ctk.END, "Вы: Отправил запрос на создание рефлексии\n\n", ("user_query"))
        self.query_input.delete('1.0', ctk.END)

        self.send_button.configure(state="disabled")
        thread = threading.Thread(target=self.gpt_Test, args=(full_query,))
        thread.start()

    def evaluate_lesson(self):
        full_query = f"{self.evaluate_text}\n\n{self.texbox.get_text()}"
        self.response_textbox.insert(ctk.END, "Вы: Отправил запрос на оценку урока\n\n", ("user_query"))
        self.query_input.delete('1.0', ctk.END)

        self.send_button.configure(state="disabled")
        thread = threading.Thread(target=self.gpt_Test, args=(full_query,))
        thread.start()
