from abc import ABC, abstractmethod
import os
import hashlib
import zlib
from .constants import OBJECTS_DIR
from typing import List, Tuple


class GitObject(ABC):
    """Абстрактный объект Git.
    - сериализация (преобразование в байтовое представление),
    - десериализация (восстановление объекта из байтов).
    """

    @abstractmethod
    def serialize(self) -> bytes:
        """
        Преобразует объект в байтовое представление.

        Returns:
            bytes: Сериализованные данные объекта.
        """
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, data: bytes) -> "GitObject":
        """
        Восстановление объекта из байтов.

        Args:
            data (bytes): Байты, из которых должен быть создан объект.

        Returns:
            Восстановленный объект соответствующего типа.
        """
        pass


class Blob(GitObject):
    """
    Объект типа Blob. Хранит точное содержимое файла.
    """
    def __init__(self, data: bytes) -> None:
        """
        Инициализирует blob.

        Args:
            data (bytes): байты файла.
        """

        self.data = data

    def serialize(self) -> bytes:
        """
        Возвращает содержимое blob в виде байтов.

        Returns:
            bytes: исходные данные файла.
        """
        return self.data

    @classmethod
    def deserialize(cls, data: bytes) -> "Blob":
        """
        Создаёт blob из байтов.

        Args:
            data (bytes): байты файла.

        Returns:
            Blob: новый объект blob.
        """

        return cls(data)


class Tree(GitObject):
    """
    Хранит записи дерева: (mode, path, sha)

    mode - "1" или "2"
    path - строка имени файла или каталога
    sha - хеш
    """

    def __init__(
            self,
            entries: List[Tuple[str, str, str]] | None = None
    ) -> None:
        """
        Инициализирует Tree.

        Args:
            entries: Список записей дерева.
            Каждая запись - кортеж.
        """

        self.entries = entries or []

    def serialize(self) -> bytes:
        """
        Сериализует дерево в байтовый формат

        Для каждой записи: "{mode} {path}\0{sha_bytes}"
        """
        result = b""

        for mode, path, sha in self.entries:
            mode_path = f"{mode} {path}".encode() + b"\x00"
            sha_bytes = bytes.fromhex(sha)
            result += mode_path + sha_bytes

        return result

    @classmethod
    def deserialize(cls, data: bytes) -> "Tree":
        """
        Десериализует бинарные данные в объект Tree.

        Args:
            data (bytes): бинарные данные сериализованного tree.

        Returns:
            Tree
        """
        entries = []
        index = 0

        while index < len(data):
            space_pos = data.find(b" ", index)
            mode = data[index:space_pos].decode()

            null_pos = data.find(b"\0", space_pos)
            path = data[space_pos + 1:null_pos].decode()

            sha_bytes = data[null_pos + 1:null_pos + 21]
            sha_hex = sha_bytes.hex()

            entries.append((mode, path, sha_hex))
            index = null_pos + 21

        return cls(entries)


class Commit(GitObject):
    """
    Объект коммита. Хранит: (tree, parent, author, message)
    """

    def __init__(
            self,
            tree: str = "",
            parent: str = "",
            author: str = "",
            message: str = "",
            tree_hash: str | None = None,
            parent_hash: str | None = None
    ) -> None:
        """
        Инициализирует Commit.
        """
        if tree_hash is not None:
            tree = tree_hash

        if parent_hash is not None:
            parent = parent_hash

        self.tree = tree
        self.parent = parent
        self.author = author
        self.message = message

    def serialize(self) -> bytes:
        """
        Сериализует коммит в байтовый формат:
            (tree, parent, author, <message>)
        """
        lines = []
        lines.append(f"tree {self.tree}")

        if self.parent:
            lines.append(f"parent {self.parent}")

        lines.append(f"author {self.author}")

        lines.append("")
        lines.append(self.message)

        return ("\n".join(lines)).encode()

    @classmethod
    def deserialize(cls, data: bytes) -> "Commit":
        """
        Десериализует бинарные данные в объект Commit.

        Args:
            data (bytes): бинарные данные сериализованного Commit.

        Returns:
            Commit
        """
        text = data.decode()
        if "\n\n" in text:
            headers, message = text.split("\n\n", 1)
        else:
            headers = text
            message = ""

        tree = ""
        parent = ""
        author = ""

        for line in headers.split("\n"):
            if line.startswith("tree "):
                tree = line[5:]
            elif line.startswith("parent "):
                parent = line[7:]
            elif line.startswith("author "):
                author = line[7:]

        return cls(tree, parent, author, message)


def hash_object(data: bytes, obj_type: str) -> str:
    """
    Вычисляет хеш объекта, создаёт сжатый файл
    и сохраняет его.

    Args:
        data (bytes): содержимое объекта
        obj_type (str): тип объекта

    Returns:
        str: строковое значение хеша
    """
    header = f"{obj_type} {len(data)}\0".encode()
    store_data = header + data

    sha1 = hashlib.sha1(store_data).hexdigest()

    compressed = zlib.compress(store_data)

    dir_name = sha1[:2]
    file_name = sha1[2:]

    dir_path = os.path.join(OBJECTS_DIR, dir_name)
    file_path = os.path.join(dir_path, file_name)

    os.makedirs(dir_path, exist_ok=True)

    with open(file_path, "wb") as file:
        file.write(compressed)

    return str(sha1)
