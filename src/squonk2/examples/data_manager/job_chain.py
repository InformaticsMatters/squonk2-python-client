#!/usr/bin/env python
"""Runs two Jobs, one after the other.

The jobs executed in the example file (jobs.yaml) are jobs that are often built into
the DM deployment, and are part of the im-test collection. The Jobs may not be
available to you in your installation.

The Job file is a YAML file and typically looks like this: -

    ---
    # A chain of Jobs
    - name: Job A
      specification:
        collection: im-test
        job: event-test
        version: '1.0.0'
    - name: Job B
      specification:
        collection: im-test
        job: coin-test
        version: '1.0.0'

You are expected to have an existing project.

You can use a token (and DM API URL) or an environment file
(i.e. a ~/.squonk2/environments file)

To run the example file on an environment you've configured called 'dls-test'
run the following from the examples directory: -

    ./job_chain.py project-00000000-0000-0000-0000-000000000000 jobs.yaml \
        -e dls-test

If you prefer to use a token against the Data Manager at
https://data-manager.example.com/data-manager-api run: -

    ./job_chain.py project-00000000-0000-0000-0000-000000000000 jobs.yaml \
        -t eyJhbGciO...bV9ZqPgIBQ \
        -d https://data-manager.example.com/data-manager-api

"""
import argparse
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import yaml

from squonk2.auth import Auth
from squonk2.dm_api import DmApi, DmApiRv
from squonk2.environment import Environment

_MAX_JOB_WAIT_S: float = 120.0
_PER_QUERY_SLEEP_S: float = 1.0


def handle_dmapirv(api_rv: DmApiRv, *, quiet: bool = False) -> None:
    """Given a DmAPiRv value this code asserts it's successful
    and prints the error if it's not.
    """
    if not api_rv.success:
        print(api_rv)
        assert api_rv.success
    if quiet:
        print(api_rv)


def run_a_job(
    token: str, *, project: str, name: str, specification: Dict[str, Any]
) -> str:
    """Runs a Job (as an Instance) using the provided 'spec'.
    If successful the Instance ID is returned.
    """
    # Start Job A - in return we're given an Instance (and a Task)
    # -----------
    job_dm_rv: DmApiRv = DmApi.start_job_instance(
        token, project_id=project, name=name, specification=specification
    )
    handle_dmapirv(job_dm_rv)
    job_instance_id: str = job_dm_rv.msg["instance_id"]

    # Wait for Job A (not forever)
    # --------------
    done: bool = False
    job_start_s: float = time.time()
    job_success: bool = False
    while not done:
        job_dm_rv = DmApi.get_instance(token, instance_id=job_instance_id)
        handle_dmapirv(job_dm_rv)
        # Wait until we see a stopped property
        # and a phase that's not RUNNING!
        if "stopped" in job_dm_rv.msg and job_dm_rv.msg["phase"] != "RUNNING":
            # Job's finished
            done = True
            # Successful?
            if job_dm_rv.msg["phase"] == "COMPLETED":
                job_success = True
        elif not done:
            elapsed_s: float = time.time() - job_start_s
            if elapsed_s > _MAX_JOB_WAIT_S:
                done = True
            else:
                time.sleep(_PER_QUERY_SLEEP_S)
    assert job_success

    return job_instance_id


def run(
    *,
    project: str,
    jobs: List[Dict[str, Any]],
    environment: Optional[str] = None,
    token: Optional[str] = None,
    dm_api_url: Optional[str] = None,
    delete: bool = True,
) -> None:
    """Run Jobs,in sequence."""

    # The user's either provided a name of an Environment,
    # or a Token (and DM API URL)...
    api_token: Optional[str] = None
    if environment:
        # Load the client Environment.
        # This gives us many things, like the DM API URL
        _ = Environment.load()
        env: Environment = Environment(environment)
        DmApi.set_api_url(env.dm_api)

        # Now get a DM API access token, using the environment material
        api_token = Auth.get_access_token(
            keycloak_url=env.keycloak_url,
            keycloak_realm=env.keycloak_realm,
            keycloak_client_id=env.keycloak_dm_client_id,
            username=env.admin_user,
            password=env.admin_password,
        )
    else:
        # Given a raw token (and DM API)
        api_token = token
        DmApi.set_api_url(dm_api_url)
    assert api_token

    # A lit of Job instances we'll create.
    # Used to delete them when all is  done.
    job_instances: List[str] = []

    # Start the Jobs - in return we're given an instance ID
    # --------------
    for job in jobs:
        job_name: Any = job["name"]
        print(f'Running Job instance "{job_name}"...')
        job_instance_id: str = run_a_job(
            api_token,
            project=project,
            name=job_name,
            specification=job["specification"],
        )
        print(f' Completed Job instance "{job_instance_id}"')
        job_instances.append(job_instance_id)

    # Housekeeping
    # ------------
    # Now, let's be 'tidy' and delete the Job instances?
    if delete:
        print("Deleting Job instances...")
        for job_instance in job_instances:
            print(f' Deleting Job instance "{job_instance_id}"...')
            dm_rv: DmApiRv = DmApi.delete_instance(api_token, instance_id=job_instance)
            handle_dmapirv(dm_rv)

    print("Done [SUCCESS]")


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="job_chain",
        description="Demonstrates the chained execution of two DM Jobs",
    )
    parser.add_argument(
        "project", type=str, help="The Project UUID where Jobs are to be run"
    )
    parser.add_argument(
        "job_file",
        type=str,
        help="A YAML file with a list of job specs (and their names)",
    )
    parser.add_argument(
        "-e", "--environment", type=str, nargs="?", help="The environment name"
    )
    parser.add_argument(
        "-t", "--token", type=str, nargs="?", help="The environment name"
    )
    parser.add_argument(
        "-d",
        "--dm-api-url",
        type=str,
        nargs="?",
        help="The DM API. Required if you use a token",
    )
    args: argparse.Namespace = parser.parse_args()

    job_file: str = args.job_file
    if not Path(job_file).is_file():
        parser.error(f"File '{job_file}' does not exist")

    if not args.token and not args.environment:
        parser.error("Must provide a token or an environment name")
    if args.token and args.environment:
        parser.error("Cannot provide a token and an environment name")
    if args.token and not args.dm_api_url:
        parser.error("Cannot provide a token without a DM API URL")

    job_file_content: str = Path(job_file).read_text(encoding="utf8")
    job_file_jobs: List[Dict[str, Any]] = yaml.load(
        job_file_content, Loader=yaml.FullLoader
    )

    run(
        project=args.project,
        jobs=job_file_jobs,
        environment=args.environment,
        token=args.token,
        dm_api_url=args.dm_api_url,
    )
