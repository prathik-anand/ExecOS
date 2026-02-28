# boardroom services package — public entry point
from app.services.boardroom.pipeline import run_pipeline

__all__ = ["run_pipeline"]
