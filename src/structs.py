from abc import ABC
from typing import get_type_hints, List
from dataclasses import dataclass
import struct
from src.types import CType
from src.annotations import AnnotationPosition, AnnotationType, AnnotationData


@dataclass
class CStruct(ABC):
    @classmethod
    def padding_needed(cls, offset: int) -> int:
        # Align nested structs the same way as C types: to their total size.
        pad = (cls._alignment - (offset % cls._alignment)) % cls._alignment
        return pad

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)

        # Validation, no struct should be _defined_ with non CType fields
        errors = []
        cls._alignment = 0

        # For calculating `struct` format string
        offset = 0
        fmt = '<'  # GBA is little-endian

        # For generating field annotations
        cls._annotation_data: List[AnnotationData] = []

        for name, type in get_type_hints(cls).items():
            # Allow either primitive C types or nested CStructs
            if issubclass(type, CType):
                padding = type.padding_needed(offset)
                offset += padding
                fmt += 'x' * padding

                cls._annotation_data.append(AnnotationData(name, type.size, offset))

                offset += type.size
                fmt += type.format
                cls._alignment = max(cls._alignment, type.size)
            elif issubclass(type, CStruct):
                # Flatten nested struct: align the start, then append its inner format
                padding = type.padding_needed(offset)
                offset += padding
                fmt += 'x' * padding

                # Append each nested annotation, adjusting offsets and names
                for entry in type._annotation_data:
                    nested_offset = offset + entry.offset
                    cls._annotation_data.append(
                        AnnotationData(entry.name, entry.size, nested_offset)
                    )

                # Append the nested struct's format (strip leading endianness)
                nested_fmt = type._format[1:]
                fmt += nested_fmt

                offset += type.size()
                cls._alignment = max(cls._alignment, type._alignment)
            else:
                errors.append(
                    f'{cls.__name__}.{name} must be a CType or CStruct subclass, got {type}'
                )
                continue

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

        unpacked_data: List[CType] = list(struct.unpack(cls.struct_format(), data))

        def _from_unpacked(unpacked_iter, struct_cls):
            values = []
            for _, t in get_type_hints(struct_cls).items():
                if issubclass(t, CType):
                    values.append(t(next(unpacked_iter)))
                elif issubclass(t, CStruct):
                    values.append(_from_unpacked(unpacked_iter, t))
                else:
                    # validation in __init_subclass__ prevents this
                    continue

            return struct_cls(*values)

        it = iter(unpacked_data)
        return _from_unpacked(it, cls)

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
        num_in_row: int = 1,
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
        annotations = self._get_annotations(
            annotation_type, annotation_position, indentation
        )

        count = 0
        content = ''

        # Flatten instance values to match flattened annotations
        def _iter_flat_values(obj):
            for v in obj.__dict__.values():
                if isinstance(v, CType):
                    yield v
                elif isinstance(v, CStruct):
                    yield from _iter_flat_values(v)

        for value, annotation in zip(_iter_flat_values(self), annotations):
            if wide_hex:
                formatted_val = f'{hex(value.value)}'
            else:
                formatted_val = f'{hex(value.value)}'

            content += f'{annotation}{formatted_val}'

            count += 1

            if count >= num_in_row:
                count = 0
                content += ',\n'
            else:
                content += ', '

        return '\n'.join([prefix, content, suffix])
