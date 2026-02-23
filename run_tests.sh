#!/bin/bash
# Запуск тестов для MatrixAPI

set -e

cd "$(dirname "$0")"

echo "🧪 Запуск тестов..."

export TESTING=true

python -m pytest tests/ --tb=short -q

echo "✅ Все тесты пройдены!"
