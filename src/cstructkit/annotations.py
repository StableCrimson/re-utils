from enum import Enum
from typing import List
from dataclasses import dataclass


@dataclass
class AnnotationData:
    name: str
    size: int
    offset: int


class AnnotationType(Enum):
    """
    Represents the various annotations that can be added to a C struct
    """

    NONE = 0
    """No annotations."""

    NAME = 1
    """Annotate the field name."""

    OFFSET = 2
    """Annotate the field offset."""

    SIZE = 3
    """Annotate the field size."""

    def get_annotations(self, data: List[AnnotationData]) -> List[str]:
        if self == AnnotationType.NAME:
            return [entry.name.upper() for entry in data]

        if self == AnnotationType.OFFSET:
            return [f'Offset: 0x{entry.offset:02X}' for entry in data]

        if self == AnnotationType.SIZE:
            return [f'Size: 0x{entry.size:02X}' for entry in data]

        return [''] * len(data)


class AnnotationPosition(Enum):
    """
    The position of annotations in C struct representations.
    """

    INLINE = 0
    """Annotations appear on the same line as the field."""

    ABOVE = 1
    """Annotations appear above the field."""

    def place_annotations(self, annotations: List[str], indentation: int) -> List[str]:
        placed = []

        if self == AnnotationPosition.INLINE:
            longest_annotation = max(len(note) for note in annotations)
            for annotation in annotations:
                placed.append(
                    f'{"\t" * indentation}/* {annotation.center(longest_annotation)} */ '
                )
        elif self == AnnotationPosition.ABOVE:
            for annotation in annotations:
                new = f'{"\t" * indentation}// {annotation}\n{"\t" * indentation}'

                # No starting newline if it's the first field
                if len(placed) != 0:
                    new = '\n' + new

                placed.append(new)

        return placed
