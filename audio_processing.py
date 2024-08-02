import sounddevice as sd
import vosk
import json
import time
import speech_recognition as sr
import threading

model = vosk.Model('vosk-model-small-ru-0.22')
google_time = 10


def callback(indata, frames, time, status, q):
    q.put(bytes(indata))


def recognize_speech_vosk(q, speaker, start_time, recording, program_start_time, transcriptions, update_text_callback,
                          samplerate, model):
    rec = vosk.KaldiRecognizer(model, samplerate)
    current_text = ""
    while recording():
        try:
            data = q.get()
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result()).get("text", "")
                if result:
                    if start_time[0] is None:
                        start_time[0] = time.time()
                    current_text += " " + result
            else:
                partial = json.loads(rec.PartialResult()).get("partial")
                if start_time[0] is None and partial:
                    start_time[0] = time.time()
                if not partial and current_text:
                    end_time = time.time()
                    if isinstance(start_time[0], (int, float)) and isinstance(end_time, (int, float)):
                        transcriptions.append((speaker, start_time[0] - program_start_time,
                                               end_time - program_start_time, current_text.strip()))
                        update_text_callback(speaker, start_time[0] - program_start_time, end_time - program_start_time,
                                             current_text.strip())
                    else:
                        print(f"Ошибка типа: start_time[0]={start_time[0]}, end_time={end_time}")
                    current_text, start_time[0] = "", None
        except Exception as e:
            print(f"Ошибка в recognize_speech_vosk: {e}")


def recognize_speech_google(buffer, speaker, start_time, program_start_time, transcriptions, update_text_callback,
                            samplerate, language):
    recognizer = sr.Recognizer()
    audio_data = sr.AudioData(buffer, samplerate, 2)
    try:
        result = recognizer.recognize_google(audio_data, language=language)
        if result:
            end_time = time.time()
            transcriptions.append(
                (speaker, start_time[0] - program_start_time, end_time - program_start_time, result.strip()))
            update_text_callback(speaker, start_time[0] - program_start_time, end_time - program_start_time,
                                 result.strip())
    except sr.UnknownValueError:
        pass
    except sr.RequestError as e:
        print(f"Ошибка запроса к Google API: {e}")


def start_recording_vosk(q, speaker, device_index, samplerate, callback, start_time, recording, program_start_time,
                         transcriptions, update_text_callback, model_path):
    try:
        model = vosk.Model(model_path)
        with sd.RawInputStream(samplerate=samplerate, blocksize=16000, device=device_index, dtype='int16', channels=1,
                               callback=lambda indata, frames, time, status: callback(indata, frames, time, status, q)):
            recognize_speech_vosk(q, speaker, start_time, recording, program_start_time, transcriptions,
                                  update_text_callback, samplerate, model)
    except Exception as e:
        print(f"Ошибка в start_recording_vosk: {e}")


def start_recording_google(q, speaker, device_index, samplerate, callback, start_time, recording, program_start_time,
                           transcriptions, update_text_callback, language):
    def record_and_recognize():
        while recording():
            buffer = bytes()
            start_time[0] = time.time()
            try:
                with sd.RawInputStream(samplerate=samplerate, blocksize=int(samplerate * google_time),
                                       device=device_index, dtype='int16', channels=1,
                                       callback=lambda indata, frames, time, status: q.put(bytes(indata))):
                    while len(buffer) < int(samplerate * google_time):
                        data = q.get()
                        buffer += data

                recognize_speech_google(buffer, speaker, start_time, program_start_time, transcriptions,
                                        update_text_callback, samplerate, language)
            except Exception as e:
                print(f"Ошибка в record_and_recognize: {e}")

    threading.Thread(target=record_and_recognize, daemon=True).start()
