"""Utilities for reading and processing log files."""

import json
from pathlib import Path
from collections import deque
from typing import List, Dict, Any


def read_logs_reverse(file_path: Path, limit: int) -> List[Dict[str, Any]]:
    """Read last N lines from a JSONL file efficiently."""
    logs = deque(maxlen=limit)
    
    with open(file_path, "rb") as f:
        # Read file backwards
        f.seek(0, 2)  # Go to end
        file_size = f.tell()
        
        if file_size == 0:
            return []
        
        # Read chunks from end
        chunk_size = min(file_size, 8192)
        leftover = b''
        
        while f.tell() > 0 and len(logs) < limit:
            # Move backwards
            new_pos = max(0, f.tell() - chunk_size)
            f.seek(new_pos)
            
            # Read chunk
            chunk = f.read(min(chunk_size, f.tell()))
            f.seek(new_pos)  # Reset position
            
            # Process lines
            lines = (chunk + leftover).split(b'\n')
            leftover = lines[0]  # Incomplete line at start
            
            # Parse complete lines (in reverse)
            for line in reversed(lines[1:]):
                if line and len(logs) < limit:
                    try:
                        logs.appendleft(json.loads(line))
                    except:
                        continue
        
        # Handle any remaining data
        if leftover and len(logs) < limit:
            try:
                logs.appendleft(json.loads(leftover))
            except:
                pass
    
    return list(logs)


def parse_log_line(line: str) -> Dict[str, Any]:
    """Parse a single log line."""
    try:
        return json.loads(line)
    except:
        return {}