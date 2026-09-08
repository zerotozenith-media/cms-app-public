"""
Timers that ask the web app to run its scheduled commands.

The work happens in the Django app, not here. A Function that imported
Django would need its own copy of the code and its own database
credentials, and the two copies would eventually drift apart.
"""
import logging
import os

import azure.functions as func
import requests

app = func.FunctionApp()

BASE_URL = os.environ["DCLM_BASE_URL"].rstrip("/")
SECRET = os.environ["DCLM_TASK_SECRET"]


def _run(command: str):
    resp = requests.post(
        f"{BASE_URL}/api/tasks/run/",
        json={"command": command},
        headers={"X-Task-Secret": SECRET},
        timeout=300,
    )
    if resp.status_code != 200:
        # Raising makes the run show as failed in the portal. A quiet
        # failure here is the whole problem this exists to prevent.
        raise RuntimeError(f"{command} failed: {resp.status_code} {resp.text[:300]}")
    logging.info("%s: %s", command, resp.text[:300])


@app.timer_trigger(schedule="0 0 * * * *", arg_name="timer", run_on_startup=False)
def check_absences(timer: func.TimerRequest) -> None:
    """Hourly. Without this no follow-up task is ever created."""
    _run("check_absences")


@app.timer_trigger(schedule="0 0 2 * * *", arg_name="timer", run_on_startup=False)
def generate_recurring_sessions(timer: func.TimerRequest) -> None:
    """Daily. Without this no weekly sessions appear to be filled in."""
    _run("generate_recurring_sessions")


@app.timer_trigger(schedule="0 0 7 * * *", arg_name="timer", run_on_startup=False)
def send_followup_digests(timer: func.TimerRequest) -> None:
    _run("send_followup_digests")


@app.timer_trigger(schedule="0 30 7 * * 1", arg_name="timer", run_on_startup=False)
def send_leadership_summary(timer: func.TimerRequest) -> None:
    _run("send_leadership_summary")
