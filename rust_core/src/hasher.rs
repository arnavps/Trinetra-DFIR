//! Streaming MD5 + SHA-256 over that chunk stream, plus the per-block Merkle tree builder.

use std::io;
use md5::Md5;
use sha2::{Digest, Sha256};
use crate::raw_io::RawReader;

#[derive(Debug, Clone)]
pub struct HashResult {
    pub md5_hex: String,
    pub sha256_hex: String,
    pub merkle_root_hex: String,
    pub total_bytes: u64,
}

pub fn compute_merkle_root(leaf_hashes: &[Vec<u8>]) -> Vec<u8> {
    if leaf_hashes.is_empty() {
        return Sha256::digest(b"").to_vec();
    }

    let mut current_layer: Vec<Vec<u8>> = leaf_hashes.to_vec();

    while current_layer.len() > 1 {
        let mut next_layer = Vec::new();
        let len = current_layer.len();
        let mut i = 0;
        while i < len {
            if i + 1 < len {
                let mut hasher = Sha256::new();
                hasher.update(&current_layer[i]);
                hasher.update(&current_layer[i + 1]);
                next_layer.push(hasher.finalize().to_vec());
            } else {
                let mut hasher = Sha256::new();
                hasher.update(&current_layer[i]);
                hasher.update(&current_layer[i]);
                next_layer.push(hasher.finalize().to_vec());
            }
            i += 2;
        }
        current_layer = next_layer;
    }

    current_layer[0].clone()
}

pub fn hash_reader(reader: &mut RawReader) -> io::Result<HashResult> {
    let mut md5_hasher = Md5::new();
    let mut sha256_hasher = Sha256::new();
    let mut leaf_hashes: Vec<Vec<u8>> = Vec::new();

    let total_bytes = reader.read_chunks(|chunk| {
        md5_hasher.update(chunk);
        sha256_hasher.update(chunk);

        let mut leaf_hasher = Sha256::new();
        leaf_hasher.update(chunk);
        leaf_hashes.push(leaf_hasher.finalize().to_vec());

        Ok(())
    })?;

    let md5_bytes = md5_hasher.finalize();
    let sha256_bytes = sha256_hasher.finalize();
    let merkle_root_bytes = compute_merkle_root(&leaf_hashes);

    let md5_hex = hex_encode(&md5_bytes);
    let sha256_hex = hex_encode(&sha256_bytes);
    let merkle_root_hex = hex_encode(&merkle_root_bytes);

    Ok(HashResult {
        md5_hex,
        sha256_hex,
        merkle_root_hex,
        total_bytes,
    })
}

fn hex_encode(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}
