"""Strips proprietary wrapper headers (.dav/.hik) from parsed/carved streams, ahead of decode."""

DAV_HEADER_MAGIC = b"DHAV"
HIK_HEADER_MAGIC = b"HIKP"
NAL_START_CODE_4 = b"\x00\x00\x00\x01"
NAL_START_CODE_3 = b"\x00\x00\x01"


def depacketize_stream(stream_buffer: bytes, oem: str = "auto") -> bytes:
    """
    Strips proprietary wrapper headers (.dav / .hik) from a stream buffer in memory
    and returns a clean H.264 / H.265 elementary bitstream.
    """
    if not stream_buffer:
        return b""

    # Strip DHAV or HIKP wrapper header if present by locating first NAL start code
    if stream_buffer.startswith(DAV_HEADER_MAGIC) or stream_buffer.startswith(HIK_HEADER_MAGIC):
        pos4 = stream_buffer.find(NAL_START_CODE_4)
        pos3 = stream_buffer.find(NAL_START_CODE_3)

        if pos4 != -1 and (pos3 == -1 or pos4 <= pos3):
            return stream_buffer[pos4:]
        elif pos3 != -1:
            return stream_buffer[pos3:]

    # Locate first NAL start code if buffer has prefix metadata
    if not (stream_buffer.startswith(NAL_START_CODE_4) or stream_buffer.startswith(NAL_START_CODE_3)):
        pos4 = stream_buffer.find(NAL_START_CODE_4)
        pos3 = stream_buffer.find(NAL_START_CODE_3)
        if pos4 != -1 and (pos3 == -1 or pos4 <= pos3):
            return stream_buffer[pos4:]
        elif pos3 != -1:
            return stream_buffer[pos3:]

    return stream_buffer
