import os
import pytest
from app.engine1_acquisition.image_reader import ImageReader
from app.engine2_detector.signature_matcher import match_signature
from app.engine3_parsers.heimvision_parser import HeimVisionParser
from app.engine5_playback.decoder import StreamDecoder

E03_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "dds", "HeimVision K9604-W.E03")


@pytest.mark.skipif(not os.path.exists(E03_PATH), reason="HeimVision .E03 physical image not available")
def test_heimvision_real_image_detection_and_parsing():
    # 1. Match signature
    res = match_signature(E03_PATH)
    assert res.matched is True
    assert res.oem == "HeimVision"

    # 2. Parse VFS
    parser = HeimVisionParser()
    vfs = parser.parse(E03_PATH)
    assert "HeimVision" in vfs.oem
    assert len(vfs.channels) == 4
    assert len(vfs.files) == 4

    # 3. Verify channel 1 metadata
    f0 = vfs.files[0]
    assert f0.channel_id == 1
    assert "2021-08-04" in f0.start_timestamp

    # 4. Stream decoder decodes real 1080p frames
    with ImageReader(E03_PATH) as reader:
        start_sec = f0.cluster_runs[0].start_sector
        reader.seek(start_sec * 512)
        stream_bytes = reader.read(1024 * 1024)

    decoder = StreamDecoder(stream_bytes, oem="HeimVision", max_frames=10)
    assert decoder.get_frame_count() > 0
    frame = decoder.read_frame(0)
    assert frame is not None
    assert frame.shape == (1080, 1920, 3)
