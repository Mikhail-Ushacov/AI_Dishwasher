"""Serializers for replay data."""

import json
import gzip
from pathlib import Path
from typing import List, Optional, TextIO
from .models import ReplayMetadata, ReplayEvent


class JSONLSerializer:
    """Serializer for JSONL format (one JSON object per line)."""
    
    def __init__(self, filepath: str, compress: bool = False):
        self.filepath = Path(filepath)
        self.compress = compress
        self._file: Optional[TextIO] = None
        self._metadata_written = False
        
    def open(self):
        """Open the file for writing."""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if self.compress:
            self._file = gzip.open(self.filepath, 'wt', encoding='utf-8')
        else:
            self._file = open(self.filepath, 'w', encoding='utf-8')
            
    def close(self):
        """Close the file."""
        if self._file:
            self._file.close()
            self._file = None
            
    def write_metadata(self, metadata: ReplayMetadata):
        """Write metadata as the first line."""
        if not self._file:
            raise RuntimeError("Serializer not opened. Call open() first.")
            
        if self._metadata_written:
            raise RuntimeError("Metadata already written.")
            
        meta_dict = {"metadata": metadata.to_dict()}
        self._file.write(json.dumps(meta_dict) + '\n')
        self._metadata_written = True
        
    def write_event(self, event: ReplayEvent):
        """Write a single event."""
        if not self._file:
            raise RuntimeError("Serializer not opened. Call open() first.")
            
        if not self._metadata_written:
            raise RuntimeError("Metadata must be written before events.")
            
        self._file.write(json.dumps(event.to_dict()) + '\n')
        
    def write_events(self, events: List[ReplayEvent]):
        """Write multiple events."""
        for event in events:
            self.write_event(event)
            
    def __enter__(self):
        self.open()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class ReplayLoader:
    """Loader for replay files."""
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        
    def load(self) -> tuple:
        """Load a replay file and return (metadata, events)."""
        metadata = None
        events = []
        
        # Detect compression
        is_gz = self.filepath.suffix == '.gz' or str(self.filepath).endswith('.jsonl.gz')
        
        if is_gz:
            file = gzip.open(self.filepath, 'rt', encoding='utf-8')
        else:
            file = open(self.filepath, 'r', encoding='utf-8')
            
        try:
            for line_num, line in enumerate(file, 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"Warning: Invalid JSON at line {line_num}: {e}")
                    continue
                    
                if line_num == 1 and 'metadata' in data:
                    # First line is metadata
                    metadata = data['metadata']
                else:
                    # Subsequent lines are events
                    events.append(data)
                    
        finally:
            file.close()
            
        return metadata, events
