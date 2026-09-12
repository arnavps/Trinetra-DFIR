//! NAL start-code scanner shared by the Frame Carver (Phase 4) and the SmartCodec bitstream preprocessor (Phase 7, Section 9.1).

pub fn scan_nal_start_codes(data: &[u8], max_units: usize) -> Vec<usize> {
    let mut offsets = Vec::new();
    if data.len() < 4 {
        return offsets;
    }

    let mut pos = 0;
    let data_len = data.len();

    while pos < data_len - 3 {
        // Search for 4-byte start code: 00 00 00 01
        let idx4 = data[pos..].windows(4).position(|w| w == [0, 0, 0, 1]).map(|i| pos + i);
        // Search for 3-byte start code: 00 00 01
        let idx3 = data[pos..].windows(3).position(|w| w == [0, 0, 1]).map(|i| pos + i);

        match (idx4, idx3) {
            (None, None) => break,
            (Some(i4), None) => {
                offsets.push(i4);
                pos = i4 + 4;
            }
            (None, Some(i3)) => {
                offsets.push(i3);
                pos = i3 + 3;
            }
            (Some(i4), Some(i3)) => {
                if i4 <= i3 {
                    offsets.push(i4);
                    pos = i4 + 4;
                } else {
                    offsets.push(i3);
                    pos = i3 + 3;
                }
            }
        }

        if offsets.len() >= max_units {
            break;
        }
    }

    offsets
}
