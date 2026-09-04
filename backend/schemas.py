"""Pydantic schemas shared by the inference API.

TrafficRow's fields mirror traffic_emergency_cyber_dataset.csv's header
exactly (minus the `label` column, which is the model's output, not its
input).
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TrafficRow(BaseModel):
    device_type: str
    zone_id: str
    protocol: str
    mqtt_msg_type: str
    src_port: int
    dst_port: int
    packet_size: int
    packets_per_second: float
    connection_duration: float
    bytes_transferred: int
    unique_dst_ips_contacted: int
    avg_request_interval: float
    syn_flag_count: int
    rst_flag_count: int
    failed_login_attempts: int
    is_encrypted: int
    mac_ip_mismatch: int
    signal_preemption_request: int
    gps_deviation_km: float
    hour_of_day: int
    day_type: str


class PredictionResponse(BaseModel):
    label: str
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: Literal["low", "medium", "high"]
    device_type: str
    zone_id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    inference_mode: Literal["trained", "heuristic"]
    confidence: Optional[float] = None
