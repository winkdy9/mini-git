import sys
import os
from pathlib import Path
from .pygit.objects import Blob, hash_object, Commit
from .pygit.index import read_index, write_index, walk_tree
from .pygit.index import build_tree_structure, write_tree_recursive
from .pygit.log import CommitHistoryIterator, get_head_commit
from typing import Callable, Any

from .pygit.constants import (
    OBJECTS_DIR,
    HEADS_DIR,
    HEAD_FILE,
    HEAD_FILE_CONTENT,
)

commands: dict[str, Callable[..., Any]] = {}


def command(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Декоратор, регистрирующий функцию как команду pygit.

    Args:
        name (str): имя команды.

    Returns:
        Callable[[Callable], Callable]:
    - Декоратор, который принимает функцию
    и добавляет её в словарь команд.
    """

    def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
        commands[name] = function
        return function

    return decorator


@command("init")
def init() -> None:
    """
    Инициализирует новый репозиторий pygit.

    Создаёт следующую структуру директорий:
    - .pygit/
    - .pygit/objects/
    - .pygit/refs/heads/
    - .pygit/HEAD с содержимым по умолчанию "ref: refs/heads/main"

    Returns:
        None
    """

    Path(OBJECTS_DIR).mkdir(parents=True, exist_ok=True)
    Path(HEADS_DIR).mkdir(parents=True, exist_ok=True)

    head_path = Path(HEAD_FILE)
    head_path.write_text(HEAD_FILE_CONTENT)

    print("Инициализация репозитория - done")


@command("add")
def add(path: str) -> None:
    """
    Добавляет файл в индекс:

    Создаёт blob и сохраняет его в хранилище объектов.
    Обновляет индекс и сохраняет обновлённый индекс.

    Args:
        path (str): Путь к файлу, который нужно добавить в индекс.

    Returns:
        None
    """
    file_path = Path(path)
    data = file_path.read_bytes()

    blob = Blob(data)
    sha = hash_object(blob.serialize(), "blob")

    index = read_index()
    index = [entry for entry in index if entry[0] != path]
    mode = "1"
    index.append((path, sha, mode))  # добавление новой записи в индекс

    write_index(index)
    print("Файл добавлен в индекс")


@command("write-tree")
def write_tree() -> str:
    """
    Создаёт дерево текущего состояния индекса:

    Считывает индекс и строит вложенную структуру.
    Рекурсивно создаёт tree-объекты и возвращает хеш корневого дерева.

    Returns:
        str: SHA-1 созданного корневого объекта tree.
    """
    index = read_index()
    tree_dict = build_tree_structure(index)

    for _ in walk_tree(tree_dict):
        pass

    root_sha = write_tree_recursive(tree_dict)
    print(root_sha)

    return root_sha


@command("commit")
def commit(*args: Any) -> None:
    """
    Создаёт новый коммит с текущим состоянием индекса.

    Args:
        *args: Аргументы командной строки.
            Либо: -m "сообщение"
            Либо: "сообщение".

    Returns:
        None
    """
    if len(args) == 1 and isinstance(args[0], list):
        args = tuple(args[0])

    if len(args) >= 2 and args[0] == "-m":
        message = " ".join(args[1:])
    else:
        message = " ".join(args)

    if not message:
        print("Ошибка: необходимо указать сообщение коммита")
        return

    author = "user"

    # Получение хеша корневого дерева, определение родительского коммита
    tree_sha = write_tree()

    with open(HEAD_FILE, "r") as f:
        ref = f.read().strip().split(" ")[1]

    ref_path = os.path.join(".pygit", ref)

    parent_sha = None
    if os.path.exists(ref_path):
        with open(ref_path, "r") as f:
            parent_sha = f.read().strip()

    commit_obj = Commit(tree_sha, parent_sha or "", author, message)
    commit_sha = hash_object(commit_obj.serialize(), "commit")

    os.makedirs(os.path.dirname(ref_path), exist_ok=True)
    with open(ref_path, "w") as f:
        f.write(commit_sha)

    print(f"[{commit_sha[:7]}] {message}")


@command("log")
def log() -> None:
    """
    Выводит историю коммитов от HEAD к первому:

    Получает хеш последнего коммита из HEAD.
    Создаёт итератор истории коммитов.
    Последовательно выводит информацию о каждом коммите:
       (хеш коммита, автора, сообщение).

    Returns:
        None
    """

    head_sha = get_head_commit()

    if not head_sha:
        print("Нет коммитов")
        return

    for entry in CommitHistoryIterator(head_sha):
        print(f"commit {entry['sha']}")
        print(f"Author: {entry['author']}")
        print(f"{entry['message']}")
        print()


def main() -> None:
    """
    Вызывает нужную команду по аргументу.

    Returns:
        None
    """
    if len(sys.argv) < 2:
        print("Ошибка: не указана команда.")
        return

    cmd = sys.argv[1]

    if cmd not in commands:
        print(f"Неизвестная команда: {cmd}")
        return

    commands[cmd](*sys.argv[2:])


if __name__ == "__main__":
    main()
