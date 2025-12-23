from abc import ABC
from dataclasses import dataclass
from typing import Any


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
    """Unigned 8-bit integer."""

    size = 1
    format = 'B'


class Int8(CType):
    """Signed 8-bit integer."""

    size = 1
    format = 'b'


class UInt16(CType):
    """Unsigned 16-bit integer."""

    size = 2
    format = 'H'


class Int16(CType):
    """Signed 16-bit integer."""

    size = 2
    format = 'h'


class UInt32(CType):
    """Unsigned 32-bit integer."""

    size = 4
    format = 'I'


class Int32(CType):
    """Signed 32-bit integer."""

    size = 4
    format = 'i'


class CArray:
    """
    Generic C array type used as `CArray[ElementType, count]`.

    This returns a dataclass subclass of `CStruct` at runtime which contains
    `count` fields each typed as `ElementType`. Using a dataclass/CStruct
    subclass allows the outer `CStruct` machinery to flatten the array into
    individual entries (annotations, formats, and unpacking) as if it were a
    nested struct containing `count` elements.
    """

    def __class_getitem__(cls, params):
        try:
            elem_type, count = params
        except Exception:  # pragma: no cover - defensive
            raise TypeError(
                'CArray[...] requires two parameters: element type and count'
            )

        # Validate element type and count
        if not isinstance(count, int) or count <= 0:
            raise TypeError('CArray count must be a positive int')

        # Defer import till now to avoid circular imports
        from src.structs import CStruct

        if not (issubclass(elem_type, CType) or issubclass(elem_type, CStruct)):
            raise TypeError('CArray element must be a CType or CStruct subclass')

        name = f'CArray_{elem_type.__name__}_{count}'

        # Build annotations for the synthetic dataclass: one field per element
        annotations = {f'_{i}': elem_type for i in range(count)}
        namespace = {'__annotations__': annotations}

        # Create a new dataclass subclass of CStruct so existing struct
        # handling flattens and unpacks the elements correctly.
        NewClass = dataclass(type(name, (CStruct,), namespace))

        setattr(NewClass, '_is_carray', True)
        return NewClass
