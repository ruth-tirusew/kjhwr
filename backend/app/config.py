from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    snapshot_dir: Path = Path(__file__).resolve().parents[2] / "data" / "snapshots"
    snapshot_id: str | None = None  # optional pin; empty or unset serves the newest snapshot
    cors_origins: str = "http://localhost:5173"
    default_cutoff: str = "09:00"  # UK time on D-1; configurable
    period_start: str = "2026-01-01"
    period_end: str = "2026-01-31"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
