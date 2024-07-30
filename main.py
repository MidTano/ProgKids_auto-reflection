import customtkinter as ctk
import sounddevice as sd
import queue
import threading
import time
import os
from datetime import datetime
import pyperclip
from audio_processing import start_recording, callback

q_student, q_teacher = queue.Queue(), queue.Queue()
device = sd.default.device
samplerate = int(sd.query_devices(device[0], 'input')['default_samplerate'])

start_time_student = [None]
start_time_teacher = [None]
current_text_student, current_text_teacher = "", ""
transcriptions, recording, program_start_time = [], False, time.time()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("АвтоРефлексия")
        self.iconbitmap("logo.ico")
        self.geometry("600x700")
        self.resizable(False, False)

        self.textbox = ctk.CTkTextbox(self, width=550, height=350)
        self.textbox.pack(padx=10, pady=10)

        self.device_var_student = ctk.StringVar(value="Не выбрано")
        self.device_var_teacher = ctk.StringVar(value="Не выбрано")
        self.device_dropdown_student = self.create_device_dropdown("Выберите микрофон ученика:", self.device_var_student, self.change_device_student)
        self.device_dropdown_teacher = self.create_device_dropdown("Выберите микрофон преподавателя:", self.device_var_teacher, self.change_device_teacher)

        self.start_stop_button = ctk.CTkButton(self, text="Начать запись", command=self.toggle_recording, fg_color="green", state="disabled")
        self.start_stop_button.pack(padx=10, pady=10)

        self.copy_button = ctk.CTkButton(self, text="Копировать текст", command=self.copy_text,fg_color="gray")
        self.copy_button.pack(padx=10, pady=10)

        self.device_var_student.trace("w", self.check_device_selection)
        self.device_var_teacher.trace("w", self.check_device_selection)

    def create_device_dropdown(self, label_text, var, command):
        ctk.CTkLabel(self, text=label_text).pack(padx=10, pady=5)
        dropdown = ctk.CTkOptionMenu(self, variable=var, values=self.get_input_devices(), command=command)
        dropdown.pack(padx=10, pady=5)
        return dropdown

    def get_input_devices(self):
        return ["Не выбрано"] + [d['name'] for d in sd.query_devices() if d['max_input_channels'] > 0]

    def check_device_selection(self, *args):
        state = "normal" if self.device_var_student.get() != "Не выбрано" and self.device_var_teacher.get() != "Не выбрано" else "disabled"
        self.start_stop_button.configure(state=state)

    def change_device(self, device_name, device_type):
        global samplerate
        if recording or device_name == "Не выбрано":
            return
        for idx, d in enumerate(sd.query_devices()):
            if d['name'] == device_name and d['max_input_channels'] > 0:
                if device_type == 'student':
                    self.student_device_index = idx
                else:
                    self.teacher_device_index = idx
                break
        samplerate = int(sd.query_devices(self.student_device_index if device_type == 'student' else self.teacher_device_index, 'input')['default_samplerate'])

    def change_device_student(self, device_name):
        self.change_device(device_name, 'student')

    def change_device_teacher(self, device_name):
        self.change_device(device_name, 'teacher')

    def toggle_recording(self):
        global recording, start_time_student, start_time_teacher, current_text_student, current_text_teacher, transcriptions, program_start_time
        if recording:
            recording = False
            self.start_stop_button.configure(text="Начать запись", fg_color="green")
            self.device_dropdown_student.configure(state="normal")
            self.device_dropdown_teacher.configure(state="normal")
            self.save_transcriptions()
        else:
            recording = True
            self.start_stop_button.configure(text="Остановить (00:00)", fg_color="red")
            self.device_dropdown_student.configure(state="disabled")
            self.device_dropdown_teacher.configure(state="disabled")
            self.textbox.delete(1.0, ctk.END)
            start_time_student[0], start_time_teacher[0] = None, None
            current_text_student, current_text_teacher, transcriptions = "", "", []
            program_start_time = time.time()
            threading.Thread(target=start_recording, args=(q_student, 'У', self.student_device_index, samplerate, callback, start_time_student, lambda: recording, program_start_time, transcriptions, self.update_text), daemon=True).start()
            threading.Thread(target=start_recording, args=(q_teacher, 'П', self.teacher_device_index, samplerate, callback, start_time_teacher, lambda: recording, program_start_time, transcriptions, self.update_text), daemon=True).start()
            threading.Thread(target=self.update_recording_time, daemon=True).start()

    def update_recording_time(self):
        while recording:
            elapsed_time = int(time.time() - program_start_time)
            minutes, seconds = divmod(elapsed_time, 60)
            self.start_stop_button.configure(text=f"Остановить ({minutes:02d}:{seconds:02d})")
            time.sleep(1)

    def update_text(self, speaker, start_time, end_time, text):
        self.textbox.insert(ctk.END, f"{speaker} {time.strftime('%H:%M:%S', time.gmtime(start_time))}-{time.strftime('%H:%M:%S', time.gmtime(end_time))} {text}\n")
        self.textbox.see(ctk.END)

    def copy_text(self):
        text = self.textbox.get(1.0, ctk.END)
        pyperclip.copy(text)
        self.copy_button.configure(text="Скопировано!", fg_color="green")
        self.after(1000, self.reset_copy_button)

    def reset_copy_button(self):
        self.copy_button.configure(text="Копировать текст", fg_color="gray")

    def save_transcriptions(self):
        try:
            folder_name = f"Запись {datetime.now().strftime('%Y.%m.%d %H.%M.%S')}"
            os.makedirs(folder_name, exist_ok=True)
            with open(os.path.join(folder_name, "transcriptions.txt"), "w", encoding="utf-8") as f:
                for speaker, start, end, text in transcriptions:
                    f.write(f"{speaker} {time.strftime('%H:%M:%S', time.gmtime(start))}-{time.strftime('%H:%M:%S', time.gmtime(end))} {text}\n")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
