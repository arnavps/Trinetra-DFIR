//! #[pyfunction] wrappers exposing the above to Python with typed error conversion.

use pyo3::exceptions::PyIOError;
use pyo3::prelude::*;
use crate::hasher::hash_reader;
use crate::raw_io::RawReader;
use crate::nal_scanner::scan_nal_start_codes;

#[pyfunction]
pub fn hash_file(path: &str, chunk_size: Option<usize>) -> PyResult<(String, String, String, u64)> {
    let mut reader = RawReader::open(path, chunk_size)
        .map_err(|e| PyIOError::new_err(format!("Failed to open file '{}': {}", path, e)))?;

    let res = hash_reader(&mut reader)
        .map_err(|e| PyIOError::new_err(format!("Hashing error on '{}': {}", path, e)))?;

    Ok((res.md5_hex, res.sha256_hex, res.merkle_root_hex, res.total_bytes))
}

#[pyfunction]
pub fn verify_read_only(path: &str) -> PyResult<bool> {
    use std::fs::OpenOptions;
    let ro_res = OpenOptions::new().read(true).write(false).open(path);
    if ro_res.is_err() {
        return Ok(false);
    }
    Ok(true)
}

#[pyfunction]
pub fn find_nal_start_codes(data: &[u8], max_units: Option<usize>) -> PyResult<Vec<usize>> {
    let limit = max_units.unwrap_or(2000);
    Ok(scan_nal_start_codes(data, limit))
}
