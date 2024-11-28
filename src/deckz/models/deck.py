"""Model classes for parsed decks.

The main class is `Deck`. It's comprised of `Part`s containing `Section`s and `File`s, \
both of which are `Node`s and have a `process` method to allow visitors to be defined.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass

from ..processing import NodeVisitor
from .scalars import FlavorName, PartName, ResolvedPath, UnresolvedPath

__all__ = ["Deck", "File", "Node", "Part", "Section"]


@dataclass
class Node(ABC):
    title: str | None
    unresolved_path: UnresolvedPath
    # resolved_path and parsing_error could benefit from a refactoring using something
    # like Either because we cannot have both a ResolvedPath and a parsing_error at the
    # same time.
    resolved_path: ResolvedPath
    parsing_error: str | None

    @abstractmethod
    def accept[**P, T](
        self, visitor: NodeVisitor[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        raise NotImplementedError


@dataclass
class File(Node):
    def accept[**P, T](
        self, visitor: NodeVisitor[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        return visitor.visit_file(self, *args, **kwargs)


@dataclass
class Section(Node):
    flavor: FlavorName
    children: list[Node]

    def accept[**P, T](
        self, visitor: NodeVisitor[P, T], *args: P.args, **kwargs: P.kwargs
    ) -> T:
        return visitor.visit_section(self, *args, **kwargs)


@dataclass
class Part:
    title: str | None
    nodes: list[Node]


@dataclass
class Deck:
    acronym: str
    parts: dict[PartName, Part]

    def filter(self, whitelist: Iterable[PartName]) -> None:
        if frozenset(whitelist).difference(self.parts):
            msg = "provided whitelist has part names not in the deck"
            raise ValueError(msg)
        to_remove = frozenset(self.parts).difference(whitelist)
        for part_name in to_remove:
            del self.parts[part_name]
