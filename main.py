import customtkinter as ctk
import sounddevice as sd
import pyaudiowpatch as pyaudio
import queue
import threading
import time
import os
from datetime import datetime
import pyperclip
from audio_processing import start_recording_vosk, start_recording_google, callback
from translation import RealTimeTranslator
from auth import AuthWindow
from gpt4o import GPT4o
import configparser

q_student, q_teacher = queue.Queue(), queue.Queue()
device = sd.default.device

start_time_student = [None]
start_time_teacher = [None]
current_text_student, current_text_teacher = "", ""
transcriptions, recording, program_start_time = [], False, time.time()

LANGUAGE_DISPLAY = ["Русский", "English", "Français", "Deutsch", "Español"]
LANGUAGE_CODES = {
    "Русский": "ru",
    "English": "en",
    "Français": "fr",
    "Deutsch": "de",
    "Español": "es"
}


class App(ctk.CTk):
    def __init__(self, user_info, session):
        super().__init__()

        self.title("АвтоРефлексия")
        self.iconbitmap("logo.ico")
        self.geometry("600x750")
        self.resizable(False, False)

        self.session = session
        self.token = self.load_token()

        self.label_name = ctk.CTkLabel(self, text=f"{user_info['firstName']} {user_info['lastName']}",
                                       font=("Arial", 14))
        self.label_name.place(x=25, y=40)

        self.textbox = ctk.CTkTextbox(self, width=550, height=300, state="disabled")
        self.textbox.place(x=25, y=70)

        self.device_var_student = ctk.StringVar(value="Не выбрано")
        self.device_var_teacher = ctk.StringVar(value="Не выбрано")
        self.recognition_method_var = ctk.StringVar(value="Vosk")
        self.language_var = ctk.StringVar(value=LANGUAGE_DISPLAY[0])
        self.translation_language_var = ctk.StringVar(value=LANGUAGE_DISPLAY[0])

        self.label = ctk.CTkLabel(self, text="Выберите микрофоны и метод распознавания:")
        self.label.place(x=175, y=370)

        self.device_dropdown_student = self.create_device_dropdown("У", self.device_var_student,
                                                                   self.change_device_student, output=True)
        self.device_dropdown_student.place(x=25, y=400)

        self.device_dropdown_teacher = self.create_device_dropdown("П", self.device_var_teacher,
                                                                   self.change_device_teacher, output=False)
        self.device_dropdown_teacher.place(x=325, y=400)

        self.recognition_method_dropdown = ctk.CTkOptionMenu(self, variable=self.recognition_method_var,
                                                             values=["Vosk", "Google"])
        self.recognition_method_dropdown.place(x=230, y=440)

        self.label_language = ctk.CTkLabel(self, text="Язык урока:")
        self.label_language.place(x=255, y=480)

        self.language_dropdown = ctk.CTkOptionMenu(self, variable=self.language_var, values=LANGUAGE_DISPLAY)
        self.language_dropdown.place(x=230, y=505)

        self.start_stop_button = ctk.CTkButton(self, text="Начать запись", command=self.toggle_recording,
                                               fg_color="green", state="disabled")
        self.start_stop_button.place(x=230, y=540)

        self.copy_button = ctk.CTkButton(self, text="Копировать текст", command=self.copy_text, fg_color="gray")
        self.copy_button.place(x=435, y=40)

        self.gpt_button = ctk.CTkButton(self, text="GPT-4o", command=self.open_gpt4o, fg_color='#3271a8')
        self.gpt_button.place(x=285, y=40)
        self.gpt4o = None

        self.translation_switch = ctk.CTkSwitch(self, text="Синхронный перевод", command=self.toggle_translation_window)
        self.translation_switch.place(x=210, y=600)

        self.label_translation_language = ctk.CTkLabel(self, text="Переводить на:")
        self.translation_language_dropdown = ctk.CTkOptionMenu(self, variable=self.translation_language_var,
                                                               values=LANGUAGE_DISPLAY)

        self.label_translation_language.place_forget()
        self.translation_language_dropdown.place_forget()

        self.translation_window = None
        self.translator = RealTimeTranslator()

        self.device_var_student.trace("w", self.check_device_selection)
        self.device_var_teacher.trace("w", self.check_device_selection)

        self.student_device_index = None
        self.teacher_device_index = None

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def on_closing(self):
        os._exit(0)

    def get_text(self):
        return self.textbox.get("1.0", ctk.END).strip()

    def load_token(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        return config.get('AUTH', 'token', fallback=None)

    def open_gpt4o(self):
        if self.gpt4o is None or not self.gpt4o.winfo_exists():
            self.gpt4o = GPT4o(self, self.session, self.token, self)
        else:
            self.gpt4o.deiconify()
        self.gpt4o.lift()

    def update_recording_time(self):
        while recording:
            elapsed_time = int(time.time() - program_start_time)
            minutes, seconds = divmod(elapsed_time, 60)
            self.start_stop_button.configure(text=f"Остановить ({minutes:02d}:{seconds:02d})")
            time.sleep(1)

    def create_device_dropdown(self, label_text, var, command, output):
        frame = ctk.CTkFrame(self)
        ctk.CTkLabel(frame, text=label_text).pack(side="left", padx=5)
        if output:
            dropdown = ctk.CTkOptionMenu(frame, variable=var, values=self.get_output_devices(), command=command)
        else:
            dropdown = ctk.CTkOptionMenu(frame, variable=var, values=self.get_input_devices(), command=command)
        dropdown.pack(side="left", padx=5)
        return frame

    def get_input_devices(self):
        p = pyaudio.PyAudio()
        devices = []
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                devices.append(device_info['name'])
        p.terminate()
        return ["Не выбрано"] + devices

    def get_output_devices(self):
        '''Заготовка для отказа от Virtual Audio Cable'''
        '''[LoopBack]'''
        p = pyaudio.PyAudio()
        devices = []
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                devices.append(device_info['name'])
        p.terminate()
        return ["Не выбрано"] + devices

    def check_device_selection(self, *args):
        state = "normal" if self.device_var_student.get() != "Не выбрано" and self.device_var_teacher.get() != "Не выбрано" else "disabled"
        self.start_stop_button.configure(state=state)

    def change_device(self, device_name, device_type):
        global samplerate
        if recording or device_name == "Не выбрано":
            return

        if device_type == 'student':
            p = pyaudio.PyAudio()
            for idx in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(idx)
                if device_info['name'] == device_name and device_info['maxInputChannels'] > 0:
                    self.student_device_index = idx
                    samplerate = int(device_info['defaultSampleRate'])
                    break
            p.terminate()
        else:
            p = pyaudio.PyAudio()
            for idx in range(p.get_device_count()):
                device_info = p.get_device_info_by_index(idx)
                if device_info['name'] == device_name and device_info['maxInputChannels'] > 0:
                    self.teacher_device_index = idx
                    samplerate = int(device_info['defaultSampleRate'])
                    break
            p.terminate()

    def change_device_student(self, device_name):
        self.change_device(device_name, 'student')

    def change_device_teacher(self, device_name):
        self.change_device(device_name, 'teacher')

    def toggle_recording(self):
        global recording, start_time_student, start_time_teacher, current_text_student, current_text_teacher, transcriptions, program_start_time
        if recording:
            recording = False
            self.start_stop_button.configure(text="Начать запись", fg_color="green")
            self.device_dropdown_student.place(x=25, y=400)
            self.device_dropdown_teacher.place(x=325, y=400)

            self.label.configure(text="Выберите микрофоны и метод распознавания:")
            self.label.place(x=175, y=370)
            self.label_language.configure(text="Язык урока:")
            self.label_language.place(x=255, y=480)

            self.recognition_method_dropdown.place(x=230, y=440)
            self.language_dropdown.place(x=230, y=505)
            self.save_transcriptions()
        else:
            recording = True
            self.start_stop_button.configure(text="Остановить (00:00)", fg_color="red")
            self.device_dropdown_student.place_forget()
            self.device_dropdown_teacher.place_forget()

            self.label.configure(text="Остановите запись")
            self.label.place(x=245, y=450)
            self.label_language.configure(text="чтобы увидеть элементы управления")
            self.label_language.place(x=185, y=480)

            self.recognition_method_dropdown.place_forget()
            self.language_dropdown.place_forget()
            self.textbox.configure(state="normal")
            self.textbox.delete(1.0, ctk.END)

            if self.translation_switch.get() and self.translation_window:
                self.translation_textbox.configure(state="normal")
                self.translation_textbox.delete(1.0, ctk.END)
                self.translation_textbox.configure(state="disabled")

            start_time_student[0], start_time_teacher[0] = None, None
            current_text_student, current_text_teacher, transcriptions = "", "", []
            program_start_time = time.time()
            recognition_method = self.recognition_method_var.get()
            language = LANGUAGE_CODES[self.language_var.get()]
            model_path = self.get_model_path(language)

            if recognition_method == "Vosk":
                threading.Thread(target=start_recording_vosk, args=(
                    q_student, 'У', self.student_device_index, samplerate, callback, start_time_student,
                    lambda: recording, program_start_time, transcriptions, self.update_text, model_path),
                                 daemon=True).start()
                threading.Thread(target=start_recording_vosk, args=(
                    q_teacher, 'П', self.teacher_device_index, samplerate, callback, start_time_teacher,
                    lambda: recording, program_start_time, transcriptions, self.update_text, model_path),
                                 daemon=True).start()
            elif recognition_method == "Google":
                threading.Thread(target=start_recording_google, args=(
                    q_student, 'У', self.student_device_index, samplerate, callback, start_time_student,
                    lambda: recording, program_start_time, transcriptions, self.update_text, language),
                                 daemon=True).start()
                threading.Thread(target=start_recording_google, args=(
                    q_teacher, 'П', self.teacher_device_index, samplerate, callback, start_time_teacher,
                    lambda: recording, program_start_time, transcriptions, self.update_text, language),
                                 daemon=True).start()

            threading.Thread(target=self.update_recording_time, daemon=True).start()

    def update_text(self, speaker, start_time, end_time, text):
        if self.translation_switch.get() and self.translation_language_var.get():
            translated_text = self.translator.translate_text(text, src_language=self.language_var.get(),
                                                             dest_language=self.translation_language_var.get())
            self.translation_textbox.configure(state="normal")
            self.translation_textbox.insert(ctk.END,
                                            f"{speaker} {time.strftime('%H:%M:%S', time.gmtime(start_time))}-{time.strftime('%H:%M:%S', time.gmtime(end_time))} {translated_text}\n")
            self.translation_textbox.see(ctk.END)
            self.translation_textbox.configure(state="disabled")
        self.textbox.configure(state="normal")
        self.textbox.insert(ctk.END,
                            f"{speaker} {time.strftime('%H:%M:%S', time.gmtime(start_time))}-{time.strftime('%H:%M:%S', time.gmtime(end_time))} {text}\n")
        self.textbox.see(ctk.END)
        self.textbox.configure(state="disabled")

    def save_transcriptions(self):
        if not transcriptions:
            return
        if not os.path.exists('Записи'):
            os.makedirs('Записи')
        filename = os.path.join('Записи', datetime.now().strftime('Запись_%Y.%m.%d_%H-%M-%S.txt'))
        with open(filename, 'w', encoding='utf-8') as f:
            for speaker, start, end, text in transcriptions:
                f.write(
                    f"{speaker} {time.strftime('%H:%M:%S', time.gmtime(start))}-{time.strftime('%H:%M:%S', time.gmtime(end))} {text}\n")

    def reset_copy_button(self):
        self.copy_button.configure(text="Копировать текст", fg_color="gray")

    def copy_text(self):
        text = self.textbox.get(1.0, ctk.END)
        pyperclip.copy(text)
        self.copy_button.configure(text="Скопировано!", fg_color="green")
        self.after(1000, self.reset_copy_button)

    def get_model_path(self, language_code):
        language_model_map = {
            "ru": "vosk-model-small-ru-0.22",
            "en": "vosk-model-small-en-us-0.15",
            "fr": "vosk-model-small-fr-0.22",
            "de": "vosk-model-small-de-0.15",
            "es": "vosk-model-small-es-0.42"
        }
        return language_model_map.get(language_code, "vosk-model-small-en-us-0.15")

    def toggle_translation_window(self):
        if self.translation_switch.get():
            self.label_translation_language.place(x=255, y=630)
            self.translation_language_dropdown.place(x=230, y=655)
            if self.translation_window is None or not self.translation_window.winfo_exists():
                self.translation_window = ctk.CTkToplevel(self)
                self.translation_window.title("Перевод")
                self.translation_window.geometry("400x300")

                self.translation_textbox = ctk.CTkTextbox(self.translation_window, width=380, height=200,
                                                          state="disabled")
                self.translation_textbox.pack(padx=10, pady=10)

                self.topmost_switch = ctk.CTkSwitch(self.translation_window, text="Поверх всех окон",
                                                    command=self.toggle_topmost)
                self.topmost_switch.pack(padx=10, pady=10)

                self.translation_window.protocol("WM_DELETE_WINDOW", self.on_translation_window_close)
        else:
            self.label_translation_language.place_forget()
            self.translation_language_dropdown.place_forget()
            if self.translation_window is not None and self.translation_window.winfo_exists():
                self.translation_window.destroy()
                self.translation_window = None

    def toggle_topmost(self):
        if self.topmost_switch.get():
            self.translation_window.attributes("-topmost", 1)
        else:
            self.translation_window.attributes("-topmost", 0)

    def on_translation_window_close(self):
        self.translation_switch.deselect()
        self.label_translation_language.place_forget()
        self.translation_language_dropdown.place_forget()
        self.translation_window.destroy()
        self.translation_window = None


def main():
    root = ctk.CTk()

    config_file = 'config.ini'
    config = configparser.ConfigParser()

    if os.path.exists(config_file):
        config.read(config_file)
        username = config.get('login', 'username', fallback='')
        password = config.get('login', 'password', fallback='')

        auth_window = AuthWindow(root)
        root.wait_window(auth_window)

        if hasattr(root, 'user_info') and root.user_info:
            app = App(root.user_info, auth_window.session)
            app.mainloop()
        else:
            print("Ошибка входа, кчао!")
            root.destroy()
    else:
        auth_window = AuthWindow(root)
        root.wait_window(auth_window)

        if hasattr(root, 'user_info') and root.user_info:
            app = App(root.user_info, auth_window.session)
            app.mainloop()
        else:
            print("Ошибка входа, кчао!")
            root.destroy()


if __name__ == "__main__":
    main()
