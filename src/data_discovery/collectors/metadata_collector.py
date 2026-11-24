from dataclasses import dataclass, field
from typing import Any
import logging

logger = logging.getLogger(__name__)
@dataclass
class DatasetMetadata:
    """Описание одного набора данных"""
    dataset_name: str
    dataset_type: str
    metadata: list[dict[str, Any]] = field(default_factory=list)
    sample: list[dict[str, Any]] = field(default_factory=list)

@dataclass
class SourceMetadata:
    """Описание одного источника данных"""
    source_name: str
    datasets: list[DatasetMetadata]

@dataclass
class DiscoveryResult:
    """Общий результат исследования всех источников"""
    sources: list[SourceMetadata] = field(default_factory=list)

# Для источников NeoWs metadata остаётся пустым: API не отдаёт готовую схему полей,
# поэтому структура полей определяется позже в StructuralProfiler по содержимому JSON.
class MetadataCollector:

    def __init__(self, neows_client, exoplanet_client):
        self.neows_client = neows_client
        self.exoplanet_client = exoplanet_client

    def _collect_exoplanet(self):
        tables = self.exoplanet_client.get_tables()
        all_columns = self.exoplanet_client.get_all_columns()

        columns_by_table = {}

        for column in all_columns:
            table_name = column['table_name']

            if table_name not in columns_by_table:
                columns_by_table[table_name] = []

            columns_by_table[table_name].append(column)

        datasets = []

        for table in tables:
            table_name = table["table_name"]

            schema_name = table.get("schema_name", "")

            if schema_name.upper() == "TAP_SCHEMA":
                continue

            try:
                sample = self.exoplanet_client.get_table_sample(
                    table_name,
                    limit=100
                )

            except Exception as e:
                logger.warning(
                    "Не удалось получить sample для таблицы %s: %s",
                    table_name,
                    e
                )
                sample = []

            dataset = DatasetMetadata(
                dataset_name=table_name,
                dataset_type="table",
                metadata=columns_by_table.get(table_name, []),
                sample=sample
            )

            datasets.append(dataset)

        source = SourceMetadata(
            source_name="NASA Exoplanet Archive",
            datasets=datasets
        )

        return source

    def _collect_neows(
            self,
            feed_start_date,
            feed_end_date,
            lookup_asteroid_id=None,
            browse_page=0
    ):

        feed_data = self.neows_client.get_feed(
            start_date=feed_start_date,
            end_date=feed_end_date
        )

        if lookup_asteroid_id is None:

            asteroids = []

            for asteroid_list in feed_data["near_earth_objects"].values():
                asteroids.extend(asteroid_list)

            if not asteroids:
                raise ValueError("Feed не вернул астероидов")

            lookup_asteroid_id = asteroids[0]["id"]

        lookup_data = self.neows_client.get_lookup(
            asteroid_id=lookup_asteroid_id
        )

        browse_data = self.neows_client.get_browse(
            page=browse_page
        )

        feed_dataset = DatasetMetadata(
            dataset_name="feed",
            dataset_type="json",
            metadata=[],
            sample=[feed_data]
        )

        lookup_dataset = DatasetMetadata(
            dataset_name="lookup",
            dataset_type="json",
            metadata=[],
            sample=[lookup_data]
        )

        browse_dataset = DatasetMetadata(
            dataset_name="browse",
            dataset_type="json",
            metadata=[],
            sample=[browse_data]
        )

        datasets = [
            feed_dataset,
            browse_dataset,
            lookup_dataset
        ]

        source = SourceMetadata(
            source_name="NASA NeoWs",
            datasets=datasets
        )

        return source

    def collect(self, feed_start_date, feed_end_date, lookup_asteroid_id, browse_page=0):
        exoplanet_source = self._collect_exoplanet()

        neows_source = self._collect_neows(
            feed_start_date=feed_start_date,
            feed_end_date=feed_end_date,
            lookup_asteroid_id=lookup_asteroid_id,
            browse_page=browse_page
        )

        result = DiscoveryResult(
            sources=[
                exoplanet_source,
                neows_source
            ]
        )

        return result
