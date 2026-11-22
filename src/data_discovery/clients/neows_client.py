import os
import logging

from datetime import datetime
from dotenv import load_dotenv

from .base_client import BaseAPIClient

load_dotenv()

logger = logging.getLogger(__name__)


class NeoWsClient(BaseAPIClient):
    """
    Клиент для взаимодействия с NASA Near Earth Object Web Service.
    """

    BASE_URL = "https://api.nasa.gov/neo/rest/v1"

    def __init__(self):
        # Инициализируем общую HTTP-сессию родительского класса
        super().__init__()

        self.api_key = os.getenv("NASA_API_KEY")

        if not self.api_key:
            raise ValueError("NASA_API_KEY не найден в .env")

    def get_feed(self, start_date, end_date):
        """
        Получает астероиды, сближающиеся с Землёй
        в заданном диапазоне дат.
        """

        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        except (ValueError, TypeError) as error:
            raise ValueError(
                "Даты должны иметь формат YYYY-MM-DD"
            ) from error

        if end_dt < start_dt:
            raise ValueError(
                "Конечная дата не может быть раньше начальной"
            )

        url = f"{self.BASE_URL}/feed"

        params = {
            "start_date": start_date,
            "end_date": end_date,
            "api_key": self.api_key
        }

        data = self._make_request(url, params)

        # Проверяем структуру ответа именно NeoWs
        if not isinstance(data, dict):
            raise ValueError(
                "Ожидался JSON-объект от NeoWs API"
            )

        return data

    def get_lookup(self, asteroid_id):
        """
        Получает подробную информацию об астероиде
        по его идентификатору NASA JPL SPK-ID.
        """

        if not str(asteroid_id).strip():
            raise ValueError("Необходимо указать asteroid_id")

        url = f"{self.BASE_URL}/neo/{asteroid_id}"

        params = {
            "api_key": self.api_key
        }

        data = self._make_request(url, params)

        if not isinstance(data, dict):
            raise ValueError(
                "Ожидался JSON-объект от NeoWs API"
            )

        return data

    def get_browse(self, page=0):
        """
        Получает страницу общего набора данных об астероидах.
        """

        if not isinstance(page, int) or isinstance(page, bool) or page < 0:
            raise ValueError(
                "Номер страницы должен быть целым числом >= 0"
            )

        url = f"{self.BASE_URL}/neo/browse"

        params = {
            "api_key": self.api_key,
            "page": page
        }

        data = self._make_request(url, params)

        if not isinstance(data, dict):
            raise ValueError(
                "Ожидался JSON-объект от NeoWs API"
            )

        return data
