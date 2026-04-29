# python parser.py . --output структура.txt --exclude parser.py структура.txt
import os
import sys
import fnmatch
import argparse
from pathlib import Path

# Попробуем импортировать tqdm, если нет – обойдёмся без прогресс-бара
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("⚠️  tqdm не установлен. Прогресс-бар отключён. Установите: pip install tqdm")

# ------------------------------------------------------------------
# 1. Настройка исключений (папки, файлы, маски)
# ------------------------------------------------------------------
DEFAULT_EXCLUDE = [
    "__pycache__",
    "*.pyc",
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    ".DS_Store",
    "*.egg-info",
    ".mypy_cache",
    ".pytest_cache",
    "venv",
    ".env",
    ".gitignore",
    "parser.py",
    "структура.txt",
    "Tracks"
]

# ------------------------------------------------------------------
# 2. Определение текстовых файлов (чьё содержимое нужно показать)
# ------------------------------------------------------------------
def is_text_file(file_path: Path) -> bool:
    """Проверяем: текстовый ли файл (по расширению + fallback по содержимому)."""
    text_exts = {
        ".py", ".txt", ".md", ".json", ".env", ".yml", ".yaml",
        ".cfg", ".ini", ".html", ".css", ".js", ".ts", ".xml",
        ".csv", ".log", ".sh", ".bat", ".ps1", ".toml", ".sql", ".rst",
    }
    if file_path.suffix.lower() in text_exts:
        return True
    # Пытаемся прочитать первые 1 КБ как текст
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read(1024)
        return True
    except (UnicodeDecodeError, PermissionError, OSError):
        return False


# ------------------------------------------------------------------
# 3. Построение дерева с отступами «- », «-- », «---- » …
# ------------------------------------------------------------------
def get_tree_prefix(depth: int) -> str:
    """Глубина 1 -> '- ', 2 -> '-- ', 3 -> '---- ', 4 -> '-------- ' ..."""
    if depth == 0:
        return ""
    num_dashes = 2 ** (depth - 1)
    return "-" * num_dashes + " "


def build_tree(root: Path, exclude_patterns: list[str]) -> str:
    """Возвращает строку с деревом проекта."""
    lines = []
    root_name = root.name
    lines.append(f"```{root_name}/")

    def walk(dir_path: Path, depth: int) -> None:
        try:
            items = sorted(dir_path.iterdir(),
                           key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return
        for item in items:
            if any(fnmatch.fnmatch(item.name, pat) for pat in exclude_patterns):
                continue
            prefix = get_tree_prefix(depth)
            if item.is_dir():
                lines.append(f"{prefix}{item.name}/")
                walk(item, depth + 1)
            else:
                lines.append(f"{prefix}{item.name}")

    walk(root, 1)
    lines.append("```")
    return "\n".join(lines)


# ------------------------------------------------------------------
# 4. Сбор содержимого текстовых файлов (с прогресс-баром)
# ------------------------------------------------------------------
def collect_file_contents(root: Path, exclude_patterns: list[str]) -> list[tuple[str, str]]:
    """Возвращает список (относительный_путь, содержимое) для текстовых файлов."""
    # Сначала собираем список всех текстовых файлов
    text_files = []

    def scan(dir_path: Path) -> None:
        try:
            items = sorted(dir_path.iterdir(),
                           key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return
        for item in items:
            if any(fnmatch.fnmatch(item.name, pat) for pat in exclude_patterns):
                continue
            if item.is_dir():
                scan(item)
            else:
                if is_text_file(item):
                    text_files.append(item)

    scan(root)

    # Теперь читаем содержимое с прогресс-баром
    result = []
    iterable = tqdm(text_files, desc="📄 Чтение файлов", unit="файл") if TQDM_AVAILABLE else text_files
    for file_path in iterable:
        try:
            rel = file_path.relative_to(root).as_posix()
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            result.append((rel, content))
        except Exception:
            pass  # недоступный файл игнорируется

    return result


# ------------------------------------------------------------------
# 5. Главная функция – запись всего в выходной txt
# ------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Генератор описания архитектуры проекта"
    )
    parser.add_argument("directory", help="Путь к корневой папке проекта")
    parser.add_argument(
        "--exclude", nargs="*", default=DEFAULT_EXCLUDE,
        help="Шаблоны исключений (можно переопределить)"
    )
    parser.add_argument(
        "--output", default="output.txt",
        help="Имя выходного файла (по умолчанию output.txt)"
    )
    parser.add_argument(
        "--no-progress", action="store_true",
        help="Отключить прогресс-бар (если tqdm не нужен)"
    )
    args = parser.parse_args()

    root = Path(args.directory).resolve()
    if not root.exists() or not root.is_dir():
        sys.exit(f"Ошибка: директория '{root}' не найдена или не является папкой.")

    # Управляем глобальной доступностью прогресс-бара
    global TQDM_AVAILABLE
    if args.no_progress:
        TQDM_AVAILABLE = False

    # ------- Строим дерево -------
    print("🌲 Генерация дерева проекта...")
    tree_text = build_tree(root, args.exclude)

    # ------- Собираем текстовые файлы (прогресс-бар внутри) -------
    files_data = collect_file_contents(root, args.exclude)

    # ------- Запись в файл -------
    print("💾 Сохранение результата...")
    with open(args.output, "w", encoding="utf-8") as out:
        out.write("-" * 56 + "\n")
        out.write("В папке проекта такая архитектура:\n")
        out.write(tree_text + "\n\n")

        for rel_path, content in files_data:
            # Формат: путь ``` содержимое ```
            out.write(f"{rel_path} ```\n{content}\n```\n\n")

        out.write("-" * 56 + "\n")

    print(f"✅ Готово! Результат сохранён в '{args.output}'.")


if __name__ == "__main__":
    main()