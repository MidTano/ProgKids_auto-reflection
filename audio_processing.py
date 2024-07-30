import sounddevice as sd
import vosk
import json
import queue
import time

model = vosk.Model('vosk-model-small-ru-0.22')
samplerate = int(sd.query_devices(sd.default.device[0], 'input')['default_samplerate'])

def callback(indata, frames, time, status, q):
    q.put(bytes(indata))

def recognize_speech(q, speaker, start_time, recording, program_start_time, transcriptions, update_text_callback):
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
                        transcriptions.append((speaker, start_time[0] - program_start_time, end_time - program_start_time, current_text.strip()))
                        update_text_callback(speaker, start_time[0] - program_start_time, end_time - program_start_time, current_text.strip())
                    else:
                        print(f"Ошибка типа: start_time[0]={start_time[0]}, end_time={end_time}")
                    current_text, start_time[0] = "", None
        except Exception as e:
            print(f"Ошибка в recognize_speech: {e}")

def start_recording(q, speaker, device_index, samplerate, callback, start_time, recording, program_start_time, transcriptions, update_text_callback):
    try:
        with sd.RawInputStream(samplerate=samplerate, blocksize=16000, device=device_index, dtype='int16', channels=1, callback=lambda indata, frames, time, status: callback(indata, frames, time, status, q)):
            recognize_speech(q, speaker, start_time, recording, program_start_time, transcriptions, update_text_callback)
    except Exception as e:
        print(f"Ошибка в start_recording: {e}")
