from abc import ABC
from typing import get_type_hints, List, Generator
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

        # Validation, no struct should be _defined_ with non CType or CStruct fields
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
                continue

            if issubclass(type, CStruct):
                # Flatten nested struct: align the start, then append its inner format
                padding = type.padding_needed(offset)
                offset += padding
                fmt += 'x' * padding

                # Append each nested annotation, adjusting offsets and names
                # If the nested type is a synthetic CArray we generate
                # annotated names that include the parent field name and
                # element index. For arrays of structs this becomes
                # `parent_0_field`, while for arrays of primitive types it
                # becomes `parent_0`.
                if getattr(type, '_is_carray', False):
                    # Number of top-level elements in the array
                    num_elems = len(type.__annotations__)
                    elem_size = type.size() // max(1, num_elems)

                    for entry in type._annotation_data:
                        nested_offset = offset + entry.offset

                        idx = entry.offset // elem_size

                        # If the inner name looks like an auto-generated
                        # field (starts with underscore), emit only the
                        # parent+index. Otherwise include the inner name
                        # as well: parent_{idx}_{inner}
                        if entry.name.startswith('_'):
                            ann_name = f'{name}_{idx}'
                        else:
                            ann_name = f'{name}_{idx}_{entry.name}'

                        cls._annotation_data.append(
                            AnnotationData(ann_name, entry.size, nested_offset)
                        )
                else:
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
                continue

            errors.append(
                f'{cls.__name__}.{name} must be a CType or CStruct subclass, got {type}'
            )

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
                    continue  # pragma: no cover

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
        fields_per_line: int = 1,
    ) -> str:
        """
        Generate a C-style struct representation of this CStruct instance.
        Args:
            annotation_type: (AnnotationType): The type of annotation to be placed on the fields within a C struct. Default `AnnotationType.NONE`.
            annotation_position (AnnotationPosition): Where to place annotations relative to their fields. Default `AnnotationPosition.INLINE`.
            indentation (int): The current indentation level for the formatted struct. Default 1.
            fields_per_line (int): Number of fields in include in a single line before inserting a line break. Default 1.
        Returns:
            c_struct (str): The C-style struct representation.
        """

        prefix = f'{"\t" * (indentation - 1)}{{'
        suffix = f'{"\t" * (indentation - 1)}}}'

        fields_per_line = max(fields_per_line, 1)

        # Flatten instance values to match flattened annotations
        def _iter_flat_values(obj: CType | CStruct) -> Generator[CType]:
            for v in obj.__dict__.values():
                if isinstance(v, CType):
                    yield v
                elif isinstance(v, CStruct):
                    yield from _iter_flat_values(v)

        # Align all values for neatness
        def _justified_hex(val: int, width: int) -> str:
            hex_val = hex(val)

            # Convert all hex chars to uppercase
            pre, suf = hex_val.split('x')
            hex_val = f'{pre}x{suf.upper()}'

            return hex_val.rjust(width)

        annotations = self._get_annotations(
            annotation_type, annotation_position, indentation
        )

        raw_values = [*_iter_flat_values(self)]
        widest_value = max(len(hex(value.value)) for value in raw_values)

        aligned_values = [
            _justified_hex(value.value, widest_value) for value in raw_values
        ]

        inline = fields_per_line >= len(aligned_values)
        content = ''
        num_in_row = 0

        for i, (value, annotation) in enumerate(zip(aligned_values, annotations)):
            if num_in_row != 0 or inline:
                annotation = annotation.removeprefix('\t' * indentation)

            content += f'{annotation}{value}'

            num_in_row += 1

            if i < len(aligned_values) - 1:
                if num_in_row >= fields_per_line:
                    num_in_row = 0
                    content += ',\n'
                else:
                    content += ', '

        if inline:
            return ' '.join([prefix, content, suffix])

        return '\n'.join([prefix, content, suffix])
