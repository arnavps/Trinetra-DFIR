//! Block-level, strictly read-only reader over a physical drive path or image file; chunked 4–16MB reads.

use std::fs::{File, OpenOptions};
use std::io::{self, Read, Seek, SeekFrom};
use std::path::Path;

pub const DEFAULT_CHUNK_SIZE: usize = 4 * 1024 * 1024; // 4MB

pub struct RawReader {
    file: File,
    chunk_size: usize,
    total_bytes: u64,
}

impl RawReader {
    pub fn open<P: AsRef<Path>>(path: P, chunk_size: Option<usize>) -> io::Result<Self> {
        let file = OpenOptions::new()
            .read(true)
            .write(false)
            .open(path)?;

        let metadata = file.metadata()?;
        let total_bytes = metadata.len();
        let chunk_size = chunk_size.unwrap_or(DEFAULT_CHUNK_SIZE);

        Ok(Self {
            file,
            chunk_size,
            total_bytes,
        })
    }

    pub fn total_bytes(&self) -> u64 {
        self.total_bytes
    }

    pub fn chunk_size(&self) -> usize {
        self.chunk_size
    }

    pub fn read_chunks<F>(&mut self, mut callback: F) -> io::Result<u64>
    where
        F: FnMut(&[u8]) -> io::Result<()>,
    {
        self.file.seek(SeekFrom::Start(0))?;
        let mut buffer = vec![0u8; self.chunk_size];
        let mut bytes_read_total = 0u64;

        loop {
            let n = self.file.read(&mut buffer)?;
            if n == 0 {
                break;
            }
            callback(&buffer[..n])?;
            bytes_read_total += n as u64;
        }

        Ok(bytes_read_total)
    }
}
