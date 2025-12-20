from src.structs import CType, CStruct, UInt8, UInt16, UInt32

class MyCType(CType):
    size = 2
    format = 'H'

class MyCStruct(CStruct):
    '''
    The struct should be organized as follows:
      00      01      02      03      04      05      06      07      08      09      0A      0B      0C
    +---------------------------------------------------------------------------------------------------
    | [ u8  ] [ pad ] [ pad ] [ pad ] [             u32             ] [ u8  ] [ pad ] [      u16     ]
      B       x       x       x       I                               B       x       H

    '''
    _0: UInt8
    # Expect 3 bytes of padding
    _4: UInt32
    _8: UInt8
    # Expect 1 byte of padding
    _A: UInt16


def test_padding_needed():
    assert MyCType.padding_needed(0) == 0
    assert MyCType.padding_needed(1) == 1
    assert MyCType.padding_needed(2) == 0

def test_struct_formatted_with_padding():
    expected_format = '<BxxxIBxH'
    assert MyCStruct.struct_format() == expected_format

def test_struct_size_with_padding():
    expected_size = 0xC # 1 + 3 + 4 + 1 + 1 + 2
    assert MyCStruct.size() == expected_size