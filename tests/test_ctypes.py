from dataclasses import dataclass
import pytest
from src.structs import (
    CType,
    CStruct,
    UInt8,
    UInt16,
    UInt32,
)
from src.annotations import (
    AnnotationPosition,
    AnnotationType,
)


class MyCType(CType):
    size = 2
    format = 'H'


@dataclass
class A(CStruct):
    """
    The struct should be organized as follows:
      00      01      02      03      04      05      06      07      08      09      0A      0B      0C
    +---------------------------------------------------------------------------------------------------
    | [ u8  ] [ pad ] [ pad ] [ pad ] [             u32             ] [ u8  ] [ pad ] [      u16     ]
      B       x       x       x       I                               B       x       H

    """

    _0: UInt8
    # Expect 3 bytes of padding
    _4: UInt32
    _8: UInt8
    # Expect 1 byte of padding
    _A: UInt16


@dataclass
class B(CStruct):
    a: UInt8
    b: UInt16


def test_padding_needed():
    assert MyCType.padding_needed(0) == 0
    assert MyCType.padding_needed(1) == 1
    assert MyCType.padding_needed(2) == 0


def test_struct_formatted_with_padding():
    expected_format = '<BxxxIBxH'
    assert A.struct_format() == expected_format


def test__size_with_padding():
    expected_size = 0xC  # 1 + 3 + 4 + 1 + 1 + 2
    assert A.size() == expected_size


def test_from_bytes_fails():
    fake_bytes = b'\x00' * (B.size() - 1)  # One byte short
    with pytest.raises(AssertionError):
        _ = B.from_bytes(fake_bytes)


def test_from_bytes():
    fake_data = b'\x11\xff\x22\x22'
    struct = B.from_bytes(fake_data)
    assert struct.a.value == 0x11
    assert struct.b.value == 0x2222


def test_from_bytes_unpacks_le():
    fake_data = b'\xff\xff\x33\x22'
    struct = B.from_bytes(fake_data)
    assert struct.b.value == 0x2233


def test_validation_fails_for_non_c_type_fields():
    with pytest.raises(TypeError):

        class BadStruct(CStruct):
            a: UInt8
            b: int  # Not a valid type!


def test_formatted_c():
    fake_data = b'\x11\xff\x22\x22'
    struct = B.from_bytes(fake_data)

    expected_str = '{\n\t0x11,\n\t0x2222\n}'
    assert struct.formatted_c() == expected_str


def test_formatted_c_indented():
    reference_lines = ['{', '\t0x11,', '\t0x2222', '}']

    fake_data = b'\x11\xff\x22\x22'
    struct = B.from_bytes(fake_data)
    indented_lines = struct.formatted_c(indentation=2).splitlines()

    for reference, actual in zip(reference_lines, indented_lines):
        assert f'\t{reference}' == actual


def test_formatted_c_wide_hex():
    expected = ['{', '\t0x0011,', '\t0x2222', '}']

    fake_data = b'\x11\xff\x22\x22'
    struct = B.from_bytes(fake_data)
    actual_lines = struct.formatted_c(wide_hex=True).splitlines()

    for exptected, actual in zip(expected, actual_lines):
        assert exptected == actual


def test_formatted_c_annotated():
    expected = ['{', '\t/* A */ 0x11,', '\t/* B */ 0x2222', '}']

    fake_data = b'\x11\xff\x22\x22'
    struct = B.from_bytes(fake_data)
    actual_lines = struct.formatted_c(
        annotation_type=AnnotationType.NAME,
        annotation_position=AnnotationPosition.INLINE,
    ).splitlines()

    for exptected, actual in zip(expected, actual_lines):
        assert exptected == actual


def test_get_annotations_inline():
    expected = ['\t/* A */ ', '\t/* B */ ']
    assert (
        B._get_annotations(AnnotationType.NAME, AnnotationPosition.INLINE, 1)
        == expected
    )


def test_get_annotations_above():
    expected = ['\t// A\n\t', '\n\t// B\n\t']

    # First field shouldn't start with a newline
    assert not B._get_annotations(AnnotationType.NAME, AnnotationPosition.ABOVE, 1)[
        0
    ].startswith('\n')
    assert (
        B._get_annotations(AnnotationType.NAME, AnnotationPosition.ABOVE, 1) == expected
    )
