#!/usr/bin/env python3
"""
Скрипт для генерации темплейта локации на основе существующего JSON файла.
Используется для создания новых локаций из существующих примеров.
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class LocationTemplateGenerator:
    """
    Генератор темплейтов для локаций
    """

    def __init__(self):
        self.supported_types = ["planet", "space", "location", "sublocation"]

    def load_location_data(self, path: Path) -> Dict[str, Any]:
        """
        Загружает данные локации из JSON файла

        Args:
            path: Путь к JSON файлу

        Returns:
            Словарь с данными локации
        """
        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {path}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return data

    def create_template_from_data(
        self,
        data: Dict[str, Any],
        new_name: Optional[str] = None,
        new_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Создает темплейт локации на основе существующих данных

        Args:
            data: Существующие данные локации
            new_name: Новое название (если нужно)
            new_description: Новое описание (если нужно)

        Returns:
            Словарь с данными темплейта
        """
        # Валидация типа
        location_type = data.get("type")
        if location_type not in self.supported_types:
            raise ValueError(f"Unsupported location type: {location_type}")

        # Создаем новый темплейт
        template = {
            "name": new_name or data.get("name", "New Location"),
            "type": location_type,
            "description": new_description or data.get("description", ""),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "parent": None,
            "children": [],
            "properties": {
                "max_players": data.get("properties", {}).get("max_players", 50),
                "is_public": data.get("properties", {}).get("is_public", True),
                "is_active": data.get("properties", {}).get("is_active", True),
                "allow_combat": data.get("properties", {}).get("allow_combat", True),
                "allow_trading": data.get("properties", {}).get("allow_trading", True),
                "allow_chat": data.get("properties", {}).get("allow_chat", True),
            },
            "metadata": {
                "author": "system",
                "version": "1.0.0",
                "tags": data.get("metadata", {}).get("tags", []),
                "difficulty": data.get("metadata", {}).get("difficulty", "medium"),
            },
            "content": {
                "description": new_description
                or data.get("content", {}).get("description", ""),
                "atmosphere": data.get("content", {}).get("atmosphere", ""),
                "weather": data.get("content", {}).get("weather", ""),
                "terrain": data.get("content", {}).get("terrain", ""),
                "resources": data.get("content", {}).get("resources", []),
                "npcs": data.get("content", {}).get("npcs", []),
                "events": data.get("content", {}).get("events", []),
            },
            "exits": {},
            "connections": [],
        }

        # Добавляем специфические поля для разных типов
        if location_type == "planet":
            template["properties"]["gravity"] = data.get("properties", {}).get(
                "gravity", "1g"
            )
            template["properties"]["atmosphere"] = data.get("properties", {}).get(
                "atmosphere", "oxygen"
            )
            template["content"]["terrain"] = data.get("content", {}).get(
                "terrain", "varied"
            )

        # Сохраняем оригинальные ID и связи
        template["original_id"] = data.get("id")
        template["original_connections"] = data.get("connections", [])

        return template

    def save_template(self, template: Dict[str, Any], path: Path) -> None:
        """
        Сохраняет темплейт в JSON файл

        Args:
            template: Темплейт локации
            path: Путь сохранения
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        print(f"✅ Темплейт сохранен: {path}")

    def generate_from_existing(
        self,
        source_path: Path,
        target_path: Path,
        new_name: Optional[str] = None,
        new_description: Optional[str] = None,
    ) -> None:
        """
        Генерирует темплейт из существующего JSON файла

        Args:
            source_path: Путь к исходному файлу
            target_path: Путь для сохранения темплейта
            new_name: Новое название
            new_description: Новое описание
        """
        data = self.load_location_data(source_path)
        template = self.create_template_from_data(data, new_name, new_description)
        self.save_template(template, target_path)


def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(
        description="Генератор темплейтов локаций из существующих JSON",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--source",
        "-s",
        type=str,
        required=True,
        help="Путь к исходному JSON файлу с локацией",
    )
    parser.add_argument(
        "--target", "-t", type=str, required=True, help="Путь для сохранения темплейта"
    )
    parser.add_argument("--name", "-n", type=str, help="Новое название локации")
    parser.add_argument("--description", "-d", type=str, help="Новое описание локации")

    args = parser.parse_args()

    generator = LocationTemplateGenerator()

    try:
        generator.generate_from_existing(
            Path(args.source), Path(args.target), args.name, args.description
        )
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
