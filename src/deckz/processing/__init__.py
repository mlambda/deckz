from typing import TYPE_CHECKING, Protocol

# Necessary to avoid circular imports with ..models.deck
if TYPE_CHECKING:
    from ..models.deck import Deck, File, Section


class NodeVisitor[**P, T](Protocol):
    def visit_file(self, file: "File", *args: P.args, **kwargs: P.kwargs) -> T: ...
    def visit_section(
        self, section: "Section", *args: P.args, **kwargs: P.kwargs
    ) -> T: ...


class Processor[T](Protocol):
    def process(self, deck: "Deck") -> T: ...
