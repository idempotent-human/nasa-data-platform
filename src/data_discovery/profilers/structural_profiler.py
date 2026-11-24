#сначала нам конечно же нужно разобраться с джойсонами астероидов metadata пустой же
#обход структуры json
#определение типов полей
#определение вложенности
#обработка массивов
#
from dataclasses import dataclass, field
from typing import Any
import logging
#тут было бы удобно написать алгоритм обхода дерева
@dataclass
class FieldProfile:
    """Профиль отдельного поля/ колонки / ключа JSON"""
    field_name: str
    inferred_type: str
    is_nullable: bool
    sample_values: list[Any] = field(default_factory=list)
    nested_fields: list["FieldProfile"] = field(default_factory=list) # список вложенных полей внутри текущего поля, у экзопланет оно пустое

@dataclass
class DatasetProfile:
    """Профиль конкретного набора данных (таблицы или API-эндпоинта)"""
    dataset_name: str
    dataset_type: str
    total_samples_analyzed: int
    fields: list[FieldProfile] = field(default_factory=list)

@dataclass
class SourceProfile:
    """Профиль источника данных, содержащий профили его датасетов."""
    source_name: str #"NASA Exoplanet Archive" или "NASA NeoWs"
    datasets: list[DatasetProfile] = field(default_factory=list)

@dataclass
class ProfilingResult:
    """Итоговый результат структурного профилирования всех источников."""
    sources: list[SourceProfile] = field(default_factory=list)


class StructuralProfiler:

    def profile(self, discovery_result):
        """
              Запускает структурное профилирование полученных данных.
              Обходит источники и их датасеты, выбирает алгоритм
              профилирования в зависимости от типа источника
              и формирует итоговый ProfilingResult.
              """
        profiling_result = ProfilingResult()
        for source in discovery_result.sources:
            source_profile = SourceProfile(
                source_name=source.source_name
            )
            for dataset in source.datasets:
                if source.source_name == "NASA NeoWs":
                    dataset_profile = self._profile_neows_datasets(dataset)
                elif source.source_name == "NASA Exoplanet Archive":
                    dataset_profile = self._profile_exoplanet_datasets(dataset)
                else:
                    continue
                source_profile.datasets.append(dataset_profile)
            profiling_result.sources.append(source_profile)

        return profiling_result

        pass
    def _profile_neows_datasets(self, dataset):
        """
                Профилирует один JSON-датасет NASA NeoWs.

                Обрабатывает каждую запись выборки, выполняет рекурсивный
                обход JSON-структуры и объединяет профили одноимённых полей.
                """

        dataset_profile = DatasetProfile(
            dataset_name=dataset.dataset_name, #тут конкретный эндпоинт
            dataset_type=dataset.dataset_type,
            total_samples_analyzed=0,
            fields=[]
        )
        for sample in dataset.sample:
            fields = self._traverse_json(sample)
            dataset_profile.fields = self._merge_field_profiles(dataset_profile.fields + fields)
            dataset_profile.total_samples_analyzed += 1

        return dataset_profile
    def _traverse_json(self, data):
        """
              Обходит JSON-объект верхнего уровня.

              Для каждого ключа вызывает рекурсивный анализ значения
              и формирует список профилей полей.
              """
        fields = []
        for field_name, value in data.items():
            field_profile = self._analyze_field(field_name, value)
            fields.append(field_profile)
        return fields
    def infer_type(self,value):

        if isinstance(value, bool):
            return "bool"

        elif isinstance(value, int):
            return "int"

        elif isinstance(value, float):
            return "float"

        elif isinstance(value, str):
            return "str"

        elif value is None:
            return "null"

        elif isinstance(value, dict):
            return "dict"

        elif isinstance(value, list):
            return "list"

        return "unknown"


    def _analyze_field(self, field_name, value):

        inferred_type = self.infer_type(value)
        field_profile = FieldProfile(
            field_name=field_name,
            inferred_type=inferred_type,
            is_nullable=value is None,
            sample_values=[],
            nested_fields=[]
        )
        if inferred_type not in ("dict", "list"):
            if value is not None:
                field_profile.sample_values.append(value)
            return field_profile
        if inferred_type == "dict":
            for nested_name, nested_value in value.items():
                nested_profile = self._analyze_field(
                    nested_name,
                    nested_value
                )
                field_profile.nested_fields.append(nested_profile)
        if inferred_type == "list":
            element_profiles = []

            for item in value:
                if isinstance(item, dict):
                    for nested_name, nested_value in item.items():
                        nested_profile = self._analyze_field(
                            nested_name,
                            nested_value
                        )
                        element_profiles.append(nested_profile)

            field_profile.nested_fields = self._merge_field_profiles(element_profiles)
        return field_profile

    def _merge_field_profiles(self, element_profiles):
        """Объединяет профили одноименных полей"""
        merged = {}
        for profile in element_profiles:
            if profile.field_name not in merged:
                merged[profile.field_name] = profile
            else:
                existing = merged[profile.field_name]
                existing.sample_values.extend(profile.sample_values)
                #добавили ограничение
                existing.sample_values = existing.sample_values[:2]

                if profile.inferred_type in ("dict", "list"):
                    existing.nested_fields = self._merge_field_profiles(existing.nested_fields + profile.nested_fields)
                existing.is_nullable = existing.is_nullable or profile.is_nullable

                if existing.inferred_type == profile.inferred_type:
                    pass
                elif profile.inferred_type == "null":
                    pass
                elif existing.inferred_type == "null":
                    existing.inferred_type = profile.inferred_type
                else:
                    existing.inferred_type = "mixed"


        return list(merged.values())


    def _profile_exoplanet_datasets(self, dataset):
        dataset_profile = DatasetProfile(
            dataset_name=dataset.dataset_name,
            dataset_type=dataset.dataset_type,
            total_samples_analyzed=len(dataset.sample),
            fields=[]
        )
        for column in dataset.metadata:
            column_name = column["column_name"]
            values = [row[column_name] for row in dataset.sample if column_name in row]

            not_null_values = [value for value in values if value is not None]

            types = {self.infer_type(value) for value in not_null_values}
            if len(types) == 0:
                inferred_type = "null"
            elif len(types) == 1:
                inferred_type = types.pop()
            else:
                inferred_type = "mixed"

            field_profile = FieldProfile(
                field_name=column_name,
                inferred_type=inferred_type,
                is_nullable=len(not_null_values) < len(dataset.sample),
                sample_values=not_null_values[:2],
                nested_fields=[]
            )
            dataset_profile.fields.append(field_profile)

        return dataset_profile
