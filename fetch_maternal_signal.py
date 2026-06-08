"""
Fetch yesterday's maternal signal from Google Health API and save to a JSON file
that heartbeat.py can read.

Run daily before heartbeat.py. Reads OAuth credentials from environment variables
(GitHub Secrets in CI, or local env for testing).

The script is intentionally tolerant of failures — if one data type isn't
available the rest still get saved. Missing fields end up as null in the output
JSON, which heartbeat.py treats as "no signal for this dimension today."
"""

import json
import os
import sys
import time
from datetime import date, timedelta, timezone, datetime
from pathlib import Path

import requests

BASE_URL = "https://health.googleapis.com/v4"
TOKEN_URL = "https://oauth2.googleapis.com/token"

OUTPUT_DIR = Path("maternal_signal")
RAW_DIR = OUTPUT_DIR / "raw"
DEBUG_RAW = os.environ.get("DEBUG_RAW") == "1"

PAGE_SIZE = 1000  # max samples per page for intraday queries


def dump_raw(name, target_date, response):
    if not DEBUG_RAW:
        return
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / f"{target_date.isoformat()}_{name}.json"
    path.write_text(json.dumps(response, indent=2) if response is not None else "null")
    print(f"  raw -> {path}", file=sys.stderr)


# ----- OAuth -----

def get_access_token():
    data = {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }
    last_exc = None
    for attempt in range(4):
        try:
            response = requests.post(TOKEN_URL, data=data, timeout=15)
            if response.status_code == 200:
                return response.json()["access_token"]
            if response.status_code < 500:
                response.raise_for_status()
            last_exc = requests.HTTPError(f"{response.status_code}: {response.text[:200]}")
        except requests.RequestException as e:
            last_exc = e
        time.sleep(2 ** attempt)
    raise last_exc


def auth_headers(token):
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


# ----- Generic list-with-pagination -----

def list_data_points(token, data_type, filter_expr=None):
    """List all data points for a data type, following nextPageToken."""
    url = f"{BASE_URL}/users/me/dataTypes/{data_type}/dataPoints"
    points = []
    params = {"pageSize": PAGE_SIZE}
    if filter_expr:
        params["filter"] = filter_expr
    while True:
        try:
            response = requests.get(url, headers=auth_headers(token), params=params, timeout=30)
        except Exception as e:
            print(f"  [{data_type}] request error: {e}", file=sys.stderr)
            return None
        if response.status_code != 200:
            print(f"  [{data_type}] HTTP {response.status_code}: {response.text[:300]}", file=sys.stderr)
            return None
        body = response.json()
        points.extend(body.get("dataPoints", []))
        token_next = body.get("nextPageToken")
        if not token_next:
            return {"dataPoints": points}
        params["pageToken"] = token_next


def fetch_daily_rollup(token, data_type, target_date):
    url = f"{BASE_URL}/users/me/dataTypes/{data_type}/dataPoints:dailyRollUp"
    body = {
        "range": {
            "start": {
                "date": {"year": target_date.year, "month": target_date.month, "day": target_date.day},
                "time": {"hours": 0, "minutes": 0, "seconds": 0, "nanos": 0},
            },
            "end": {
                "date": {"year": target_date.year, "month": target_date.month, "day": target_date.day},
                "time": {"hours": 23, "minutes": 59, "seconds": 59, "nanos": 0},
            },
        },
        "windowSizeDays": 1,
    }
    try:
        response = requests.post(url, headers=auth_headers(token), json=body, timeout=30)
    except Exception as e:
        print(f"  [{data_type} rollup] error: {e}", file=sys.stderr)
        return None
    if response.status_code != 200:
        print(f"  [{data_type} rollup] HTTP {response.status_code}: {response.text[:300]}", file=sys.stderr)
        return None
    return response.json()


# ----- Per-data-type fetchers -----

def fetch_heart_rate(token, target_date):
    start = f"{target_date.isoformat()}T00:00:00Z"
    end = f"{(target_date + timedelta(days=1)).isoformat()}T00:00:00Z"
    filter_expr = (
        f'heart_rate.sample_time.physical_time >= "{start}"'
        f' AND heart_rate.sample_time.physical_time < "{end}"'
    )
    return list_data_points(token, "heart-rate", filter_expr)


def fetch_hrv(token, target_date):
    start = f"{target_date.isoformat()}T00:00:00Z"
    end = f"{(target_date + timedelta(days=1)).isoformat()}T00:00:00Z"
    filter_expr = (
        f'heart_rate_variability.sample_time.physical_time >= "{start}"'
        f' AND heart_rate_variability.sample_time.physical_time < "{end}"'
    )
    return list_data_points(token, "heart-rate-variability", filter_expr)


def fetch_resting_hr(token, _target_date):
    # Daily record type — fetch recent points and pick the one matching target date
    # in summarize_resting_hr.
    return list_data_points(token, "daily-resting-heart-rate")


def fetch_sleep(token, target_date):
    # Sleep filter accepts interval.end_time but not start_time. Catch any session
    # ending on the target date (covers night-of going into morning-after).
    start = f"{target_date.isoformat()}T00:00:00Z"
    end = f"{(target_date + timedelta(days=2)).isoformat()}T00:00:00Z"
    filter_expr = (
        f'sleep.interval.end_time >= "{start}" AND sleep.interval.end_time < "{end}"'
    )
    return list_data_points(token, "sleep", filter_expr)


# ----- Summarization -----

def _to_float(v):
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def summarize_hr(response):
    if not response or not response.get("dataPoints"):
        return {"min": None, "max": None, "mean": None, "samples": 0}
    values = []
    for point in response["dataPoints"]:
        bpm = _to_float(point.get("heartRate", {}).get("beatsPerMinute"))
        if bpm is not None:
            values.append(bpm)
    if not values:
        return {"min": None, "max": None, "mean": None, "samples": 0}
    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
        "samples": len(values),
    }


def summarize_hrv(response):
    if not response or not response.get("dataPoints"):
        return {"mean_ms": None, "samples": 0}
    values = []
    for point in response["dataPoints"]:
        rmssd = _to_float(
            point.get("heartRateVariability", {})
                 .get("rootMeanSquareOfSuccessiveDifferencesMilliseconds")
        )
        if rmssd is not None:
            values.append(rmssd)
    if not values:
        return {"mean_ms": None, "samples": 0}
    return {"mean_ms": sum(values) / len(values), "samples": len(values)}


def summarize_resting_hr(response, target_date):
    if not response or not response.get("dataPoints"):
        return None
    for point in response["dataPoints"]:
        drhr = point.get("dailyRestingHeartRate", {})
        d = drhr.get("date", {})
        if (d.get("year") == target_date.year and d.get("month") == target_date.month
                and d.get("day") == target_date.day):
            return _to_float(drhr.get("beatsPerMinute"))
    return None


def _rfc3339_to_dt(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def summarize_sleep(response, target_date):
    """Aggregate the main sleep session that ends on target_date."""
    if not response or not response.get("dataPoints"):
        return {"minutes_asleep": None, "minutes_awake": None, "stages": None}
    main = None
    longest_dur = -1.0
    for point in response["dataPoints"]:
        sleep = point.get("sleep", {})
        interval = sleep.get("interval", {})
        start_s = interval.get("startTime")
        end_s = interval.get("endTime")
        if not start_s or not end_s:
            continue
        try:
            start = _rfc3339_to_dt(start_s)
            end = _rfc3339_to_dt(end_s)
        except Exception:
            continue
        if end.date() != target_date:
            continue
        dur = (end - start).total_seconds()
        if dur > longest_dur:
            longest_dur = dur
            main = sleep
    if main is None:
        return {"minutes_asleep": None, "minutes_awake": None, "stages": None}
    stages = {}
    minutes_asleep = 0
    minutes_awake = 0
    for stage in main.get("stages", []):
        try:
            start = _rfc3339_to_dt(stage["startTime"])
            end = _rfc3339_to_dt(stage["endTime"])
        except (KeyError, ValueError):
            continue
        minutes = (end - start).total_seconds() / 60.0
        kind = stage.get("type", "UNKNOWN")
        stages[kind] = stages.get(kind, 0) + minutes
        if kind == "AWAKE":
            minutes_awake += minutes
        else:
            minutes_asleep += minutes
    return {
        "minutes_asleep": int(round(minutes_asleep)),
        "minutes_awake": int(round(minutes_awake)),
        "stages": {k: int(round(v)) for k, v in stages.items()},
    }


def summarize_steps(response):
    if not response or not response.get("rollupDataPoints"):
        return None
    return _to_float(response["rollupDataPoints"][0].get("steps", {}).get("countSum"))


def summarize_active_minutes(response):
    if not response or not response.get("rollupDataPoints"):
        return None
    azm = response["rollupDataPoints"][0].get("activeZoneMinutes", {})
    total = 0.0
    any_field = False
    for key in ("sumInFatBurnHeartZone", "sumInCardioHeartZone", "sumInPeakHeartZone"):
        v = _to_float(azm.get(key))
        if v is not None:
            total += v
            any_field = True
    return total if any_field else None


# ----- Main -----

def main():
    target = date.today() - timedelta(days=1)
    if len(sys.argv) > 1:
        target = date.fromisoformat(sys.argv[1])

    print(f"Fetching maternal signal for {target}...")
    token = get_access_token()

    hr_raw = fetch_heart_rate(token, target);            dump_raw("heart_rate", target, hr_raw)
    hrv_raw = fetch_hrv(token, target);                  dump_raw("hrv", target, hrv_raw)
    resting_raw = fetch_resting_hr(token, target);       dump_raw("resting_hr", target, resting_raw)
    steps_raw = fetch_daily_rollup(token, "steps", target);              dump_raw("steps", target, steps_raw)
    active_raw = fetch_daily_rollup(token, "active-zone-minutes", target); dump_raw("active_minutes", target, active_raw)
    sleep_raw = fetch_sleep(token, target);              dump_raw("sleep", target, sleep_raw)

    signal = {
        "date": target.isoformat(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "heart_rate": summarize_hr(hr_raw),
        "hrv": summarize_hrv(hrv_raw),
        "resting_hr": summarize_resting_hr(resting_raw, target),
        "steps": summarize_steps(steps_raw),
        "active_minutes": summarize_active_minutes(active_raw),
        "sleep": summarize_sleep(sleep_raw, target),
        "notes": None,
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / f"{target.isoformat()}.json"
    out_path.write_text(json.dumps(signal, indent=2))
    print(f"Wrote {out_path}")
    print(json.dumps(signal, indent=2))


if __name__ == "__main__":
    main()
