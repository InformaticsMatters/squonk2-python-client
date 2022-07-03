#!/usr/bin/env python
"""A simple developer-centric test script.
"""
import argparse
import os
import sys
import time
from typing import NoReturn, Optional

from dm_api.dm_api import DmApi, DmApiRv, TEST_PRODUCT_ID

# Get configuration from the environment.
# All the expected variables must be defined...
API_URL: str = os.environ['SQUONK_API_URL']
KEYCLOAK_URL: str = os.environ['SQUONK_API_KEYCLOAK_URL']
KEYCLOAK_REALM: str = os.environ['SQUONK_API_KEYCLOAK_REALM']
KEYCLOAK_CLIENT_ID: str = os.environ['SQUONK_API_KEYCLOAK_CLIENT_ID']
KEYCLOAK_USER: str = os.environ['SQUONK_API_KEYCLOAK_USER']
KEYCLOAK_USER_PASSWORD: str = os.environ['SQUONK_API_KEYCLOAK_USER_PASSWORD']
# Optional
API_URL_VALIDATION: bool = os.environ.get('SQUONK_API_URL_VALIDATION', 'yes').lower() == 'yes'


def fail(msg: str, rv: Optional[DmApiRv] = None) -> NoReturn:
    """Issues a failure message then sies a sys.exit(1).
    """
    err_msg = f'FAILED {msg}'
    if rv:
        assert not rv.success
        err_msg += f' (rv.msg={rv.msg})'
    print(err_msg)
    sys.exit(1)


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
    DmApi.set_api_url(API_URL, verify_ssl_cert=API_URL_VALIDATION)
    url, verify = DmApi.get_api_url()
    assert url == API_URL
    first_token = DmApi.get_access_token(
        KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID,
        KEYCLOAK_USER, KEYCLOAK_USER_PASSWORD)
    if not first_token:
        fail(f'Failed to get token from "{KEYCLOAK_URL}"')
        sys.exit(1)
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
    if not rv.success:
        fail('ping()', rv)
    rv = DmApi.get_version(token)
    if not rv.success:
        fail(f'get_version()', rv)
    print(f"DM-API version={rv.msg['version']}")

    # Get existing projects
    rv_projects = DmApi.get_available_projects(token)
    if not rv_projects.success:
        fail('get_available_projects()', rv)

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
        if not found:
            fail(f'Project does not exist ({args.project_id})')
        project_id = args.project_id
    else:
        # Crete a new project, using the one we're about to
        # create if it already exists on the server.
        new_project_name = 'DmApi Test Project'
        project_exists = False
        for project in rv_projects.msg['projects']:
            if project['name'] == new_project_name:
                print(f"Using existing project ({project['project_id']})")
                project_id = project['project_id']
                project_exists = True
                break
        if project_exists:
            print(f'Test project ("{new_project_name}") already exists')
        else:
            # By not providing a project ID
            # we create one using a build-in Account Server "Product"
            # specifically designed for testing.
            print(f'Creating new Project ("{new_project_name}", "{TEST_PRODUCT_ID})...')
            rv = DmApi.create_project(token, new_project_name, TEST_PRODUCT_ID)
            if not rv.success:
                fail('create_project()', rv)
            project_id = rv.msg['project_id']
            print(f'Created project_id={project_id}')
    assert project_id

    # Get a list of project files on the root
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
    rv = DmApi.put_unmanaged_project_files(token, project_id,
                                           local_file,
                                           project_path=project_path)
    if not rv.success:
        fail(f'put_unmanaged_project_files({project_id})', rv)
    rv = DmApi.get_unmanaged_project_file(token, project_id,
                                          local_file,
                                          project_path=project_path,
                                          local_file=local_file)
    if not rv.success:
        fail(f'get_unmanaged_project_file({project_id})', rv)
    rv = DmApi.delete_unmanaged_project_files(token, project_id,
                                              local_file,
                                              project_path=project_path)
    if not rv.success:
        fail(f'delete_unmanaged_project_files({project_id})', rv)

    # Run a test job
    print('Starting Job...')
    job_collection = 'im-test'
    job_name = 'nop'
    job_version = '1.0.0'
    rv = DmApi.get_job_by_name(token, job_collection, job_name, job_version)
    if not rv.success:
        fail('get_job_by_name()', rv)
    spec = {'collection': job_collection, 'job': job_name, 'version': job_version}
    rv = DmApi.start_job_instance(token, project_id, 'DmApi Test Job', specification=spec)
    if not rv.success:
        fail('start_job_instance()', rv)
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
    if not rv.success:
        fail(f'get_task({job_task_id})', rv)
    for event in rv.msg['events']:
        print(f"# {event['time']} {event['level']} {event['message']}")
    print('Deleting Job...')
    rv = DmApi.delete_instance(token, job_instance_id)
    if not rv.success:
        fail(f'delete_instance({job_instance_id})', rv)
    print('Deleted')

    # Finally, if we created a project, delete it.
    if not args.project_id:
        print('Deleting project I created...')
        print(f'Deleting project_id={project_id}...')
        rv = DmApi.delete_project(token, project_id)
        if not rv.success:
            fail(f'delete_project({project_id})', rv)
        print('Deleted')

    print('Done')


if __name__ == '__main__':

    main()
