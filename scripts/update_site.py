#!/usr/bin/env python3
"""
Основной скрипт для обновления сайта
"""

import os
import sys
import argparse
import logging
import asyncio
import importlib.util
from datetime import datetime
import pytz
import subprocess
from typing import List, Tuple

# Добавляем путь к корню проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config import TIMEZONE, OUTPUT_DIR

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def import_script(script_name):
    """
    Импортирует скрипт по имени из текущей директории
    """
    script_path = os.path.join(os.path.dirname(__file__), f"{script_name}.py")
    spec = importlib.util.spec_from_file_location(script_name, script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def run_git_command(command: List[str]) -> Tuple[int, str, str]:
    """
    Запускает git команду и возвращает код возврата, stdout и stderr
    """
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr
    except Exception as e:
        logger.error(f"Error running git command {' '.join(command)}: {e}")
        return 1, "", str(e)

def update_git_repo():
    """
    Обновляет Git репозиторий: добавляет изменения, создает коммит и пушит
    """
    try:
        # Проверяем статус Git
        returncode, stdout, stderr = run_git_command(['git', 'status', '--porcelain'])
        if returncode != 0:
            logger.error(f"Failed to get git status: {stderr}")
            return False

        # Если нет изменений, выходим
        if not stdout.strip():
            logger.info("No changes to commit")
            return True

        # Добавляем файлы в индекс
        paths_to_add = [
            OUTPUT_DIR,                    # docs директория
            # os.path.join(DATA_DIR, '*.json')  # JSON файлы с данными
        ]
        
        for path in paths_to_add:
            returncode, stdout, stderr = run_git_command(['git', 'add', path])
            if returncode != 0:
                logger.error(f"Failed to add {path} to git: {stderr}")
                return False

        # Создаем коммит
        commit_message = f"Update site data and pages ({datetime.now(pytz.timezone(TIMEZONE)).strftime('%Y-%m-%d %H:%M')})"
        returncode, stdout, stderr = run_git_command(['git', 'commit', '-m', commit_message])
        if returncode != 0:
            logger.error(f"Failed to commit changes: {stderr}")
            return False

        # Пушим изменения
        returncode, stdout, stderr = run_git_command(['git', 'push'])
        if returncode != 0:
            logger.error(f"Failed to push changes: {stderr}")
            return False

        logger.info("Successfully updated git repository")
        return True

    except Exception as e:
        logger.error(f"Error updating git repository: {e}")
        return False

async def update_site(days: int):
    """
    Запускает полный процесс обновления сайта
    """
    try:
        start_time = datetime.now(pytz.timezone(TIMEZONE))
        logger.info(f"Starting site update process at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 1. Сбор данных
        logger.info("Step 1: Collecting data...")
        data_collector = import_script("data_collector")
        await data_collector.main()

        # 2. Обогащение данных
        logger.info("Step 2: Enriching data...")
        enrich_data = import_script("enrich_data")
        enrich_data.process_data()

        # 3. Генерация сайта
        logger.info("Step 3: Generating site...")
        generate_site = import_script("generate_site")
        generate_site.generate_site()

        # 4. Обновление Git репозитория
        logger.info("Step 4: Updating git repository...")
        if not update_git_repo():
            logger.warning("Failed to update git repository")

        end_time = datetime.now(pytz.timezone(TIMEZONE))
        duration = end_time - start_time
        logger.info(f"Site update completed in {duration.total_seconds():.1f} seconds")

    except Exception as e:
        logger.error(f"Error during site update: {e}")
        raise

def main():
    """
    Точка входа в скрипт
    """
    parser = argparse.ArgumentParser(description='Обновление сайта с объявлениями')
    parser.add_argument('--days', type=int, default=90,
                      help='За сколько последних дней собирать данные (по умолчанию: 9)')
    args = parser.parse_args()

    try:
        asyncio.run(update_site(args.days))
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
    except Exception as e:
        logger.error(f"Process failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 