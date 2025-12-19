from typing import Literal, List
from io import BytesIO

def read_rom_bytes(offset: int, length: int = -1) -> bytes:
  '''
  Read a block of bytes from a ROM file.
  Args:
      offset (int): The offset in the ROM to start reading from.
      length (int): The total length of data to read in bytes. If -1, read to the end of the file.
  Returns:
      bytes: The bytes read from the ROM.
  '''
  with open('baserom.gba', 'rb') as rom:
    rom.seek(offset)
    if length == -1:
      return rom.read()
    else:
      return rom.read(length)

def read_rom_table(offset: int, length: int, 
                   element_size: int = 1) -> list[bytes]:
  '''
  Read a table of data from a ROM file.
  Args:
      offset (int): The offset in the ROM to start reading from.
      length (int): The total length of data to read in bytes.
      element_size (int): The size of each element in bytes.
  Returns:
      list[bytes]: The list of chunks read from the ROM.
  '''
  data = []

  raw_data = BytesIO(read_rom_bytes(offset, length))

  for _ in range(length // element_size):
    data.append(raw_data.read(element_size))

  return data

def read_rom_int_table(offset: int, length: int, 
                   element_size: int = 1, 
                   endianness: Literal['little', 'big'] = 'little', 
                   signed: bool = False) -> list[int]:
  '''
  Read a table of numbers from a ROM file.
  Args:
      offset (int): The offset in the ROM to start reading from.
      length (int): The total length of data to read in bytes.
      element_size (int): The size of each element in bytes.
      endianness ('little', 'big'): The endianness of the data.
      signed (bool): Whether the data is signed or unsigned.
  Returns:
      list[int]: The list of integers read from the ROM.
  '''
  data = []

  raw_data = read_rom_table(offset, length, element_size)

  for entry in raw_data:
    data.append(int.from_bytes(entry, endianness, signed=signed))

  return data

def lz77_decompress(data: bytes | BytesIO) -> bytes:
  '''
  Decompress LZ77-compressed data from a GBA ROM.
  Args:
      data (bytes | BytesIO): The LZ77-compressed data.
  Returns:
      bytes: The decompressed data.
  '''

  if not isinstance(data, BytesIO):
    data = BytesIO(data)
  else:
    data.seek(0)

  # LZ77 header is a 4-byte word, where the lowest byte is the magic number (0x10),
  # and the upper 3 bytes are the length of the _decompressed_ data.
  header = int.from_bytes(data.read(4), 'little')

  magic = header & 0xFF
  assert magic == 0x10, f'Invalid LZ77 magic! Expected: 0x10, Received 0x{magic:02x}'

  decompressed_length = header >> 8

  decompressed_data = BytesIO()
  bytes_written = 0

  while bytes_written < decompressed_length:
    flags = int.from_bytes(data.read(1))

    # For each of the bits in the flag byte, from MSB to LSB
    for i in range(8):
      if bytes_written >= decompressed_length:
        break

      # If the bit is 0, the next byte is a literal
      # If the bit is 1, the next 2 bytes are a (displacement, length) pair
      type = flags & (0x80 >> i)

      # Next byte is literal
      if type == 0:
        value = int.from_bytes(data.read(1))
        decompressed_data.write(bytes([value]))
        bytes_written += 1
        continue

      # Next 2 bytes are (displacement, length) pair
      # Displacement: 12 bits, Length: 4 bits
      # Displacement is the distance back from the current position to copy from
      # Length is the number of bytes to copy, minus 3 (so a length of 0 means copy 3 bytes)
      value = int.from_bytes(data.read(2), 'little')
      displacement = ((value & 0xF) << 8) | (value >> 8)
      length = ((value >> 4) & 0xF)

      for _ in range(length + 3):
        byte = decompressed_data.getbuffer()[bytes_written - displacement - 1]
        decompressed_data.write(bytes([byte]))
        bytes_written += 1

  return decompressed_data.getvalue()

def split_blob(blob: bytes | BytesIO) -> List[bytes]:
  '''
  Split a blob of data into chunks based on a table of offsets.
  The first 4 bytes of the blob indicate the number of entries (N).
  The next N * 4 bytes are the offsets of each entry within the blob.
  Args:
      blob (bytes | BytesIO): The blob of data to split.
  Returns:
      list[bytes]: A list of byte chunks extracted from the blob.
  '''

  if not isinstance(blob, BytesIO):
    blob = BytesIO(blob)
  else:
    blob.seek(0)

  num_chunks = int.from_bytes(blob.read(4), 'little')
  offsets = []
  chunks = []

  for _ in range(num_chunks):
    offsets.append(int.from_bytes(blob.read(4), 'little'))

  for i in range(len(offsets)):
    blob.seek(offsets[i])
    end_offset = offsets[i + 1] if i + 1 < len(offsets) else len(blob.getbuffer())
    chunk_size = end_offset - offsets[i]
    chunks.append(blob.read(chunk_size))

  return chunks