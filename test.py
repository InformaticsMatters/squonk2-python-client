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

    # Configure.
    # Depending on keycloak configuration
    # you may only have 5 minutes before the token expires.
    DmApi.set_api_url(API_URL)
    url, verify = DmApi.get_api_url()
    assert url == API_URL
    first_token = DmApi.get_access_token(
        KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID,
        KEYCLOAK_USER, KEYCLOAK_USER_PASSWORD)
    assert first_token
    print(f'DM-API connected ({API_URL})')

    # Get another token using the existing token.
    # Just tests that prior tokens are given back.
    token = DmApi.get_access_token(
        KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID,
        KEYCLOAK_USER, KEYCLOAK_USER_PASSWORD,
        prior_token=first_token)
    assert token == first_token

    # Basic ping/version
    rv: DmApiRv = DmApi.ping(token)
    assert rv.success
    rv = DmApi.get_version(token)
    assert rv.success
    print(f"DM-API version={rv.msg['version']}")

    # Get existing projects
    rv_projects = DmApi.get_available_projects(token)
    assert rv_projects.success

    # If given a project ID find it,
    # otherwise create one using the '1111' codes,
    # assuming admin user (because we have no Product, Unit, Organisation atm)
    project_id = ''
    if args.project_id:
        found = False
        for project in rv_projects.msg['projects']:
            if project['project_id'] == args.project_id:
                print(f"Found project (product_id={project['product_id']} size={project['size']})")
                found = True
                break
        assert found
        project_id = args.project_id
    else:
        # Delete project if it exists
        new_project_name = 'DmApi Project'
        project_exists = False
        for project in rv_projects.msg['projects']:
            if project['name'] == new_project_name:
                print(f"Using existing project ({project['project_id']})")
                project_id = project['project_id']
                project_exists = True
                break
        if not project_exists:
            print(f'Creating new Project ("{new_project_name}")...')
            rv = DmApi.create_project(token, 'DmApi-generated Project')
            assert rv.success
            project_id = rv.msg['project_id']
            print(f'Created project_id={project_id}')
    assert project_id

    # get a list of project files on the root
    print("Listing project files")
    rv = DmApi.list_project_files(token, project_id, '/')
    assert rv.success
    num_project_files = 0
    if rv.msg['files']:
        for project_file in rv.msg['files']:
            num_project_files += 1
            print(f"+ {project_file['file_name']}")
    else:
        print('+ (none)')
    plural = 'file' if num_project_files == 1 else 'files'
    print(f"Project has {num_project_files} {plural}")

    print('Uploading, downloading and deleting unmanaged file on a path...')
    # Put a simple file into the project, get it back and delete it
    local_file = 'LICENSE'
    project_path = '/license'
    rv = DmApi.upload_unmanaged_project_files(token, project_id,
                                              local_file,
                                              project_path=project_path)
    assert rv.success
    rv = DmApi.download_unmanaged_project_file(token, project_id,
                                               local_file,
                                               project_path=project_path,
                                               local_file=local_file)
    assert rv.success
    rv = DmApi.delete_unmanaged_project_files(token, project_id,
                                              local_file,
                                              project_path=project_path)
    assert rv.success

    # Run a test job
    print('Starting Job...')
    job_name = 'DmApi Job'
    spec = {'collection': 'im-test', 'job': 'nop', 'version': '1.0.0'}
    rv = DmApi.start_job_instance(token, project_id, job_name, specification=spec)
    assert rv.success
    job_task_id = rv.msg['task_id']
    job_instance_id = rv.msg['instance_id']
    print(f'Started (task_id={job_task_id} instance_id={job_instance_id})')

    # Wait for the Job (but not forever),
    # print the events and then delete it
    print('Waiting for job completion...')
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
    print('Deleting Job...')
    rv = DmApi.delete_instance(token, job_instance_id)
    assert rv.success
    print('Deleted')

    # Finally, if we created a project, delete it.
    if not args.project_id:
        print('Deleting project I created...')
        print(f'Deleting project_id={project_id}...')
        rv = DmApi.delete_project(token, project_id)
        assert rv.success
        print('Deleted')

    print('Done')


if __name__ == '__main__':

    main()
