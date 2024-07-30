# ProgKids_auto-reflection

## Установка

Для установки и запуска выполните следующие шаги:

1. Клонируйте репозиторий:
    ```bash
    git clone https://github.com/MidTano/ProgKids_auto-reflection.git
    cd ProgKids_auto-reflection
    ```

2. Создайте и активируйте виртуальное окружение:
    ```bash
    python -m venv venv
    source venv/bin/activate   # Для Windows: venv\Scripts\activate
    ```

3. Установите зависимости:
    ```bash
    pip install -r requirements.txt
    ```

4. Запустите приложение:
    ```bash
    python main.py
    ```

## Использование

1. Выберите микрофоны для ученика и преподавателя.
2. Нажмите кнопку "Начать запись" для начала записи.
3. Нажмите кнопку "Остановить" для завершения записи.
4. Тексты будут отображены в текстовом поле.
5. Для копирования текста в буфер обмена нажмите кнопку "Копировать текст".

После завершенрия записи файл будет сохранен в папку, чтобы его можно было открыть в любое время

## Зависимости

- customtkinter
- sounddevice
- vosk
- pyperclip

