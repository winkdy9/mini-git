import os
import zlib
from .objects import Commit
from .constants import OBJECTS_DIR, HEAD_FILE


class CommitHistoryIterator:
    """
    Итератор истории коммитов: идём от HEAD к корню.
    """

    def __init__(self, start_sha: str | None) -> None:
        """
        Инициализирует итератор.

        Параметры:
            start_sha (str): SHA коммита, с которого начинаем обход.
        """
        self.current_sha = start_sha

    def __iter__(self) -> "CommitHistoryIterator":
        """Возвращает итератор.

        Returns:
            CommitHistoryIterator"""
        return self

    def __next__(self) -> dict[str, str]:
        """
        Возвращает информацию о текущем коммите и
        сдвигает указатель на родительский коммит.

        Returns:
            dict[str, str]: словарь с ключами
             "sha", "author", "message".

        Raises:
            StopIteration: если достигнут корневой коммит.
        """
        if self.current_sha is None:
            raise StopIteration

        sha = self.current_sha

        obj_type, body = read_object(sha)

        commit = Commit.deserialize(body)

        result = {
            "sha": sha,
            "author": commit.author,
            "message": commit.message.strip()
        }

        self.current_sha = commit.parent if commit.parent else None

        return result


def read_object(sha: str) -> tuple[str, bytes]:
    """
    Читает объект по SHA из .pygit/objects и возвращает (тип, данные).

    Args:
        sha (str): хеш объекта.

    Returns:
        tuple[str, bytes]: тип объекта и его несжатое содержимое.
    """
    dir_name = sha[:2]
    file_name = sha[2:]

    path = os.path.join(OBJECTS_DIR, dir_name, file_name)
    with open(path, "rb") as f:
        compressed = f.read()

    data = zlib.decompress(compressed)

    null_index = data.index(b"\0")
    header = data[:null_index]
    body = data[null_index + 1:]

    obj_type = header.split()[0].decode()

    return obj_type, body


def get_head_commit() -> str | None:
    """
    Считывает текущий коммит из файла HEAD.

    Returns:
        str или None: SHA коммита, на который указывает HEAD, либо None.
    """
    if not os.path.exists(HEAD_FILE):
        return None

    with open(HEAD_FILE, "r") as f:
        ref_path = f.read().strip().split(" ")[1]

    if os.path.exists(ref_path):
        with open(ref_path, "r") as f:
            return f.read().strip()
    return None
