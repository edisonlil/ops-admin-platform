"""
Deploy history and rollback management.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class DeployHistory:
    """Manages deployment history for each target."""
    
    def __init__(self, config_dir: Path):
        self.history_dir = config_dir / "deploy_history"
        self.history_dir.mkdir(exist_ok=True)
    
    def _get_history_file(self, target: str) -> Path:
        return self.history_dir / f"{target}.json"
    
    def record(self, target: str, version: str, image: str, success: bool, message: str = "") -> None:
        """Record a deployment."""
        history_file = self._get_history_file(target)
        
        history = []
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                pass
        
        # Add new record
        record = {
            "timestamp": datetime.now().isoformat(),
            "version": version,
            "image": image,
            "success": success,
            "message": message,
        }
        history.insert(0, record)  # Most recent first
        
        # Keep only last 50 records
        history = history[:50]
        
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    
    def get_history(self, target: str, limit: int = 10) -> list[dict]:
        """Get deployment history for target."""
        history_file = self._get_history_file(target)
        
        if not history_file.exists():
            return []
        
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            return history[:limit]
        except Exception:
            return []
    
    def get_last_successful(self, target: str) -> Optional[dict]:
        """Get the last successful deployment."""
        history = self.get_history(target, limit=20)
        for record in history:
            if record.get("success"):
                return record
        return None
    
    def clear(self, target: str) -> None:
        """Clear deployment history."""
        history_file = self._get_history_file(target)
        if history_file.exists():
            history_file.unlink()


def format_history_list(history: list[dict], limit: int = 10) -> str:
    """Format history for display."""
    if not history:
        return "  No deployment history."
    
    lines = []
    for i, record in enumerate(history[:limit], 1):
        status = "✓" if record.get("success") else "✗"
        timestamp = record.get("timestamp", "")
        # Parse and format timestamp
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            time_str = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            time_str = timestamp[:16]
        
        version = record.get("version", "unknown")
        msg = record.get("message", "")
        
        lines.append(f"  {i}. {status} {time_str} | {version}")
        if msg:
            lines.append(f"     {msg}")
    
    return "\n".join(lines)