from deep_translator import GoogleTranslator


class RealTimeTranslator:
    def __init__(self):
        self.language_map = {
            "Русский": "ru",
            "English": "en",
            "Français": "fr",
            "Deutsch": "de",
            "Español": "es"
        }

    def translate_text(self, text, src_language, dest_language):
        src_code = self.language_map.get(src_language, 'en')
        dest_code = self.language_map.get(dest_language, 'en')

        if not text or not src_code or not dest_code:
            print("Ошибка перевода: Пустой текст или неверный язык.")
            return text

        try:
            translated = GoogleTranslator(source=src_code, target=dest_code).translate(text)
            if translated is None:
                raise ValueError("Получен пустой перевод.")
            return translated
        except Exception as e:
            print(f"Ошибка перевода: {e}")
            return text
