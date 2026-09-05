"""Reassembles fragmented Groups-of-Pictures from carved NAL units."""

from typing import List


def reassemble_gop_fragments(nal_units: List[bytes]) -> List[bytes]:
    """
    Reassembles carved NAL units into raw elementary stream GOP (Group-of-Pictures) fragments.
    OUTPUT INVARIANT: Returns raw elementary stream bytes. Never repackages or converts into containers (.mp4/.mkv).
    """
    if not nal_units:
        return []

    gop_fragments: List[bytes] = []
    current_gop = bytearray()

    for nal in nal_units:
        # Check NAL unit type (5 = IDR keyframe, 7 = SPS, 8 = PPS)
        # NAL header byte follows start code (index 3 or 4)
        prefix_len = 4 if nal.startswith(b"\x00\x00\x00\x01") else 3
        if len(nal) > prefix_len:
            nal_header = nal[prefix_len]
            nal_type = nal_header & 0x1F

            # Start a new GOP on SPS (7) or IDR Keyframe (5)
            if nal_type in (5, 7) and current_gop:
                gop_fragments.append(bytes(current_gop))
                current_gop = bytearray()

        current_gop.extend(nal)

    if current_gop:
        gop_fragments.append(bytes(current_gop))

    return gop_fragments
