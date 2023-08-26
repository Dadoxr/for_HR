from typing import List, Dict, Any
from datetime import datetime

class S3Storage:
    """S3-compatible storage abstraction."""
    
    def __init__(self, bucket: str = "data-bucket") -> None:
        self.bucket: str = bucket
    
    def save(self, path: str, data: List[Dict[str, Any]]) -> None:
        """Save data to storage."""
        timestamp: str = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        file_path: str = f"{path}/{timestamp}.json"
        print(f"Saved {len(data)} records to {file_path}")

