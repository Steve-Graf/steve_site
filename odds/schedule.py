import json
import os
from datetime import datetime

SCHEDULE_PATH = os.path.join(os.path.dirname(__file__), "nfl_schedule.json")


def load_weeks():
    with open(SCHEDULE_PATH) as f:
        return json.load(f)


def _parse_iso_z(dt_str):
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


def get_nfl_week(target):
    weeks = load_weeks()

    for week in weeks:
        start = _parse_iso_z(week["startDate"])
        end = _parse_iso_z(week["endDate"])

        if start <= target <= end:
            return week
    return None
