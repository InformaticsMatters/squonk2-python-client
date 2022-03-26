#!/usr/bin/env python
"""A simple developer-centric test script.
"""
import argparse
import os
import time

from dm_api.dm_api import DmApi, DmApiRv

API_URL: str = os.environ['SQUONK_API_URL']
KEYCLOCK_URL: str = os.environ['SQUONK_API_KEYCLOAK_URL']
KEYCLOCK_REALM: str = os.environ['SQUONK_API_KEYCLOAK_REALM']
KEYCLOCK_CLIENT_ID: str = os.environ['SQUONK_API_KEYCLOAK_CLIENT_ID']
KEYCLOCK_USER: str = os.environ['SQUONK_API_KEYCLOAK_USER']
KEYCLOCK_USER_PASSWORD: str = os.environ['SQUONK_API_KEYCLOAK_USER_PASSWORD']


def main():
    arg_parser: argparse.ArgumentParser = argparse\
        .ArgumentParser(description='Data Manager API Tester',
                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    arg_parser.add_argument('-p', '--project-id',
                            help='A pre-existing DM-API Project',
                            required=True,
                            type=str)
    args: argparse.Namespace = arg_parser.parse_args()

    project_id: str = args.project_id

    # Configure
    DmApi.set_api_url(API_URL)
    url, verify = DmApi.get_api_url()
    assert url == API_URL
    token = DmApi.get_access_token(
        KEYCLOCK_URL, KEYCLOCK_REALM, KEYCLOCK_CLIENT_ID,
        KEYCLOCK_USER, KEYCLOCK_USER_PASSWORD)
    assert token
    print(f"DM-API connected")

    # Basic ping/version
    rv: DmApiRv = DmApi.ping(token)
    assert rv.success
    rv = DmApi.get_version(token)
    assert rv.success
    print(f"DM-API version={rv.msg['version']}")

    # Put a simple file into the project and run a test Job
    rv = DmApi.upload_unmanaged_project_files(token, project_id, 'LICENSE', force=True)
    assert rv.success
    spec = {'collection': 'im-test', 'job': 'nop', 'version': '1.0.0'}
    rv = DmApi.start_job_instance(token, project_id, 'Test Job', specification=spec)
    assert rv.success
    job_task_id = rv.msg['task_id']
    job_instance_id = rv.msg['instance_id']
    print(f'Running Job (task_id={job_task_id} instance_id={job_instance_id})')

    # Wait for Job and then delete it
    done = False
    while not done:
        rv = DmApi.get_instance(token, job_instance_id)
        assert rv.success
        job_phase = rv.msg['phase']
        if job_phase == 'COMPLETED':
            print(f'Dome ({job_phase})')
            done = True
        else:
            print(f'Waiting ({job_phase})...')
            time.sleep(2)
    rv = DmApi.delete_instance(token, job_instance_id)
    assert rv.success


if __name__ == '__main__':

    main()
