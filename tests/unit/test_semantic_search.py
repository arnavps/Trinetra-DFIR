"""
Unit tests for offline CLIP ViT-B/32 semantic search and local FAISS indexing.
"""

import os
import pytest
import numpy as np

from app.engine8_ai import semantic_search


def test_clip_faiss_indexing_and_query(tmp_path):
    """
    Tests building a local FAISS index from clip embeddings and querying with a natural-language string offline.
    """
    index_file = os.path.join(tmp_path, "test_faiss_index.bin")
    meta_file = os.path.join(tmp_path, "test_faiss_meta.json")

    # Generate synthetic clip records
    clip_records = [
        {
            "file_id": "clip1",
            "timestamp": "2026-09-04 12:00:00",
            "channel_id": 1,
            "description": "red car moving fast down street",
            "frame": np.ones((100, 100, 3), dtype=np.uint8) * 50,
        },
        {
            "file_id": "clip2",
            "timestamp": "2026-09-04 12:05:00",
            "channel_id": 2,
            "description": "person wearing blue hoodie walking",
            "frame": np.ones((100, 100, 3), dtype=np.uint8) * 200,
        },
    ]

    engine = semantic_search.CLIPEmbeddingEngine()

    total_indexed = semantic_search.build_faiss_index(
        clip_records,
        index_file_path=index_file,
        metadata_file_path=meta_file,
        clip_engine=engine,
    )

    assert total_indexed == 2
    assert os.path.exists(index_file)
    assert os.path.exists(meta_file)

    # Query semantic index with natural-language text
    results = semantic_search.query_semantic_search(
        query_text="red vehicle",
        index_file_path=index_file,
        metadata_file_path=meta_file,
        top_k=2,
        clip_engine=engine,
    )

    assert len(results) == 2
    assert "file_id" in results[0]
    assert "similarity_score" in results[0]
    assert isinstance(results[0]["similarity_score"], float)
