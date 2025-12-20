from abc import ABC
from typing import get_type_hints, Any, List
from dataclasses import dataclass
import struct
from src.annotations import AnnotationPosition, AnnotationType, AnnotationData


@dataclass
class CType(ABC):
    """
    Base class for C data types used in CStruct definitions.
    Attributes:
      size (int): Size of the data type in bytes.
      format (str): Struct format character for this data type.
      value (Any): The actual value of the data type.
    """

    size: int
    """Size of the data type in bytes."""

    format: str
    """Struct format character for this data type."""

    value: Any
    """The actual value of the data type."""

    def __init__(self, value: Any):
        self.value = value

    @classmethod
    def padding_needed(cls, offset: int) -> int:
        """
        Calculate the padding needed to align the current offset to this type's size.
        Args:
          offset (int): The current offset in bytes.
        Returns:
          pad (int): The number of padding bytes needed to achieve proper alignment for the data type.
        """

        pad = (cls.size - (offset % cls.size)) % cls.size
        return pad


class UInt8(CType):
    size = 1
    format = 'B'


class UInt16(CType):
    size = 2
    format = 'H'


class UInt32(CType):
    size = 4
    format = 'I'


# TODO: add bitfield support
# TODO: Move basic c types to separate module


@dataclass
class CStruct(ABC):
    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)

        # Validation, no struct should be _defined_ with non CType fields
        errors = []

        # For calculating `struct` format string
        offset = 0
        fmt = '<'  # GBA is little-endian

        # For generating field annotations
        cls._annotation_data = []

        for name, type in get_type_hints(cls).items():
            if not issubclass(type, CType):
                errors.append(
                    f'{cls.__name__}.{name} must be a CType subclass, got {type}'
                )
                continue

            padding = type.padding_needed(offset)
            offset += padding
            fmt += 'x' * padding

            cls._annotation_data.append(AnnotationData(name, type.size, offset))

            offset += type.size
            fmt += type.format

        cls._size = struct.calcsize(fmt)
        cls._format = fmt

        if len(errors) > 0:
            raise TypeError('\n'.join(errors))

    @classmethod
    def struct_format(cls) -> str:
        """
        Generate the necessary struct format string for this CStruct subclass.
        Returns:
            fmt (str): The struct format string.
        """

        return cls._format

    @classmethod
    def size(cls) -> int:
        """
        Calculate the total size of this CStruct subclass in bytes.
        Returns:
            size (int): The total size in bytes.
        """

        return cls._size

    @classmethod
    def from_bytes(cls, data: bytes):
        """
        Create an instance of this CStruct subclass from a bytes.
        Args:
            data (bytes): The byte data to parse.
        Returns:
            instance (CStruct): An instance of the CStruct subclass.
        """

        assert len(data) >= cls.size(), (
            f'Data must be at least {cls.size():02X} bytes long, got {len(data):02X} bytes.'
        )

        unpacked_data = list(struct.unpack(cls.struct_format(), data))
        fields = []

        for _, type in get_type_hints(cls).items():
            # Only for type hints
            if not issubclass(type, CType):
                continue  # pragma: no cover

            fields.append(type(unpacked_data.pop(0)))

        return cls(*fields)

    @classmethod
    def _get_annotations(
        cls,
        annotation_type: AnnotationType,
        position: AnnotationPosition,
        indentation: int,
    ) -> List[str]:
        if annotation_type == AnnotationType.NONE:
            return ['\t' * indentation] * len(cls._annotation_data)

        annotations = annotation_type.get_annotations(cls._annotation_data)
        return position.place_annotations(annotations, indentation)

    def formatted_c(
        self,
        annotation_type: AnnotationType = AnnotationType.NONE,
        annotation_position: AnnotationPosition = AnnotationPosition.INLINE,
        indentation: int = 1,
        wide_hex: bool = False,
    ) -> str:
        """
        Generate a C-style struct representation of this CStruct instance.
        Args:
            annotation_type: (AnnotationType): The type of annotation to be placed on the fields within a C struct. Default `AnnotationType.NONE`.
            annotation_position (AnnotationPosition): Where to place annotations relative to their fields. Default `AnnotationPosition.INLINE`.
            indentation (int): The current indentation level for indentation.
            wide_hex (bool): Whether to print hexidecimal values padded to 4 bytes.
        Returns:
            c_struct (str): The C-style struct representation.
        """

        prefix = f'{"\t" * (indentation - 1)}{{'
        suffix = f'{"\t" * (indentation - 1)}}}'
        lines = []
        annotations = self._get_annotations(
            annotation_type, annotation_position, indentation
        )

        for value, annotation in zip(self.__dict__.values(), annotations):
            # Only for type hints
            if not isinstance(value, CType):
                continue  # pragma: no cover

            if wide_hex:
                formatted_val = f'0x{value.value:04X}'
            else:
                formatted_val = f'0x{value.value:02X}'

            # TODO: Allow nested structs
            lines.append(f'{annotation}{formatted_val}')

        return '\n'.join([prefix, ',\n'.join(lines), suffix])
