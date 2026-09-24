import requests
import certifi
import os
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("max-bot")

# ===========================================================================
#  Настройка сертификатов: certifi + корневые/промежуточные сертификаты Минцифры
# ===========================================================================

# URL официальных сертификатов НУЦ Минцифры (источник — сайт Госуслуг)
MINCIFRY_CERTS = {
    "root":           "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt",
    "sub":            "https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt",
    "sub_2024":       "https://gu-st.ru/content/lending/russian_trusted_sub_ca_2024_pem.crt",
    "root_gost_2025": "https://gu-st.ru/content/lending/russian_trusted_root_ca_gost_2025_pem.crt",
    "sub_gost_2025":  "https://gu-st.ru/content/lending/russian_trusted_sub_ca_gost_2025_pem.crt",
}

# Папка рядом со скриптом
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
BUNDLE_DIR  = os.path.join(SCRIPT_DIR, "certs")
BUNDLE_FILE = os.path.join(BUNDLE_DIR, "combined-ca-bundle.pem")


def build_combined_bundle():
    """
    Создаёт объединённый CA-bundle: certifi + сертификаты Минцифры.

    Принцип:
      1. Берём стандартный bundle из certifi (сотни доверенных CA).
      2. Дописываем в конец корневые и промежуточные сертификаты Минцифры.
      3. Сохраняем в отдельный файл — НЕ модифицируем certifi напрямую
         (иначе при обновлении пакета изменения затрутся).

    Источник сертификатов: https://www.gosuslugi.ru/crt
    """
    os.makedirs(BUNDLE_DIR, exist_ok=True)

    # 1. Базовый bundle из certifi
    with open(certifi.where(), "r", encoding="utf-8") as f:
        base_certs = f.read()
    log.info("Базовый certifi bundle: %s (%d байт)", certifi.where(), len(base_certs))

    # 2. Скачиваем сертификаты Минцифры
    #    verify=False для самого gu-st.ru, т.к. он тоже может использовать
    #    сертификат Минцифры (замкнутый круг). Альтернатива — скачать вручную
    #    с https://www.gosuslugi.ru/crt и положить .crt файлы в папку certs/.
    extra_certs = []
    for name, url in MINCIFRY_CERTS.items():
        cert_path = os.path.join(BUNDLE_DIR, f"{name}.pem")

        # Если файл уже скачан ранее — используем локальную копию
        if os.path.exists(cert_path):
            with open(cert_path, "r", encoding="utf-8") as f:
                pem = f.read().strip()
            if "BEGIN CERTIFICATE" in pem:
                extra_certs.append(pem)
                log.info("Сертификат взят из локальной копии: %s", name)
                continue

        # Иначе скачиваем
        try:
            resp = requests.get(url, timeout=15, verify=False)
            resp.raise_for_status()
            pem = resp.text.strip()
            if "BEGIN CERTIFICATE" in pem:
                with open(cert_path, "w", encoding="utf-8") as f:
                    f.write(pem + "\n")
                extra_certs.append(pem)
                log.info("Сертификат Минцифры скачан: %s", name)
            else:
                log.warning("Файл %s не содержит сертификат, пропускаем", name)
        except Exception as e:
            log.warning("Не удалось скачать %s: %s", name, e)

    if not extra_certs:
        log.error("Не удалось получить ни один сертификат Минцифры!")
        log.error("Скачайте вручную с https://www.gosuslugi.ru/crt и положите .crt файлы в папку certs/")
        return certifi.where()  # fallback на чистый certifi

    # 3. Объединяем: certifi + сертификаты Минцифры
    combined = base_certs
    for cert in extra_certs:
        if cert not in combined:
            combined += "\n" + cert + "\n"

    with open(BUNDLE_FILE, "w", encoding="utf-8") as f:
        f.write(combined)

    log.info("Объединённый CA-bundle создан: %s (%d сертификатов Минцифры)",
             BUNDLE_FILE, len(extra_certs))
    return BUNDLE_FILE


# ===========================================================================
#  Клиент MAX API
# ===========================================================================

API    = "https://platform-api2.max.ru"
TOKEN  = os.environ.get("MAX_BOT_TOKEN", "")
HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json",
}

# Создаём сессию с объединённым bundle
session = requests.Session()
session.headers.update(HEADERS)


def init_ssl():
    """Инициализирует SSL-сессию с объединённым bundle."""
    bundle = build_combined_bundle()
    session.verify = bundle
    log.info("SSL проверка через: %s", bundle)
    return bundle


def get_me():
    """Проверка токена: GET /me"""
    r = session.get(f"{API}/me", timeout=10)
    r.raise_for_status()
    return r.json()


def get_updates(marker=None, timeout=30):
    """Long polling: GET /updates"""
    params = {"timeout": timeout, "limit": 100}
    if marker is not None:
        params["marker"] = marker
    r = session.get(f"{API}/updates", params=params, timeout=timeout + 10)
    r.raise_for_status()
    return r.json()


def send_message(chat_id, text):
    """Отправка сообщения: POST /messages"""
    r = session.post(f"{API}/messages", json={"chat_id": chat_id, "text": text}, timeout=10)
    r.raise_for_status()
    return r.json()


# ===========================================================================
#  Main
# ===========================================================================

def main():
    if not TOKEN:
        log.error("Переменная окружения MAX_BOT_TOKEN не задана!")
        log.error("Пример: export MAX_BOT_TOKEN='ваш_токен'")
        return

    # 1. Создаём объединённый CA-bundle и настраиваем сессию
    init_ssl()

    # 2. Проверяем токен
    try:
        me = get_me()
        log.info("Бот авторизован: %s (user_id=%s)", me.get("name"), me.get("user_id"))
    except requests.exceptions.HTTPError as e:
        log.error("Ошибка авторизации, проверьте MAX_BOT_TOKEN: %s", e)
        return
    except requests.exceptions.SSLError as e:
        log.error("SSL ошибка даже с объединённым bundle: %s", e)
        log.error("Скачайте сертификаты вручную с https://www.gosuslugi.ru/crt")
        return

    # 3. Основной цикл
    marker = None
    log.info("Бот запущен. Напишите ему в MAX.")

    while True:
        try:
            data = get_updates(marker=marker)
            marker = data.get("marker", marker)

            for update in data.get("updates", []):
                event_type = update.get("update_type")

                if event_type == "bot_started":
                    msg = update.get("message", {})
                    chat_id = msg.get("recipient", {}).get("chat_id") \
                              or msg.get("chat_id")
                    send_message(chat_id, "Привет! Я эхо-бот на requests + сертификаты Минцифры 🤖")
                    log.info("Новый пользователь запустил бота (chat_id=%s)", chat_id)

                elif event_type == "message_created":
                    msg = update.get("message", {})
                    chat_id = msg.get("recipient", {}).get("chat_id") \
                              or msg.get("chat_id")
                    text = msg.get("body", {}).get("text", "")
                    sender = msg.get("sender", {}).get("user_id", "аноним")
                    log.info("Сообщение от %s: %s", sender, text)
                    send_message(chat_id, f"Эхо: {text}")

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else "?"
            if status == 429:
                retry_after = int(e.response.headers.get("Retry-After", 2))
                log.warning("Rate limited, ждём %s сек", retry_after)
                time.sleep(retry_after)
            else:
                log.error("HTTP %s: %s", status, e)
                time.sleep(2)

        except requests.exceptions.ConnectionError as e:
            log.error("Сетевая ошибка: %s", e)
            time.sleep(5)

        except Exception as e:
            log.error("Непредвиденная ошибка: %s", e)
            time.sleep(2)


if __name__ == "__main__":
    main()
