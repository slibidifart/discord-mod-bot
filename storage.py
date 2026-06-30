import json
import os
from pathlib import Path
from typing import Any


class Store:
    def __init__(self, file_name: str | None = None):
        self.path = Path(file_name or os.getenv("DATA_FILE", "data/bot_data.json"))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, Any] = {"guilds": {}}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self._save()
            return
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                self.data = loaded
            self.data.setdefault("guilds", {})
        except (OSError, json.JSONDecodeError):
            backup = self.path.with_suffix(f".broken-{int(self.path.stat().st_mtime)}.json")
            self.path.replace(backup)
            self.data = {"guilds": {}}
            self._save()

    def _save(self) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    def guild(self, guild_id: int) -> dict[str, Any]:
        guilds = self.data.setdefault("guilds", {})
        record = guilds.setdefault(str(guild_id), {})
        record.setdefault("config", {"verified_role_id": None, "log_channel_id": None})
        record.setdefault("pending", {})
        record.setdefault("verifications", {})
        record.setdefault("warnings", {})
        return record

    def get_config(self, guild_id: int) -> dict[str, Any]:
        return self.guild(guild_id)["config"]

    def set_config(self, guild_id: int, key: str, value: Any) -> None:
        self.guild(guild_id)["config"][key] = value
        self._save()

    def set_pending(self, guild_id: int, user_id: int, value: dict[str, Any]) -> None:
        self.guild(guild_id)["pending"][str(user_id)] = value
        self._save()

    def get_pending(self, guild_id: int, user_id: int) -> dict[str, Any] | None:
        return self.guild(guild_id)["pending"].get(str(user_id))

    def remove_pending(self, guild_id: int, user_id: int) -> None:
        self.guild(guild_id)["pending"].pop(str(user_id), None)
        self._save()

    def set_verification(self, guild_id: int, user_id: int, value: dict[str, Any]) -> None:
        record = self.guild(guild_id)
        record["verifications"][str(user_id)] = value
        record["pending"].pop(str(user_id), None)
        self._save()

    def get_verification(self, guild_id: int, user_id: int) -> dict[str, Any] | None:
        return self.guild(guild_id)["verifications"].get(str(user_id))

    def remove_verification(self, guild_id: int, user_id: int) -> dict[str, Any] | None:
        record = self.guild(guild_id)
        previous = record["verifications"].pop(str(user_id), None)
        record["pending"].pop(str(user_id), None)
        self._save()
        return previous

    def add_warning(self, guild_id: int, user_id: int, warning: dict[str, Any]) -> int:
        warnings = self.guild(guild_id)["warnings"].setdefault(str(user_id), [])
        warnings.append(warning)
        self._save()
        return len(warnings)

    def get_warnings(self, guild_id: int, user_id: int) -> list[dict[str, Any]]:
        return self.guild(guild_id)["warnings"].get(str(user_id), [])

    def clear_warnings(self, guild_id: int, user_id: int) -> int:
        record = self.guild(guild_id)
        count = len(record["warnings"].pop(str(user_id), []))
        self._save()
        return count
