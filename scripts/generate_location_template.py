#!/usr/bin/env python3
"""
Скрипт для генерации темплейта локации в формате JSON.
Используется для создания новых локаций в builtin или instance контенте.
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

    def create_location_template(
        self, name: str, location_type: str, description: str = ""
    ) -> Dict[str, Any]:
        """
        Создает темплейт локации

        Args:
            name: Название локации
            location_type: Тип локации (planet/space/location/sublocation)
            description: Описание локации

        Returns:
            Словарь с данными локации
        """
        if location_type not in self.supported_types:
            raise ValueError(
                f"Unsupported location type: {location_type}. "
                f"Supported types: {self.supported_types}"
            )

        template = {
            "name": name,
            "type": location_type,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "parent": None,  # Родительская локация (если есть)
            "children": [],  # Подлокации
            "properties": {
                "max_players": 50,
                "is_public": True,
                "is_active": True,
                "allow_combat": True,
                "allow_trading": True,
                "allow_chat": True,
            },
            "metadata": {
                "author": "system",
                "version": "1.0.0",
                "tags": [],
                "difficulty": "medium",
            },
            "content": {
                "description": description,
                "atmosphere": "",
                "weather": "",
                "terrain": "",
                "resources": [],
                "npcs": [],
                "events": [],
            },
            "exits": {},  # Доступные выходы в другие локации
            "connections": [],  # Связи с другими локациями
        }

        return template

    def save_location_template(self, template: Dict[str, Any], path: Path) -> None:
        """
        Сохраняет темплейт локации в JSON файл

        Args:
            template: Темплейт локации
            path: Путь для сохранения
        """
        # Создаем директории если их нет
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        print(f"✅ Локация сохранена: {path}")

    def generate_from_interactive(self) -> None:
        """
        Интерактивный режим генерации локации
        """
        print("🔧 Генератор темплейтов локаций")
        print("=" * 40)

        name = input("📝 Название локации: ").strip()
        if not name:
            print("❌ Название не может быть пустым!")
            return

        print(f"\n📋 Доступные типы локаций:")
        for i, t in enumerate(self.supported_types, 1):
            print(f"  {i}. {t}")

        type_choice = input(
            f"\n❓ Выберите тип (1-{len(self.supported_types)}): "
        ).strip()
        try:
            type_index = int(type_choice) - 1
            if type_index < 0 or type_index >= len(self.supported_types):
                raise ValueError
            location_type = self.supported_types[type_index]
        except ValueError:
            print("❌ Неверный выбор типа!")
            return

        description = input("📝 Описание локации: ").strip()

        # Дополнительные параметры в зависимости от типа
        template = self.create_location_template(name, location_type, description)

        # Специфические параметры для разных типов
        if location_type == "planet":
            template["properties"]["gravity"] = "1g"
            template["properties"]["atmosphere"] = "oxygen"
            template["content"]["terrain"] = "varied"

        # Спрашиваем о родительской локации
        if location_type in ["location", "sublocation"]:
            parent = input(
                "📂 Родительская локация (оставьте пустым если нет): "
            ).strip()
            if parent:
                template["parent"] = parent

        # Спрашиваем о тегах
        tags_input = input("🏷️  Теги (через запятую): ").strip()
        if tags_input:
            template["metadata"]["tags"] = [
                t.strip() for t in tags_input.split(",") if t.strip()
            ]

        # Путь сохранения
        save_path = input("📁 Путь сохранения (относительно builtin/): ").strip()
        if not save_path:
            save_path = f"locations/{name.replace(' ', '_').lower()}.json"

        full_path = Path("builtin") / save_path

        self.save_location_template(template, full_path)


def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(
        description="Генератор темплейтов локаций",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument("--name", "-n", type=str, help="Название локации")
    parser.add_argument(
        "--type",
        "-t",
        type=str,
        choices=["planet", "space", "location", "sublocation"],
        help="Тип локации",
    )
    parser.add_argument("--description", "-d", type=str, help="Описание локации")
    parser.add_argument("--path", "-p", type=str, help="Путь сохранения")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Интерактивный режим"
    )

    args = parser.parse_args()

    generator = LocationTemplateGenerator()

    if args.interactive:
        generator.generate_from_interactive()
    else:
        if not args.name or not args.type:
            print("❌ Требуется указать --name и --type!")
            parser.print_help()
            return 1

        template = generator.create_location_template(
            args.name, args.type, args.description or ""
        )

        save_path = (
            Path("builtin")
            / "locations"
            / (args.path or f"{args.name.replace(' ', '_').lower()}.json")
        )
        generator.save_location_template(template, save_path)

    return 0


if __name__ == "__main__":
    exit(main())
