#!/usr/bin/env python
"""Test script for time control selection feature."""
import requests
import json
from pprint import pprint

API_URL = "http://localhost:8000"


def test_time_controls_endpoint():
    """Test the time controls discovery endpoint."""
    print("\n" + "=" * 80)
    print("Testing /api/analysis/time-controls endpoint")
    print("=" * 80)

    # Test with Lichess user
    print("\n1. Testing with Lichess user 'sumosalami'...")
    response = requests.post(
        f"{API_URL}/api/analysis/time-controls",
        json={
            "platform": "lichess",
            "username": "sumosalami",
            "sample_size": 100
        }
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nUsername: {data['username']}")
        print(f"Platform: {data['platform']}")
        print(f"Total Sampled: {data['total_sampled']}")
        print(f"\nTime Controls Found: {len(data['time_controls'])}")
        print("\nTime Controls:")
        for tc in data['time_controls']:
            print(f"  - {tc['display_name']}: {tc['count']} games ({tc['category']})")
    else:
        print(f"Error: {response.text}")


def test_filtered_analysis():
    """Test starting an analysis with time control filter."""
    print("\n" + "=" * 80)
    print("Testing filtered analysis")
    print("=" * 80)

    # First get time controls
    print("\n1. Getting time controls for user...")
    response = requests.post(
        f"{API_URL}/api/analysis/time-controls",
        json={
            "platform": "lichess",
            "username": "sumosalami",
            "sample_size": 50
        }
    )

    if response.status_code != 200:
        print(f"Error getting time controls: {response.text}")
        return

    data = response.json()
    if not data['time_controls']:
        print("No time controls found!")
        return

    # Use the first time control
    time_control = data['time_controls'][0]['time_control']
    print(f"\n2. Starting analysis with time control: {time_control}")

    response = requests.post(
        f"{API_URL}/api/analysis/start",
        json={
            "platform": "lichess",
            "username": "sumosalami",
            "limit": 10,
            "time_control": time_control
        }
    )

    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nJob ID: {data['job_id']}")
        print(f"Status: {data['status']}")
        print(f"Message: {data['message']}")
        print(f"\nYou can check the results at:")
        print(f"  http://localhost:3000/results/{data['job_id']}")
    else:
        print(f"Error: {response.text}")


def test_error_cases():
    """Test error handling."""
    print("\n" + "=" * 80)
    print("Testing error cases")
    print("=" * 80)

    # Test 1: Invalid platform
    print("\n1. Testing invalid platform...")
    response = requests.post(
        f"{API_URL}/api/analysis/time-controls",
        json={
            "platform": "invalid",
            "username": "test",
            "sample_size": 50
        }
    )
    print(f"Status Code: {response.status_code} (expected 400)")
    if response.status_code != 200:
        print(f"Error: {response.json()['detail']}")

    # Test 2: Empty username
    print("\n2. Testing empty username...")
    response = requests.post(
        f"{API_URL}/api/analysis/time-controls",
        json={
            "platform": "lichess",
            "username": "",
            "sample_size": 50
        }
    )
    print(f"Status Code: {response.status_code} (expected 400)")
    if response.status_code != 200:
        print(f"Error: {response.json()['detail']}")

    # Test 3: Non-existent user
    print("\n3. Testing non-existent user...")
    response = requests.post(
        f"{API_URL}/api/analysis/time-controls",
        json={
            "platform": "lichess",
            "username": "thisuserdoesnotexist123456789",
            "sample_size": 50
        }
    )
    print(f"Status Code: {response.status_code} (expected 404 or 500)")
    if response.status_code != 200:
        error_data = response.json()
        print(f"Error: {error_data.get('detail', error_data)}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("TIME CONTROL SELECTION FEATURE - TEST SUITE")
    print("=" * 80)
    print("\nMake sure the backend is running on http://localhost:8000")
    input("Press Enter to start tests...")

    try:
        # Test 1: Time controls endpoint
        test_time_controls_endpoint()

        input("\nPress Enter to continue to filtered analysis test...")

        # Test 2: Filtered analysis
        test_filtered_analysis()

        input("\nPress Enter to continue to error case tests...")

        # Test 3: Error cases
        test_error_cases()

        print("\n" + "=" * 80)
        print("All tests completed!")
        print("=" * 80)

    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to API at http://localhost:8000")
        print("Make sure the backend is running:")
        print("  cd backend && docker-compose up -d")
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
