import time
import logging
import requests

logger = logging.getLogger(__name__)

class BaseAPIClient:
    """
    Базовый клиент для работы с HTTP API.

    Содержит общую сетевую логику:
    - HTTP-сессию;
    - таймауты;
    - повторные запросы;
    - обработку HTTP-ошибок;
    - преобразование ответа в JSON.
    """

    MAX_RETRIES = 3
    TIMEOUT = (10, 30)

    def __init__(self):

        self.session = requests.Session()

        self.session.headers.update({
            "Accept": "application/json"
        })

    def _make_request(self, url, params=None):
        """
        Отправляет GET-запрос и возвращает JSON-ответ.

        Метод не проверяет структуру JSON.
        Он возвращает dict, list или другой допустимый
        JSON-объект — в зависимости от ответа сервера.
        """

        for attempt in range(1, self.MAX_RETRIES + 1):

            try:
                logger.info("Отправка запроса: %s", url)

                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.TIMEOUT
                )

                # Обработка ограничения количества запросов
                if response.status_code == 429:

                    if attempt < self.MAX_RETRIES:
                        retry_after = response.headers.get("Retry-After")

                        try:
                            wait_time = max(0, float(retry_after))
                        except (TypeError, ValueError):
                            wait_time = 2 ** attempt

                        logger.warning(
                            "Превышен лимит запросов. "
                            "Повтор через %s секунд.",
                            wait_time
                        )

                        time.sleep(wait_time)
                        continue


                if response.status_code in (500, 502, 503, 504):

                    if attempt < self.MAX_RETRIES:
                        wait_time = 2 ** attempt

                        logger.warning(
                            "Ошибка сервера (%s). "
                            "Повтор через %s секунд.",
                            response.status_code,
                            wait_time
                        )

                        time.sleep(wait_time)
                        continue

                response.raise_for_status()

                try:
                    data = response.json()

                except requests.exceptions.JSONDecodeError as error:
                    logger.error("Сервер вернул некорректный JSON")

                    raise ValueError(
                        "Не удалось преобразовать ответ в JSON"
                    ) from error

                logger.info("Ответ успешно получен")

                return data

            except (
                requests.exceptions.Timeout,
                requests.exceptions.ConnectionError
            ) as error:

                if attempt < self.MAX_RETRIES:
                    wait_time = 2 ** attempt

                    logger.warning(
                        "Сетевая ошибка: %s. "
                        "Повтор через %s секунд.",
                        error,
                        wait_time
                    )

                    time.sleep(wait_time)

                else:
                    logger.error(
                        "Не удалось выполнить запрос после %s попыток",
                        self.MAX_RETRIES
                    )
                    raise

        raise RuntimeError("Не удалось получить ответ от API")

    def close(self):

        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
