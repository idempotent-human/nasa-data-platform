import logging
import re

from .base_client import BaseAPIClient


logger = logging.getLogger(__name__)


class ExoplanetClient(BaseAPIClient):
    """
    Клиент для взаимодействия с NASA Exoplanet Archive
    через Table Access Protocol (TAP).
    """

    BASE_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

    def __init__(self):
        # Получаем HTTP-сессию и общую сетевую логику
        # от родительского класса
        super().__init__()

    def execute_query(self, query):
        """
        Выполняет запрос к Exoplanet Archive
        на языке ADQL и возвращает JSON-ответ.
        """

        if not isinstance(query, str) or not query.strip():
            raise ValueError("Необходимо указать ADQL-запрос")

        params = {
            "query": query,
            "format": "json"
        }

        data = self._make_request(
            self.BASE_URL,
            params
        )

        # Проверяем структуру ответа TAP
        if not isinstance(data, list):
            raise ValueError(
                "Ожидался список записей от Exoplanet Archive"
            )

        return data

    def get_tables(self):
        """
        Получает список доступных таблиц Exoplanet Archive.
        """

        query = """
            SELECT *
            FROM TAP_SCHEMA.tables
        """

        return self.execute_query(query)

    def get_columns(self, table_name):
        """
        Получает метаданные столбцов указанной таблицы.
        """

        if not isinstance(table_name, str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_]*",
            table_name
        ):
            raise ValueError("Некорректное имя таблицы")

        query = f"""
            SELECT *
            FROM TAP_SCHEMA.columns
            WHERE table_name = '{table_name}'
        """

        return self.execute_query(query)

    def get_table_sample(self, table_name, limit=2):
        """
        Получает выборку записей из указанной таблицы.
        """
        if not isinstance(table_name, str) or not re.fullmatch(
                r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)?",
                table_name
        ):
            raise ValueError("Некорректное имя таблицы")

        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("limit должен быть целым числом больше 0")

        query = f"""
            SELECT TOP {limit} *
            FROM {table_name}
        """

        return self.execute_query(query)

    def get_all_columns(self):
        query = """
            SELECT * FROM TAP_SCHEMA.columns
        """
        return self.execute_query(query)
