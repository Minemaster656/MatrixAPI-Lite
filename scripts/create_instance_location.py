#!/usr/bin/env python3
"""
CLI инструмент для создания локаций в instance контенте.
Создает локации в content/instances/ и поддерживает различные опции.
"""

import argparse
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class InstanceLocationCreator:
    """
    Создает локации в instance контенте
    """

    def __init__(self):
        self.supported_types = ["planet", "space", "location", "sublocation"]
        self.instance_path = Path("instance_content/locations")
        self.builtin_path = Path("builtin/locations")

    def create_location_instance(
        self, name: str, location_type: str, description: str = ""
    ) -> Dict[str, Any]:
        """
        Создает экземпляр локации для instance контента

        Args:
            name: Название локации
            location_type: Тип локации
            description: Описание

        Returns:
            Словарь с данными локации
        """
        if location_type not in self.supported_types:
            raise ValueError(f"Unsupported location type: {location_type}")

        # Генерируем уникальный ID
        location_id = f"{location_type[:3]}_{name.replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        template = {
            "id": location_id,
            "name": name,
            "type": location_type,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "parent": None,
            "children": [],
            "properties": {
                "max_players": 50,
                "is_public": True,
                "is_active": True,
                "allow_combat": True,
                "allow_trading": True,
                "allow_chat": True,
                "instance_only": True,
            },
            "metadata": {
                "author": "instance",
                "version": "1.0.0",
                "tags": [],
                "difficulty": "medium",
                "instance_created": datetime.now().isoformat(),
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
            "exits": {},
            "connections": [],
            "instance_data": {
                "owner": "current_instance",
                "customizations": {},
                "modifications": [],
            },
        }

        return template

    def save_location_instance(self, template: Dict[str, Any], path: Path) -> None:
        """
        Сохраняет экземпляр локации

        Args:
            template: Темплейт локации
            path: Путь сохранения
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)

        print(f"✅ Экземпляр локации создан: {path}")

    def create_from_builtin(
        self, builtin_name: str, instance_name: Optional[str] = None
    ) -> None:
        """
        Создает экземпляр локации из builtin локации

        Args:
            builtin_name: Название builtin локации
            instance_name: Новое название для instance (если отличается)
        """
        # Ищем builtin локацию
        builtin_files = list(self.builtin_path.glob("**/*.json"))

        matches = []
        for file in builtin_files:
            with open(file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data["name"].lower() == builtin_name.lower():
                    matches.append((file, data))

        if not matches:
            print(f"❌ Builtin локация '{builtin_name}' не найдена!")
            print("Доступные локации:")
            for file in builtin_files:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"  - {data['name']}")
            return

        if len(matches) > 1:
            print(f"Найдено несколько локаций с именем '{builtin_name}':")
            for i, (file, data) in enumerate(matches, 1):
                print(f"{i}. {file}")
            choice = input("Выберите номер: ").strip()
            try:
                index = int(choice) - 1
                if index < 0 or index >= len(matches):
                    print("Неверный выбор!")
                    return
                file, data = matches[index]
            except ValueError:
                print("Неверный ввод!")
                return
        else:
            file, data = matches[0]

        # Создаем экземпляр
        instance_data = data.copy()
        instance_data["id"] = (
            f"instance_{instance_data['name'].replace(' ', '_').lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        instance_data["created_at"] = datetime.now().isoformat()
        instance_data["updated_at"] = datetime.now().isoformat()
        instance_data["properties"]["instance_only"] = True
        instance_data["metadata"]["author"] = "instance"
        instance_data["metadata"]["instance_created"] = datetime.now().isoformat()
        instance_data["instance_data"] = {
            "owner": "current_instance",
            "customizations": {},
            "modifications": [],
        }

        if instance_name:
            instance_data["name"] = instance_name

        instance_path = (
            self.instance_path
            / f"{instance_data['name'].replace(' ', '_').lower()}.json"
        )
        self.save_location_instance(instance_data, instance_path)

    def generate_from_interactive(self) -> None:
        """
        Интерактивный режим создания экземпляра локации
        """
        print("🔧 Создатель экземпляров локаций")
        print("=" * 40)

        print("\nВыберите способ создания:")
        print("1. Создать новую локацию")
        print("2. Создать из существующей builtin локации")

        choice = input("\nВаш выбор (1/2): ").strip()

        if choice == "1":
            self.create_new_instance_interactive()
        elif choice == "2":
            self.create_from_builtin_interactive()
        else:
            print("Неверный выбор!")

    def create_new_instance_interactive(self) -> None:
        """
        Интерактивное создание новой локации
        """
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

        template = self.create_location_instance(name, location_type, description)

        # Спрашиваем о родительской локации
        if location_type in ["location", "sublocation"]:
            parent = input(
                "📂 Родительская локация (оставьте пустым если нет): "
            ).strip()
            if parent:
                template["parent"] = parent

        # Спрашиваем о тегах
        tags_input = input("🏷️  Тги (через запятую): ").strip()
        if tags_input:
            template["metadata"]["tags"] = [
                t.strip() for t in tags_input.split(",") if t.strip()
            ]

        # Путь сохранения
        save_path = input(
            "📁 Путь сохранения (относительно content/instances/): "
        ).strip()
        if not save_path:
            save_path = f"{template['name'].replace(' ', '_').lower()}.json"

        full_path = self.instance_path / save_path
        self.save_location_instance(template, full_path)

    def create_from_builtin_interactive(self) -> None:
        """
        Интерактивное создание из builtin
        """
        builtin_name = input("📂 Название builtin локации: ").strip()
        instance_name = input(
            "📝 Новое название для instance (оставьте пустым чтобы оставить прежнее): "
        ).strip()

        self.create_from_builtin(builtin_name, instance_name if instance_name else None)  # type: ignore


def main():
    """Основная функция CLI"""
    parser = argparse.ArgumentParser(
        description="Создатель экземпляров локаций",
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
        "--from-builtin", "-b", type=str, help="Создать из builtin локации"
    )
    parser.add_argument(
        "--instance-name", "-in", type=str, help="Новое название для instance локации"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Интерактивный режим"
    )

    args = parser.parse_args()

    creator = InstanceLocationCreator()

    if args.interactive:
        creator.generate_from_interactive()
    elif args.from_builtin:
        creator.create_from_builtin(args.from_builtin, args.instance_name)
    else:
        if not args.name or not args.type:
            print("❌ Требуется указать --name и --type!")
            parser.print_help()
            return 1

        template = creator.create_location_instance(
            args.name, args.type, args.description or ""
        )

        save_path = creator.instance_path / (
            args.path or f"{args.name.replace(' ', '_').lower()}.json"
        )
        creator.save_location_instance(template, save_path)

    return 0


if __name__ == "__main__":
    exit(main())
