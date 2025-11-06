#!/usr/bin/env python3
"""
Trigger an Airflow DAG on AWS MWAA and wait for completion.

This script:
1. Gets a CLI token from AWS MWAA
2. Triggers a DAG run via Airflow CLI command
3. Polls the DAG run status until completion
4. Exits with code 0 on success, 1 on failure

Environment variables required:
- AWS_REGION: AWS region (e.g., eu-west-2)
- MWAA_ENVIRONMENT_NAME: Name of MWAA environment
- DAG_ID: ID of the DAG to trigger
- TIMEOUT_MINUTES: (Optional) Maximum time to wait, default 10
"""

import base64
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import subprocess


def get_mwaa_cli_token(environment_name, region):
    """Get a CLI token for MWAA environment."""
    print(f"Getting CLI token for MWAA environment: {environment_name}")

    try:
        result = subprocess.run(
            [
                "aws", "mwaa", "create-cli-token",
                "--name", environment_name,
                "--region", region
            ],
            capture_output=True,
            text=True,
            check=True
        )

        token_data = json.loads(result.stdout)
        return token_data["CliToken"], token_data["WebServerHostname"]
    except subprocess.CalledProcessError as e:
        print(f"Error getting CLI token: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing token response: {e}", file=sys.stderr)
        sys.exit(1)


def execute_mwaa_cli_command(webserver_hostname, token, command):
    """Execute an Airflow CLI command via MWAA CLI endpoint."""
    url = f"https://{webserver_hostname}/aws_mwaa/cli"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "text/plain"
    }

    request = Request(url, data=command.encode("utf-8"), headers=headers, method="POST")

    try:
        with urlopen(request) as response:
            response_data = json.loads(response.read().decode("utf-8"))
            # MWAA returns base64-encoded stdout/stderr
            stdout_b64 = response_data.get("stdout", "")
            stderr_b64 = response_data.get("stderr", "")

            stdout = base64.b64decode(stdout_b64).decode("utf-8") if stdout_b64 else ""
            stderr = base64.b64decode(stderr_b64).decode("utf-8") if stderr_b64 else ""

            return stdout, stderr
    except HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code}: {error_body}", file=sys.stderr)
        raise
    except URLError as e:
        print(f"URL Error: {e.reason}", file=sys.stderr)
        raise


def trigger_dag(environment_name, region, dag_id):
    """Trigger a DAG run and return the run ID."""
    print(f"\nTriggering DAG: {dag_id}")

    # Get a fresh token (valid for 60 seconds)
    token, webserver_hostname = get_mwaa_cli_token(environment_name, region)

    # Add note and conf to identify this was triggered by our script
    trigger_note = "Triggered by GitHub Actions deployment script"
    command = f'dags trigger {dag_id} --conf \'{{"triggered_by":"github-actions-script","timestamp":"{datetime.now(timezone.utc).isoformat()}"}}\''

    try:
        stdout, stderr = execute_mwaa_cli_command(webserver_hostname, token, command)

        if stderr and "error" in stderr.lower():
            print(f"Error triggering DAG: {stderr}", file=sys.stderr)
            sys.exit(1)

        # Parse the dag_run_id from table output
        # Look for manual__YYYY-MM-DDTHH:MM:SS+00:00 pattern
        match = re.search(r'manual__\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2}', stdout)
        if match:
            dag_run_id = match.group(0)
            print(f"✓ DAG run triggered: {dag_run_id}")
            return dag_run_id

        # Fallback: extract timestamp and construct run ID
        match = re.search(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+\d{2}:\d{2})', stdout)
        if match:
            dag_run_id = f"manual__{match.group(1)}"
            print(f"✓ DAG run triggered: {dag_run_id}")
            return dag_run_id

        # If we can't parse, that's okay - we'll check the latest run
        print("✓ DAG triggered (will monitor latest run)")
        return None

    except Exception as e:
        print(f"Failed to trigger DAG: {e}", file=sys.stderr)
        sys.exit(1)


def get_dag_run_state(environment_name, region, dag_id, dag_run_id):
    """Get the current state of a DAG run using CLI."""
    # Get a fresh token
    token, webserver_hostname = get_mwaa_cli_token(environment_name, region)

    # Use "dags list-runs" with specific run_id if available
    if dag_run_id:
        command = f"dags list-runs -d {dag_id} --run-id {dag_run_id} --no-backfill"
    else:
        command = f"dags list-runs -d {dag_id} --no-backfill"

    try:
        stdout, stderr = execute_mwaa_cli_command(webserver_hostname, token, command)

        if stdout:
            # Parse table output - format: dag_id | run_id | state | execution_date | start_date | end_date
            lines = [l for l in stdout.split('\n') if l.strip() and not l.strip().startswith('=')]

            # Find data lines (skip header line)
            data_lines = []
            for line in lines:
                if '|' in line and 'dag_id' not in line and 'run_id' not in line:
                    data_lines.append(line)

            if data_lines:
                # Use first matching line (most recent run if dag_run_id not specified)
                target_line = data_lines[0]

                if dag_run_id:
                    # Find the specific run
                    for line in data_lines:
                        if dag_run_id in line:
                            target_line = line
                            break

                # Parse the line: split by '|' and extract fields
                parts = [p.strip() for p in target_line.split('|')]
                if len(parts) >= 6:
                    run_id = parts[1]
                    state = parts[2]
                    start_date = parts[4]
                    end_date = parts[5]

                    return state, {
                        "run_id": run_id,
                        "state": state,
                        "start_date": start_date,
                        "end_date": end_date
                    }

        return None, None

    except Exception as e:
        print(f"Error getting DAG run state: {e}", file=sys.stderr)
        return None, None


def wait_for_completion(environment_name, region, dag_id, dag_run_id, timeout_minutes=10):
    """Wait for DAG run to complete, polling every 30 seconds."""
    print(f"\nWaiting for DAG run to complete (timeout: {timeout_minutes} minutes)...")
    print("─" * 60)

    start_time = time.time()
    timeout_seconds = timeout_minutes * 60
    poll_interval = 30
    last_state = None

    while True:
        elapsed = time.time() - start_time

        if elapsed > timeout_seconds:
            print(f"\n✗ Timeout reached after {timeout_minutes} minutes", file=sys.stderr)
            return False

        state, run_info = get_dag_run_state(environment_name, region, dag_id, dag_run_id)

        if not state:
            print(f"[{int(elapsed):>5}s] Waiting for run to appear...")
            time.sleep(poll_interval)
            continue

        elapsed_str = f"{int(elapsed)}s"

        # Only print if state changed
        if state != last_state:
            print(f"[{elapsed_str:>5}] State: {state}")
            last_state = state

        if state == "success":
            print("─" * 60)
            print(f"✓ DAG run completed successfully!")
            if run_info:
                print(f"  Run ID: {run_info.get('run_id')}")
                print(f"  Start: {run_info.get('start_date')}")
                print(f"  End: {run_info.get('end_date')}")
            return True

        elif state == "failed":
            print("─" * 60)
            print(f"✗ DAG run failed!", file=sys.stderr)
            if run_info:
                print(f"  Run ID: {run_info.get('run_id')}", file=sys.stderr)
                print(f"  Start: {run_info.get('start_date')}", file=sys.stderr)
                print(f"  End: {run_info.get('end_date')}", file=sys.stderr)
            return False

        elif state in ["running", "queued"]:
            time.sleep(poll_interval)

        else:
            print(f"[{elapsed_str:>5}] State: {state} (unexpected)")
            time.sleep(poll_interval)


def main():
    """Main execution function."""
    # Get environment variables
    region = os.environ.get("AWS_REGION")
    environment_name = os.environ.get("MWAA_ENVIRONMENT_NAME")
    dag_id = os.environ.get("DAG_ID")
    timeout_minutes = int(os.environ.get("TIMEOUT_MINUTES", "10"))

    # Validate required variables
    if not all([region, environment_name, dag_id]):
        print("Error: Missing required environment variables", file=sys.stderr)
        print("Required: AWS_REGION, MWAA_ENVIRONMENT_NAME, DAG_ID", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("AWS MWAA DAG Trigger and Status Check")
    print("=" * 60)
    print(f"Environment: {environment_name}")
    print(f"Region: {region}")
    print(f"DAG ID: {dag_id}")
    print(f"Timeout: {timeout_minutes} minutes")
    print("=" * 60)

    # Trigger DAG
    dag_run_id = trigger_dag(environment_name, region, dag_id)

    # Wait for completion
    success = wait_for_completion(
        environment_name,
        region,
        dag_id,
        dag_run_id,
        timeout_minutes
    )

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
