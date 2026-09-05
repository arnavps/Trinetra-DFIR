//! PyO3 module entrypoint; registers raw_io, hasher and nal_scanner functions as the Python-importable unidvr_rustcore module.

pub mod raw_io;
pub mod hasher;
pub mod nal_scanner;
pub mod bindings;

use pyo3::prelude::*;

#[pymodule]
fn unidvr_rustcore(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(bindings::hash_file, m)?)?;
    m.add_function(wrap_pyfunction!(bindings::verify_read_only, m)?)?;
    Ok(())
}
