#!/usr/bin/env python
"""A simple developer-centric test script.
"""
import argparse
import os
import time

from dm_api.dm_api import DmApi, DmApiRv

# Get configuration from the environment.
# All the expected variables must be defined...
API_URL: str = os.environ['SQUONK_API_URL']
KEYCLOAK_URL: str = os.environ['SQUONK_API_KEYCLOAK_URL']
KEYCLOAK_REALM: str = os.environ['SQUONK_API_KEYCLOAK_REALM']
KEYCLOAK_CLIENT_ID: str = os.environ['SQUONK_API_KEYCLOAK_CLIENT_ID']
KEYCLOAK_USER: str = os.environ['SQUONK_API_KEYCLOAK_USER']
KEYCLOAK_USER_PASSWORD: str = os.environ['SQUONK_API_KEYCLOAK_USER_PASSWORD']


def main():
    # Prepare arg-parser and parse the command-line...
    arg_parser: argparse.ArgumentParser = argparse\
        .ArgumentParser(description='Data Manager API Tester',
                        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument('-p', '--project-id',
                            help='A pre-existing DM-API Project',
                            type=str)
    args: argparse.Namespace = arg_parser.parse_args()

    # Configure
    DmApi.set_api_url(API_URL)
    url, verify = DmApi.get_api_url()
    assert url == API_URL
    token = DmApi.get_access_token(
        KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID,
        KEYCLOAK_USER, KEYCLOAK_USER_PASSWORD)
    assert token
    print(f'DM-API connected ({API_URL})')

    # Basic ping/version
    rv: DmApiRv = DmApi.ping(token)
    assert rv.success
    rv = DmApi.get_version(token)
    assert rv.success
    print(f"DM-API version={rv.msg['version']}")

    # If given a project ID find it,
    # otherwise create one (assuming admin user)
    if args.project_id:
        rv = DmApi.get_available_projects(token)
        project_id = args.project_id
        assert rv.success
        found = False
        for project in rv.msg['projects']:
            if project['project_id'] == project_id:
                print(f"Found project (product_id={project['product_id']} size={project['size']})")
                found = True
                break
        assert found
    else:
        print('Creating new Project...')
        rv = DmApi.create_project(token, 'DmApi-generated Project')
        assert rv.success
        project_id = rv.msh['project_id']
        print(f'Created project_id={project_id}')
    assert project_id

    # get a list of project files on the root
    print("Listing project files")
    rv = DmApi.list_project_files(token, project_id, '/')
    assert rv.success
    num_project_files = 0
    for project_file in rv.msg['files']:
        num_project_files += 1
        print(f"+ {project_file['file_name']}")
    plural = 'file' if num_project_files == 1 else 'files'
    print(f"Project has {num_project_files} {plural}")

    # Put a simple file into the project, get it back and delete it
    rv = DmApi.upload_unmanaged_project_files(token, project_id, 'LICENSE', force=True)
    assert rv.success
    rv = DmApi.download_unmanaged_project_file(token, project_id, 'LICENSE', 'LICENSE')
    assert rv.success
    rv = DmApi.delete_unmanaged_project_files(token, project_id, 'LICENSE')
    assert rv.success

    # Run a test job
    spec = {'collection': 'im-test', 'job': 'nop', 'version': '1.0.0'}
    rv = DmApi.start_job_instance(token, project_id, 'Test Job', specification=spec)
    assert rv.success
    job_task_id = rv.msg['task_id']
    job_instance_id = rv.msg['instance_id']
    print(f'Running Job (task_id={job_task_id} instance_id={job_instance_id})')

    # Wait for the Job (but not forever),
    # print the events and then delete it
    max_wait_seconds = 120
    wait_seconds = 0
    done = False
    while not done and wait_seconds < max_wait_seconds:
        rv = DmApi.get_instance(token, job_instance_id)
        assert rv.success
        job_phase = rv.msg['phase']
        if job_phase == 'COMPLETED':
            print(f'Done ({job_phase})')
            done = True
        else:
            print(f'Waiting ({job_phase})...')
            time.sleep(2)
            wait_seconds += 2
    assert done
    print('Job events...')
    rv = DmApi.get_task(token, job_task_id)
    assert rv.success
    for event in rv.msg['events']:
        print(f"# {event['time']} {event['level']} {event['message']}")
    rv = DmApi.delete_instance(token, job_instance_id)
    assert rv.success

    # Finally, if we created a project, delete it.
    if not args.project_id:
        print(f'Deleting project_id={project_id}...')
        rv = DmApi.delete_project(token, project_id)
        assert rv.success

    print('Done!')


if __name__ == '__main__':

    main()
