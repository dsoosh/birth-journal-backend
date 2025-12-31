#!/usr/bin/env python3
"""
Wipe database and populate with test data for development/testing.

Usage:
    python scripts/seed_test_data.py
    python scripts/seed_test_data.py --url http://192.168.0.245:8000
"""

import argparse
import datetime as dt
import random
import sys
import uuid

import requests


def main():
    parser = argparse.ArgumentParser(
        description="Wipe database and seed with test data."
    )
    parser.add_argument(
        "--url",
        type=str,
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--midwife-email",
        type=str,
        default="test@midwife.com",
        help="Midwife email (default: test@midwife.com)",
    )
    parser.add_argument(
        "--midwife-password",
        type=str,
        default="test123",
        help="Midwife password (default: test123)",
    )
    parser.add_argument(
        "--no-wipe",
        action="store_true",
        help="Skip database wipe (just add data)",
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    api_url = f"{base_url}/api/v1"

    print("=" * 50)
    print("  Seed Test Data")
    print("=" * 50)
    print(f"\nBackend: {base_url}")

    # Step 1: Wipe database (if enabled)
    if not args.no_wipe:
        print("\n[1/5] Wiping database...")
        try:
            resp = requests.post(f"{api_url}/dev/wipe", timeout=10)
            if resp.status_code == 200:
                print("      ✓ Database wiped")
            elif resp.status_code == 404:
                print("      ⚠ Wipe endpoint not available (add it or use --no-wipe)")
            else:
                print(f"      ✗ Wipe failed: {resp.status_code} {resp.text}")
        except requests.exceptions.RequestException as e:
            print(f"      ✗ Wipe failed: {e}")
    else:
        print("\n[1/5] Skipping database wipe (--no-wipe)")

    # Step 2: Create midwife account
    print("\n[2/5] Creating midwife account...")
    try:
        resp = requests.post(
            f"{api_url}/auth/test-account",
            json={"email": args.midwife_email, "password": args.midwife_password},
            timeout=5,
        )
        resp.raise_for_status()
        midwife_token = resp.json()["token"]
        print(f"      ✓ Midwife: {args.midwife_email}")
    except requests.exceptions.RequestException as e:
        print(f"      ✗ Failed to create midwife: {e}")
        sys.exit(1)

    headers = {"Authorization": f"Bearer {midwife_token}"}

    # Step 3: Create a case
    print("\n[3/5] Creating case...")
    try:
        resp = requests.post(f"{api_url}/cases", headers=headers, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        case_id = data["case_id"]
        join_code = data["join_code"]
        print(f"      ✓ Case ID: {case_id}")
        print(f"      ✓ Join Code: {join_code}")
    except requests.exceptions.RequestException as e:
        print(f"      ✗ Failed to create case: {e}")
        sys.exit(1)

    # Step 4: Join as patient to get patient token
    print("\n[4/5] Joining as patient...")
    try:
        resp = requests.post(
            f"{api_url}/cases/join",
            json={"join_code": join_code},
            timeout=5,
        )
        resp.raise_for_status()
        patient_token = resp.json()["token"]
        print("      ✓ Patient joined case")
    except requests.exceptions.RequestException as e:
        print(f"      ✗ Failed to join case: {e}")
        sys.exit(1)

    patient_headers = {"Authorization": f"Bearer {patient_token}"}

    # Step 5: Seed contraction events over the last 8 hours
    print("\n[5/5] Seeding contraction events...")
    now = dt.datetime.now(dt.timezone.utc)
    events = []

    # Generate realistic contraction patterns
    # Early labor: contractions every 15-20 min, 30-45 sec
    # Active labor: contractions every 3-5 min, 45-60 sec
    
    # Simulate 8 hours of labor with increasing frequency
    hours_back = 8
    current_time = now - dt.timedelta(hours=hours_back)
    
    contraction_count = 0
    while current_time < now:
        # Calculate progression (0 = start, 1 = now)
        progression = (now - current_time).total_seconds() / (hours_back * 3600)
        progression = 1 - progression  # Invert so 0 = 8h ago, 1 = now
        
        # Gap between contractions decreases as labor progresses
        # Early: 15-20 min, Active: 3-5 min
        if progression < 0.3:
            gap_minutes = random.uniform(15, 20)
            duration_seconds = random.randint(30, 45)
        elif progression < 0.6:
            gap_minutes = random.uniform(8, 12)
            duration_seconds = random.randint(40, 50)
        else:
            gap_minutes = random.uniform(3, 6)
            duration_seconds = random.randint(45, 65)
        
        # contraction_start event
        start_id = str(uuid.uuid4())
        start_time = current_time
        events.append({
            "event_id": start_id,
            "case_id": case_id,
            "type": "contraction_start",
            "ts": start_time.isoformat(),
            "payload_v": 1,
            "payload": {"local_seq": int(start_time.timestamp() * 1000)},
        })
        
        # contraction_end event
        end_time = start_time + dt.timedelta(seconds=duration_seconds)
        end_id = str(uuid.uuid4())
        events.append({
            "event_id": end_id,
            "case_id": case_id,
            "type": "contraction_end",
            "ts": end_time.isoformat(),
            "payload_v": 1,
            "payload": {"duration_s": duration_seconds},
        })
        
        contraction_count += 1
        current_time = end_time + dt.timedelta(minutes=gap_minutes)

    # Add a set_labor_active event at the beginning
    labor_active_event = {
        "event_id": str(uuid.uuid4()),
        "case_id": case_id,
        "type": "set_labor_active",
        "ts": (now - dt.timedelta(hours=hours_back)).isoformat(),
        "payload_v": 1,
        "payload": {"active": True},
    }
    events.insert(0, labor_active_event)

    # Add some symptom events
    symptom_events = [
        {
            "event_id": str(uuid.uuid4()),
            "case_id": case_id,
            "type": "labor_event",
            "ts": (now - dt.timedelta(hours=6)).isoformat(),
            "payload_v": 1,
            "payload": {"kind": "mucus_plug", "severity": "medium"},
        },
        {
            "event_id": str(uuid.uuid4()),
            "case_id": case_id,
            "type": "labor_event",
            "ts": (now - dt.timedelta(hours=2)).isoformat(),
            "payload_v": 1,
            "payload": {"kind": "waters_breaking", "severity": "high"},
        },
    ]
    events.extend(symptom_events)

    # Sync events to server
    try:
        resp = requests.post(
            f"{api_url}/events/sync",
            json={"cursor": None, "events": events},
            headers=patient_headers,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
        accepted = len(result.get("accepted_event_ids", []))
        rejected = len(result.get("rejected", []))
        print(f"      ✓ Created {contraction_count} contractions ({accepted} events accepted, {rejected} rejected)")
    except requests.exceptions.RequestException as e:
        print(f"      ✗ Failed to sync events: {e}")
        sys.exit(1)

    # Summary
    print("\n" + "=" * 50)
    print("  Test Data Seeded Successfully!")
    print("=" * 50)
    print(f"\nMidwife Login:")
    print(f"  Email: {args.midwife_email}")
    print(f"  Password: {args.midwife_password}")
    print(f"\nPatient Join Code: {join_code}")
    print(f"\nCase ID: {case_id}")
    print(f"\nContraction Summary:")
    print(f"  - {contraction_count} contractions over {hours_back} hours")
    print(f"  - Pattern simulates early to active labor progression")
    print(f"  - Includes mucus plug and waters breaking events")
    print()


if __name__ == "__main__":
    main()
