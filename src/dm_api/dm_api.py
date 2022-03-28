"""Python utilities to simplify calls to some parts of the Data Manager API.

For API methods where a user can expect material from a successful call
the original response payload can be found in the DmApiRv 'msg' property
as a Python dictionary.

The URL to the DM API URL is picked up from the environment variable
'SQUONK_API_URL'. If this isn't set the user can set it programmatically
using the 'DmApi.set_api_url()' method.
"""
from collections import namedtuple
import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

from wrapt import synchronized
import requests

# The return value from our public methods.
# 'success' (a boolean) is True if the call was successful, False otherwise.
# The 'msg' (an optional dictionary) will provide a potentially useful
# error message or API-specific response content on success.
DmApiRv: namedtuple = namedtuple('DmApiRv', 'success msg')

# The Job instance Application ID - a 'well known' identity.
_DM_JOB_APPLICATION_ID: str = 'datamanagerjobs.squonk.it'
# The API URL environment variable
_API_URL_ENV_NAME: str = 'SQUONK_API_URL'

_LOGGER: logging.Logger = logging.getLogger(__name__)


class DmApi:
    """Simplified API access methods.
    """

    # The default DM API is extracted from the environment,
    # otherwise it can be set using 'set_api_url()'
    _dm_api_url: str = os.environ.get(_API_URL_ENV_NAME, '')
    # Do we expect the DM API to be secure?
    # This can be disabled using 'set_api_url()'
    _verify_ssl_cert: bool = True

    @classmethod
    def _request(cls,
                 method: str,
                 endpoint: str,
                 access_token: str,
                 headers: Optional[Dict[str, Any]] = None,
                 data: Optional[Dict[str, Any]] = None,
                 files: Optional[Dict[str, Any]] = None,
                 params: Optional[Dict[str, Any]] = None,
                 timeout: int = 4)\
            -> Optional[requests.Response]:
        """Sends a request to the DM API endpoint.
        """
        assert method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
        assert endpoint
        assert access_token

        url: str = DmApi._dm_api_url + endpoint

        # Adds the access token to the headers,
        # or create a headers block
        if headers:
            use_headers = headers.copy()
            use_headers['Authorization'] = 'Bearer ' + access_token
        else:
            use_headers = {'Authorization': 'Bearer ' + access_token}

        resp: Optional[requests.Response] = None
        try:
            # Send the request (displaying the request/response)
            # and returning the response, whatever it is.
            resp = requests.request(method.upper(), url,
                                    headers=use_headers,
                                    params=params,
                                    data=data,
                                    files=files,
                                    timeout=timeout,
                                    verify=DmApi._verify_ssl_cert)
        except:
            _LOGGER.exception('Request failed')

        return resp

    @classmethod
    def _get_latest_job_operator_version(cls,
                                         access_token: str,
                                         timeout_s: int = 4)\
            -> Optional[str]:
        """Gets Job application data frm the DM API.
        We'll get and return the latest version found so that we can launch
        Jobs. If the Job application info is not available it indicates
        the server has no Job Operator installed.
        """
        assert access_token

        resp = DmApi._request('GET',
                              f'/application/{_DM_JOB_APPLICATION_ID}',
                              access_token=access_token,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            _LOGGER.warning('Failed getting Job application info [%s]', resp)
            return None

        # If there are versions, return the first in the list
        if 'versions' in resp.json() and len(resp.json()['versions']):
            return resp.json()['versions'][0]

        _LOGGER.debug('No versions returned for Job application info'
                      ' - no operator?')
        return ''

    @classmethod
    def _put_unmanaged_project_file(cls,
                                    access_token: str,
                                    project_id: str,
                                    project_file: str,
                                    project_path: str = '/',
                                    timeout_s: int = 120)\
            -> bool:
        """Puts an individual file into a DM project.
        """
        data: Dict[str, Any] = {}
        if project_path:
            data['path'] = project_path
        files = {'file': open(project_file, 'rb')}  # pylint: disable=consider-using-with

        _LOGGER.debug('Putting file %s -> %s (project_id=%s)',
                      project_file, project_path, project_id)

        resp = DmApi._request('PUT', f'/project/{project_id}/file',
                              access_token=access_token,
                              data=data,
                              files=files,
                              timeout=timeout_s)

        if not resp or resp.status_code not in [201]:
            _LOGGER.warning('Failed putting file %s -> %s (resp=%s project_id=%s)',
                            project_file, project_path, resp, project_id)
            return False

        # OK if we get here
        return True

    @classmethod
    @synchronized
    def set_api_url(cls, url: str, verify_ssl_cert: bool = True) -> None:
        """Replaces the class API URL value.
        Typically https://example.com/data-manager-api
        """
        assert url
        DmApi._dm_api_url = url
        DmApi._verify_ssl_cert = verify_ssl_cert

        # Disable the 'InsecureRequestWarning'?
        if not verify_ssl_cert:
            disable_warnings(InsecureRequestWarning)

    @classmethod
    @synchronized
    def get_api_url(cls) -> Tuple[str, bool]:
        """Return the URL and whether validating the SSL layer.
        """
        return DmApi._dm_api_url, DmApi._verify_ssl_cert

    @classmethod
    @synchronized
    def get_access_token(cls,
                         keycloak_url: str,
                         keycloak_realm: str,
                         keycloak_client_id: str,
                         username: str,
                         password: str,
                         timeout_s: int = 4)\
            -> Optional[str]:
        """Gets a DM API access token from the given Keycloak server
        and clint ID. The keycloak URL is typically 'https://example.com/auth'
        """
        assert keycloak_url
        assert keycloak_realm
        assert keycloak_client_id
        assert username
        assert password

        data: str = f'client_id={keycloak_client_id}'\
            f'&grant_type=password'\
            f'&username={username}'\
            f'&password={password}'
        headers: Dict[str, Any] =\
            {'Content-Type': 'application/x-www-form-urlencoded'}
        url = f'{keycloak_url}/realms/{keycloak_realm}' \
              f'/protocol/openid-connect/token'

        try:
            resp: requests.Response = requests.post(url,
                                                    headers=headers,
                                                    data=data,
                                                    timeout=timeout_s)
        except:
            return None

        if resp.status_code not in [200]:
            _LOGGER.error('Failed to get token text=%s', resp.text)
            assert False

        assert 'access_token' in resp.json()
        return resp.json()['access_token']

    @classmethod
    @synchronized
    def ping(cls, access_token: str, timeout_s: int = 4)\
            -> DmApiRv:
        """Calls the DM API to ensure the server is responding.
        Here we do something relatively simple, and the best endpoint
        to call (in DM 0.7) is '/account-server/namespace'.
        """
        assert access_token

        if not DmApi._dm_api_url:
            return DmApiRv(success=False,
                           msg={'msg': 'No API URL defined'})

        resp = DmApi._request('GET', '/account-server/namespace',
                              access_token=access_token, timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed ping (resp={resp})'})

        # OK if we get here
        return DmApiRv(success=True, msg=None)

    @classmethod
    @synchronized
    def get_version(cls, access_token: str, timeout_s: int = 4)\
            -> DmApiRv:
        """Calls the DM API to get the underlying service version.
        """
        assert access_token

        if not DmApi._dm_api_url:
            return DmApiRv(success=False,
                           msg={'msg': 'No API URL defined'})

        resp = DmApi._request('GET', '/version',
                              access_token=access_token, timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed getting version (resp={resp})'})

        # OK if we get here
        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def create_project(cls,
                       access_token: str,
                       project_name: str,
                       as_tier_product_id: str = 'product-11111111-1111-1111-1111-111111111111',
                       as_organisation_id: str = 'org-11111111-1111-1111-1111-111111111111',
                       as_unit_id: str = 'unit-11111111-1111-1111-1111-111111111111',
                       timeout_s: int = 4)\
            -> DmApiRv:
        """Creates a project using an organisation, unit and product.
        """
        assert access_token
        assert project_name
        assert as_tier_product_id
        assert as_organisation_id
        assert as_unit_id

        if not DmApi._dm_api_url:
            return DmApiRv(success=False,
                           msg={'msg': 'No API URL defined'})

        data: Dict[str, Any] = {'unit_id': as_unit_id,
                                'organisation_id': as_organisation_id,
                                'tier_product_id': as_tier_product_id,
                                'name': project_name}
        resp = DmApi._request('POST', '/project',
                              access_token=access_token,
                              data=data,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [201]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed creating project (resp={resp})'})

        # OK if we get here
        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def delete_project(cls,
                       access_token: str,
                       project_id: str,
                       timeout_s: int = 4) \
            -> DmApiRv:
        """Deletes a project.
        """
        assert access_token
        assert project_id

        if not DmApi._dm_api_url:
            return DmApiRv(success=False,
                           msg={'msg': 'No API URL defined'})

        resp = DmApi._request('DELETE', f'/project/{project_id}',
                              access_token=access_token,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed deleting project (resp={resp})'})

        # OK if we get here
        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def upload_unmanaged_project_files(cls,
                                       access_token: str,
                                       project_id: str,
                                       project_files: Union[str, List[str]],
                                       project_path: str = '/',
                                       force: bool = False,
                                       timeout_per_file_s: int = 120)\
            -> DmApiRv:
        """Puts a file, or list of files, into a DM Project
        using an optional path. The files can include relative or absolute
        paths but are written to the same path in the project.

        Files are not written to the project if a file of the same name exists.
        'force' can be used to over-write files but files on the server that
        are immutable cannot be over-written and will result in an error.
        """

        assert access_token
        assert project_id
        assert project_files
        assert isinstance(project_files, (list, str))
        assert project_path\
               and isinstance(project_path, str)\
               and project_path.startswith('/')

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        # If we're not forcing the files collect the names
        # of every file on the path - we use this to skip files that
        # are already present.
        existing_path_files: List[str] = []
        if force:
            _LOGGER.warning('Putting files (force=true project_id=%s)',
                            project_id)
        else:
            _LOGGER.debug('Getting existing files on path %s (project_id=%s)',
                          project_path, project_id)

            # What files already exist on the path?
            # To save time we avoid putting files that appear to exist.
            params: Dict[str, Any] = {'project_id': project_id}
            if project_path:
                params['path'] = project_path

            resp = DmApi._request('GET', '/file', access_token=access_token,
                                  params=params)
            if not resp or resp.status_code not in [200]:
                return DmApiRv(success=False,
                               msg={'msg': f'Failed getting existing files'
                                    f' (resp={resp} project_id={project_id})'})

            for item in resp.json()['files']:
                existing_path_files.append(item['file_name'])

            _LOGGER.debug('Got %d files (project_id=%s)',
                          len(existing_path_files), project_id)

        # Now post every file that's not in the existing list
        if isinstance(project_files, str):
            src_files = [project_files]
        else:
            src_files = project_files
        for src_file in src_files:
            # Source file has to exist
            # whether we end up sending it or not.
            if not os.path.isfile(src_file):
                return DmApiRv(success=False,
                               msg={'msg': f'No such file ({src_file})'})
            if os.path.basename(src_file) in existing_path_files:
                _LOGGER.debug('Skipping %s - already present (project_id=%s)',
                              src_file, project_id)
            else:
                if not DmApi._put_unmanaged_project_file(access_token,
                                                         project_id,
                                                         src_file,
                                                         project_path,
                                                         timeout_per_file_s):
                    return DmApiRv(success=False,
                                   msg={'msg': 'Failed sending files'})

        # OK if we get here
        return DmApiRv(success=True, msg={})

    @classmethod
    @synchronized
    def delete_unmanaged_project_files(cls,
                                       access_token: str,
                                       project_id: str,
                                       project_files: Union[str, List[str]],
                                       project_path: str = '/',
                                       timeout_s: int = 4)\
            -> DmApiRv:
        """Deletes an unmanaged project file on a path.
        """
        assert access_token
        assert project_id
        assert isinstance(project_files, (list, str))
        assert project_path\
               and isinstance(project_path, str)\
               and project_path.startswith('/')

        if isinstance(project_files, str):
            files_to_delete = [project_files]
        else:
            files_to_delete = project_files

        for file_to_delete in files_to_delete:
            params: Dict[str, Any] = {'project_id': project_id,
                                      'path': project_path,
                                      'file': file_to_delete}
            resp = DmApi._request('DELETE', '/file',
                                  access_token=access_token,
                                  params=params,
                                  timeout=timeout_s)
            if not resp or resp.status_code not in [204]:
                return DmApiRv(success=False,
                               msg={'msg': f'Failed to delete project file [{resp}]'})

        # OK if we get here
        return DmApiRv(success=True, msg={})

    @classmethod
    @synchronized
    def list_project_files(cls,
                           access_token: str,
                           project_id: str,
                           project_path: str = '/',
                           include_hidden: bool = False,
                           timeout_s: int = 8)\
            -> DmApiRv:
        """Gets the list of project files on a path.
        """
        assert access_token
        assert project_id
        assert project_path\
               and isinstance(project_path, str)\
               and project_path.startswith('/')

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        params: Dict[str, Any] = {'project_id': project_id,
                                  'path': project_path,
                                  'include_hidden': include_hidden}
        resp = DmApi._request('GET', '/file',
                              access_token=access_token,
                              params=params,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed to get instance [{resp}]'})

        # OK if we get here
        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def download_unmanaged_project_file(cls,
                                        access_token: str,
                                        project_id: str,
                                        project_file: str,
                                        local_file: str,
                                        project_path: str = '/',
                                        timeout_s: int = 8)\
            -> DmApiRv:
        """Get a single unmanaged file from a project path, saving it to
        the filename defined in local_file.
        """
        assert access_token
        assert project_id
        assert project_file
        assert local_file
        assert project_path\
               and isinstance(project_path, str)\
               and project_path.startswith('/')

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        params: Dict[str, Any] = {'path': project_path,
                                  'file': project_file}
        resp = DmApi._request('GET', f'/project/{project_id}/file',
                              access_token=access_token,
                              params=params,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed to get file [{resp}]'})

        # OK if we get here
        with open(local_file, 'wb') as file_handle:
            file_handle.write(resp.content)
        return DmApiRv(success=True, msg={})

    @classmethod
    @synchronized
    def start_job_instance(cls,
                           access_token: str,
                           project_id: str,
                           name: str,
                           callback_url: Optional[str] = None,
                           callback_context: Optional[str] = None,
                           specification: Optional[Dict[str, Any]] = None,
                           debug: Optional[str] = None,
                           timeout_s: int = 4)\
            -> DmApiRv:
        """Instantiates a Job (based on the latest Job application ID
        and version known to the API).
        """

        assert access_token
        assert project_id
        assert name
        assert isinstance(specification, (type(None), dict))

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        # Get the latest Job operator version.
        # If there isn't one the DM can't run Jobs.
        job_application_version: Optional[str] =\
            DmApi._get_latest_job_operator_version(access_token)
        if job_application_version is None:
            # Failed calling the server.
            # Incorrect URL, bad token or server out of action?
            return DmApiRv(success=False,
                           msg={'msg': 'Failed getting Job operator version'})
        if not job_application_version:
            return DmApiRv(success=False,
                           msg={'msg': 'No Job operator installed'})

        _LOGGER.debug('Starting Job instance (project_id=%s)', project_id)

        data: Dict[str, Any] =\
            {'application_id': _DM_JOB_APPLICATION_ID,
             'application_version': job_application_version,
             'as_name': name,
             'project_id': project_id,
             'specification': json.dumps(specification)}
        if debug:
            data['debug'] = debug
        if callback_url:
            _LOGGER.debug('Job callback_url=%s (project_id=%s)',
                          callback_url, project_id)
            data['callback_url'] = callback_url
            if callback_context:
                _LOGGER.debug('Job callback_context=%s (project_id=%s)',
                              callback_context, project_id)
                data['callback_context'] = callback_context

        resp = DmApi._request('POST', '/instance', access_token=access_token,
                              data=data, timeout=timeout_s)
        if not resp or resp.status_code not in [201]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed to start instance [{resp}]'})

        _LOGGER.debug('Started Job instance (project_id=%s)', project_id)
        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def get_available_projects(cls, access_token: str, timeout_s: int = 4)\
            -> DmApiRv:
        """Gets information about all projects available to you.
        """
        assert access_token

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        resp = DmApi._request('GET', '/project',
                              access_token=access_token,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed to get projects [{resp}]'})

        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def get_project(cls,
                    access_token: str,
                    project_id: str,
                    timeout_s: int = 4)\
            -> DmApiRv:
        """Gets detailed information about a specific project.
        """
        assert access_token
        assert project_id

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        resp = DmApi._request('GET', f'/project/{project_id}',
                              access_token=access_token,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed to get project [{resp}]'})

        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def get_instance(cls,
                     access_token: str,
                     instance_id: str,
                     timeout_s: int = 4)\
            -> DmApiRv:
        """Gets information about an Application/Job instance.
        """
        assert access_token
        assert instance_id

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        resp = DmApi._request('GET', f'/instance/{instance_id}',
                              access_token=access_token,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed to get instance [{resp}]'})

        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def get_project_instances(cls,
                              access_token: str,
                              project_id: str,
                              timeout_s: int = 4)\
            -> DmApiRv:
        """Gets information about all instances available to you.
        """
        assert access_token
        assert project_id

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        params: Dict[str, Any] = {'project_id': project_id}
        resp = DmApi._request('GET', '/instance',
                              access_token=access_token,
                              params=params,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed to get project instances [{resp}]'})

        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def delete_instance(cls,
                        access_token: str,
                        instance_id: str,
                        timeout_s: int = 4)\
            -> DmApiRv:
        """Deletes an Application/Job instance.
        """
        assert access_token
        assert instance_id

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        resp = DmApi._request('DELETE', f'/instance/{instance_id}',
                              access_token=access_token,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed to delete instance [{resp}]'})

        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def get_task(cls,
                 access_token: str,
                 task_id: str,
                 event_prior_ordinal: int = 0,
                 event_limit: int = 0,
                 timeout_s: int = 4)\
            -> DmApiRv:
        """Gets information about a specific Task
        """
        assert access_token
        assert task_id
        assert event_prior_ordinal >= 0
        assert event_limit >= 0

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        params: Dict[str, Any] = {}
        if event_prior_ordinal:
            params['event_prior_ordinal'] = event_prior_ordinal
        if event_limit:
            params['event_limit'] = event_limit
        resp = DmApi._request('GET', f'/task/{task_id}',
                              access_token=access_token,
                              params=params,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed to get task [{resp}]'})

        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def get_available_jobs(cls, access_token: str, timeout_s: int = 4)\
            -> DmApiRv:
        """Gets a summary list of avaailble Jobs.
        """
        assert access_token

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        resp = DmApi._request('GET', '/job',
                              access_token=access_token,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed to get available jobs [{resp}]'})

        return DmApiRv(success=True, msg=resp.json())

    @classmethod
    @synchronized
    def get_job(cls, access_token: str, job_id: int, timeout_s: int = 4)\
            -> DmApiRv:
        """Gets detailed information about a specific Job.
        """
        assert access_token
        assert job_id > 0

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg={'msg': 'No API URL defined'})

        resp = DmApi._request('GET', f'/job/{job_id}',
                              access_token=access_token,
                              timeout=timeout_s)
        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False,
                           msg={'msg': f'Failed to get job detail [{resp}]'})

        return DmApiRv(success=True, msg=resp.json())
