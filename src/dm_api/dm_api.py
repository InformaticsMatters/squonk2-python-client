"""Python utilities to simplify calls to the parts of the Data Manager API.
"""
from collections import namedtuple
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

from wrapt import synchronized
import requests

# The return value from our public methods.
# 'success' (a boolean) is True if the call was successful, False otherwise.
# The 'msg' (a string used on failure) will provide a potentially useful
# error message.
DmApiRv: namedtuple = namedtuple('DmApiRv', 'success msg')

# The Job instance Application ID - a 'well known' identity.
_DM_JOB_APPLICATION_ID: str = 'datamanagerjobs.squonk.it'

_LOGGER: logging.Logger = logging.getLogger(__name__)


class DmApi:
    """Simplified API access methods.
    """

    # The default DM API is extracted from the environment,
    # otherwise it can be set using 'set_api_url()'
    _dm_api_url: str = os.environ.get('SQUONK_API_URL', '')
    _verify_ssl_cert: bool = True

    @classmethod
    @synchronized
    def set_api_url(cls, url: str, verify_ssl_cert: bool = True) -> None:
        """Replaces the class API URL value.
        """
        assert url
        DmApi._dm_api_url = url
        DmApi._verify_ssl_cert = verify_ssl_cert

        # Disable the 'InsecureRequestWarning'?
        if not verify_ssl_cert:
            disable_warnings(InsecureRequestWarning)

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

        headers: Dict[str, Any] = {'Authorization': 'Bearer ' + access_token}
        url: str = DmApi._dm_api_url + f'/application/{_DM_JOB_APPLICATION_ID}'

        try:
            resp = requests.get(url, headers=headers, timeout=timeout_s,
                                verify=DmApi._verify_ssl_cert)
        except:
            _LOGGER.exception('Exception getting Job application info')
            return None
        if resp.status_code not in [200]:
            _LOGGER.warning('Failed getting Job application info [%d]',
                            resp.status_code)
            return None

        # If there are versions, return the first in the list
        if 'versions' in resp.json() and len(resp.json()['versions']):
            return resp.json()['versions'][0]

        _LOGGER.debug('No versions returned for Job application info'
                      ' - no operator?')
        return None

    @classmethod
    @synchronized
    def ping(cls, access_token: str, timeout_s: int = 4)\
            -> DmApiRv:
        """Calls the DM API to ensure the server is responding.
        Here we do something relatively simple, and the best endpoint
        to call (in DM 0.7) is '/account-server/namespace'.
        """
        assert access_token

        headers: Dict[str, Any] = {'Authorization': 'Bearer ' + access_token}
        url: str = DmApi._dm_api_url + '/account-server/namespace'

        resp: Optional[requests.Response] = None
        try:
            resp = requests.get(url, headers=headers, timeout=timeout_s,
                                verify=DmApi._verify_ssl_cert)
        except:
            _LOGGER.exception('Exception on ping')

        if not resp or resp.status_code not in [200]:
            return DmApiRv(success=False, msg=f'Failed ping (resp={resp})')

        # OK if we get here
        return DmApiRv(success=True, msg=None)

    @classmethod
    def _put_project_file(cls,
                          access_token: str,
                          project_id: str,
                          project_file: str,
                          project_path: str = '/',
                          timeout_s: int = 120)\
            -> bool:
        """Puts an individual file into a DM project.
        """
        headers: Dict[str, Any] = {'Authorization': 'Bearer ' + access_token}

        data: Dict[str, Any] = {}
        if project_path:
            data['path'] = project_path
        url: str = DmApi._dm_api_url + f'/project/{project_id}/file'
        files = {'file': open(project_file, 'rb')}  # pylint: disable=consider-using-with

        _LOGGER.debug('Putting file %s -> %s (project_id=%s)',
                      project_file, project_path, project_id)

        try:
            resp = requests.put(url,
                                headers=headers,
                                data=data,
                                files=files,
                                timeout=timeout_s,
                                verify=DmApi._verify_ssl_cert)
        except:
            _LOGGER.exception('Exception putting file %s -> %s (project_id=%s)',
                              project_file, project_path, project_id)
            return False

        if resp.status_code not in [201]:
            _LOGGER.warning('Failed putting file %s -> %s (project_id=%s) [%d]',
                            project_file, project_path, project_id,
                            resp.status_code)
            return False

        # OK if we get here
        return True

    @classmethod
    @synchronized
    def put_project_files(cls,
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

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg='No API URL defined')

        headers: Dict[str, Any] = {'Authorization': 'Bearer ' + access_token}

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
            url: str = DmApi._dm_api_url + '/file'

            try:
                resp: requests.Response =\
                    requests.get(url,
                                 headers=headers,
                                 params=params,
                                 timeout=4,
                                 verify=DmApi._verify_ssl_cert)
            except:
                msg: str = 'Exception getting files'
                _LOGGER.exception(msg)
                return DmApiRv(success=False, msg=msg)

            if not resp or resp.status_code not in [200]:
                return DmApiRv(success=False,
                               msg=f'Failed getting existing files'
                                   f' (project_id={project_id})')

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
                return DmApiRv(success=False, msg=f'No such file ({src_file})')
            if os.path.basename(src_file) in existing_path_files:
                _LOGGER.debug('Skipping %s - already present (project_id=%s)',
                              src_file, project_id)
            else:
                if not DmApi._put_project_file(access_token,
                                               project_id,
                                               src_file,
                                               project_path,
                                               timeout_per_file_s):
                    return DmApiRv(success=False, msg='Failed sending files')

        # OK if we get here
        return DmApiRv(success=True, msg=None)

    @classmethod
    @synchronized
    def post_job_instance(cls,
                          access_token: str,
                          project_id: str,
                          name: str,
                          callback_url: Optional[str] = None,
                          callback_context: Optional[str] = None,
                          specification: Optional[Dict[str, Any]] = None,
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
            return DmApiRv(success=False, msg='No API URL defined')

        # Get the latest Job operator version.
        # If there isn't one the DM can't run Jobs.
        job_application_version: Optional[str] =\
            DmApi._get_latest_job_operator_version(access_token)
        if not job_application_version:
            return DmApiRv(success=False, msg='No Job operator installed')

        _LOGGER.debug('Starting Job instance (project_id=%s)', project_id)

        headers: Dict[str, Any] = {'Authorization': 'Bearer ' + access_token}

        data: Dict[str, Any] =\
            {'application_id': _DM_JOB_APPLICATION_ID,
             'application_version': job_application_version,
             'as_name': name,
             'project_id': project_id,
             'specification': json.dumps(specification)}
        if callback_url:
            _LOGGER.debug('Job callback_url=%s (project_id=%s)',
                          callback_url, project_id)
            data['callback_url'] = callback_url
            if callback_context:
                _LOGGER.debug('Job callback_context=%s (project_id=%s)',
                              callback_context, project_id)
                data['callback_context'] = callback_context

        url: str = DmApi._dm_api_url + '/instance'

        try:
            resp: requests.Response =\
                requests.post(url,
                              headers=headers,
                              data=data,
                              timeout=timeout_s,
                              verify=DmApi._verify_ssl_cert)
        except:
            msg: str = 'Exception starting instance'
            _LOGGER.exception(msg)
            return DmApiRv(success=False, msg=msg)
        if resp.status_code not in [201]:
            return DmApiRv(success=False,
                           msg=f'Failed to start instance [{resp.status_code}]')

        # OK if we get here

        _LOGGER.debug('Started Job instance (project_id=%s)', project_id)

        instance_id: str = resp.json()['instance_id']
        task_id: str = resp.json()['task_id']
        return DmApiRv(success=True,
                       msg=f'instance_id={instance_id} task_id={task_id}')
