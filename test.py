import time
import requests

# Вставьте сюда ваш настоящий токен, полученный в dev.max.ru
TOKEN = "f9LHodD0cOIbrEOIdO2KtQhHu6oFF5dP-zMhJ0d2jMvIO_sEO4pJKYDuIiMSK0MHTfYuUgkIeaKDaTIcFdH_"
BASE_URL = f"https://max.ru/{TOKEN}"


def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    # timeout лучше уменьшить до 30-50 секунд, чтобы скрипт не зависал долго
    params = {"timeout": 30, "offset": offset}
    response = requests.get(url, params=params)
    # Проверяем, что сервер вернул успешный статус (200 OK)
    response.raise_for_status()
    return response.json()


def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    response = requests.post(url, json=payload)
    response.raise_for_status()


def main():
    last_update_id = None
    print("Бот запущен...")

    while True:
        try:
            updates = get_updates(last_update_id)
            if "result" in updates and updates["result"]:
                for update in updates["result"]:
                    # Смещаем offset на +1 относительно текущего update_id
                    last_update_id = update["update_id"] + 1

                    message = update.get("message")
                    if message and "text" in message:
                        chat_id = message["chat"]["id"]
                        user_text = message["text"]

                        # Эхо-логика
                        send_message(chat_id, f"Вы написали: {user_text}")

        except requests.exceptions.RequestException as req_err:
            print(f"Ошибка сети/API: {req_err}")
            time.sleep(5)
        except Exception as e:
            print(f"Непредвиденная ошибка: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
