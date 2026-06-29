from .constants import INDEX_FILE
import os
from typing import List, Tuple, Dict, Generator, Any
from .objects import Tree, hash_object


def read_index() -> List[Tuple[str, str, str]]:
    """
    Читает индекс и возвращает список кортежей (path, sha, mode).

    Returns:
        List[Tuple[str, str, str]]: список записей индекса.
    """
    if not os.path.exists(INDEX_FILE):
        return []

    entries = []
    with open(INDEX_FILE, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            path, sha, mode = line.split(" ")
            entries.append((path, sha, mode))

    return entries


def write_index(entries: List[Tuple[str, str, str]]) -> None:
    """
    Записывает список кортежей в файл индекса.

    Args:
        entries (List[Tuple[str, str, str]]):
            Список кортежей (path, sha, mode).
    """
    with open(INDEX_FILE, "w", encoding="utf-8") as file:
        for path, sha, mode in entries:
            file.write(f"{path} {sha} {mode}\n")


def add_to_index(path: str, sha: str, mode: str) -> None:
    """
    Добавляет или обновляет запись в индексе.

    Args:
        path (str): путь к файлу.
        sha (str): хеш объекта.
        mode (str): тип файла.
    """
    entries = read_index()

    new_entries = []
    updated = False

    for p, s, m in entries:
        if p == path:
            new_entries.append((path, sha, mode))
            updated = True
        else:
            new_entries.append((p, s, m))

    if not updated:
        new_entries.append((path, sha, mode))

    write_index(new_entries)


def build_tree_structure(
        index_entries: List[Tuple[str, str, str]]
) -> Dict[str, Any]:
    """
    Преобразует индекс в вложенные словари:
        { "dirs": {...}, "files": {...} }

    Args:
        index_entries (List[Tuple[str, str, str]]):
            список записей индекса.

    Returns:
        Dict[str, Any]: рекурсивная структура каталогов и файлов.
    """
    tree: Dict[str, Any] = {"dirs": {}, "files": {}}

    for path, sha, mode in index_entries:
        parts = path.split(os.sep)
        node = tree
        for part in parts[:-1]:
            node = node["dirs"].setdefault(part, {"dirs": {}, "files": {}})
        node["files"][parts[-1]] = (sha, mode)

    return tree


def walk_tree(
        node: Dict[str, Any],
        dirname: str = ""
) -> Generator[Tuple[str, str], None, None]:
    """
    Генератор, рекурсивно обходит структуру директорий.

    Args:
        node (Dict[str, Any]): дерево, сгенерированное build_tree_structure().
        dirname (str): текущий путь при рекурсивном обходе.
    """
    for subdir, subtree in node["dirs"].items():
        full_path = os.path.join(dirname, subdir)
        yield full_path, "dir"
        yield from walk_tree(subtree, full_path)

    for filename, (sha, mode) in node["files"].items():
        full_path = os.path.join(dirname, filename)
        yield full_path, "file"


def write_tree_recursive(node: Dict[str, Any]) -> str:
    """
    Рекурсивно создаёт tree объекты. Возвращает SHA текущего дерева.

    Args:
        node: Узел дерева, которое имеет структуру вида:
            {"dirs":  { dirname: subtree, ... },
            "files": { filename: (sha, mode), ... }}

    Returns:
        str: хеш созданного объекта tree.
    """
    entries = []

    for dirname, subnode in node["dirs"].items():
        subtree_sha = write_tree_recursive(subnode)
        entries.append(("2", dirname, subtree_sha))

    for filename, (sha, mode) in node["files"].items():
        entries.append((mode, filename, sha))

    tree_obj = Tree(entries)
    tree_data = tree_obj.serialize()

    tree_sha = hash_object(tree_data, "tree")

    return tree_sha
