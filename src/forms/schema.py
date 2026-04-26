"""Structured schema for a DA-31 leave request."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

LeaveType = Literal["ORDINARY", "EMERGENCY", "PERMISSIVE_TDY", "OTHER"]


class LeaveRequest(BaseModel):
    name: str = Field(..., description="Soldier's name in 'LAST, FIRST MI' format")
    rank: str = Field(..., description="Rank abbreviation, e.g. SPC, SGT, CPT")
    ssn: str = Field(default="XXX-XX-XXXX")
    org_station: str = Field(..., description="Unit, station, phone")
    leave_address: str = Field(..., description="Address during leave")
    leave_type: LeaveType = Field(default="ORDINARY")
    days_requested: int = Field(..., gt=0, le=120)
    days_accrued: float = Field(default=15.0, ge=0)
    date_from: date
    date_to: date
    control_number: str = Field(default="")

    def to_form_dict(self) -> dict:
        return {
            "control_number": self.control_number,
            "name": self.name,
            "ssn": self.ssn,
            "rank": self.rank,
            "date": date.today().strftime("%d %b %y").upper(),
            "leave_address": self.leave_address,
            "type_ordinary": "X" if self.leave_type == "ORDINARY" else "",
            "type_emergency": "X" if self.leave_type == "EMERGENCY" else "",
            "type_permissive": "X" if self.leave_type == "PERMISSIVE_TDY" else "",
            "type_other": "X" if self.leave_type == "OTHER" else "",
            "org_station": self.org_station,
            "days_accrued": str(self.days_accrued),
            "days_requested": str(self.days_requested),
            "date_from": self.date_from.strftime("%d %b %y").upper(),
            "date_to": self.date_to.strftime("%d %b %y").upper(),
            "signature_req": f"/s/ {self.name.split(',')[0]}",
        }