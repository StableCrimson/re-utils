from abc import ABC
from typing import get_type_hints, Any
from dataclasses import dataclass
import re
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


@dataclass
class CStruct(ABC):
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
            # This can be done "cleaner" with `filter`, but this gives us
            # better type hints since Python can't infer the type on a filtered list.
            if not issubclass(type, CType):
                continue

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
            if not issubclass(type, CType):
                continue

            fields.append(type(unpacked_data.pop(0)))

        return cls(*fields)

    def formatted_c(
        self, nesting: int = 1, annotated: bool = False, wide_hex: bool = False
    ) -> str:
        """
        Generate a C-style struct representation of this CStruct instance.
        Args:
            nesting (int): The current nesting level for indentation.
            annotated (bool): Whether to include annotations.
            wide_hex (bool): Whether to print hexidecimal values padded to 4 bytes.
        Returns:
            c_struct (str): The C-style struct representation.
        """

        lines = ['{']
        longest_field_name = max(len(name) for name in self.__dict__.keys())

        for i, (name, value) in enumerate(self.__dict__.items()):
            if not isinstance(value, CType):
                continue

            annotation = ''
            if annotated:
                annotation = f'/* {name.upper().center(longest_field_name)} */ '

            if wide_hex:
                formatted_val = f'0x{value.value:04X}'
            else:
                formatted_val = f'0x{value.value:02X}'

            # TODO: Allow nested structs
            lines.append(f'{"\t" * nesting}{annotation}{formatted_val}')

            if i < len(self.__dict__) - 1:
                lines[-1] += ','

        lines.append('}')
        return '\n'.join(lines)
