from typing import Optional
from pydantic import BaseModel


class WebhookConfig(BaseModel):
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    secret: Optional[str] = None
    review_command: str = "run"  # run, run-inline, run-summary, run-context