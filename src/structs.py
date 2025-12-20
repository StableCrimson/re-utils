from abc import ABC
from typing import get_type_hints, Any
from dataclasses import dataclass
import struct

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

        # TODO: Compute field offsets and formats here

        errors = []
        for name, type in get_type_hints(cls).items():
            if not issubclass(type, CType):
                errors.append(
                    f'{cls.__name__}.{name} must be a CType subclass, got {type}'
                )

        if len(errors) > 0:
            raise TypeError('\n'.join(errors))

    @classmethod
    def struct_format(cls) -> str:
        """
        Generate the necessary struct format string for this CStruct subclass.
        Returns:
            fmt (str): The struct format string.
        """

        fmt = '<'  # GBA is little-endian
        offset = 0

        for _, type in get_type_hints(cls).items():
            # This is solely done for type hints. Validation is done at class creation
            # better type hints since Python can't infer the type on a filtered list.
            if not issubclass(type, CType):
                continue  # pragma: no cover

            padding = type.padding_needed(offset)
            offset += padding
            fmt += 'x' * padding
            offset += type.size
            fmt += type.format

        return fmt

    @classmethod
    def size(cls) -> int:
        """
        Calculate the total size of this CStruct subclass in bytes.
        Returns:
            size (int): The total size in bytes.
        """

        return struct.calcsize(cls.struct_format())

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
        cls, indentation: int
    ) -> List[str]:  # TODO: Stylized annotations
        fields = get_type_hints(cls).keys()

        longest_field_name = max(len(field) for field in fields)

        annotations = []
        for field in fields:
            annotations.append(f'/* {field.upper().center(longest_field_name)} */ ')

        return annotations

    def formatted_c(
        self, indentation: int = 1, annotated: bool = False, wide_hex: bool = False
    ) -> str:
        """
        Generate a C-style struct representation of this CStruct instance.
        Args:
            indentation (int): The current indentation level for indentation.
            annotated (bool): Whether to include annotations.
            wide_hex (bool): Whether to print hexidecimal values padded to 4 bytes.
        Returns:
            c_struct (str): The C-style struct representation.
        """

        lines = [f'{"\t" * (indentation - 1)}{{']

        if annotated:
            annotations = self._get_annotations(indentation)
        else:
            annotations = []

        for i, value in enumerate(self.__dict__.values()):
            # Only for type hints
            if not isinstance(value, CType):
                continue  # pragma: no cover

            annotation = ''
            if annotated:
                annotation = annotations[i]

            if wide_hex:
                formatted_val = f'0x{value.value:04X}'
            else:
                formatted_val = f'0x{value.value:02X}'

            # TODO: Allow nested structs
            lines.append(f'{"\t" * indentation}{annotation}{formatted_val}')

            if i < len(self.__dict__) - 1:
                lines[-1] += ','

        lines.append(f'{"\t" * (indentation - 1)}}}')
        return '\n'.join(lines)
