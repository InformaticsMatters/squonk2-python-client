"""Python utilities to simplify calls to the Data Manager API.
"""
from collections import namedtuple
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

from wrapt import synchronized
import requests

# The return value from an API call.
# 'success' (a boolean) is True if the call was successful, False otherwise.
# The 'msg' (a string used on failure) will provide a potentially useful
# error message.
DmApiRv: namedtuple = namedtuple('DmApiRv', 'success msg')

# The Job Operator details
_DM_JOB_APPLICATION_ID: str = 'datamanagerjobs.squonk.it'
_DM_JOB_APPLICATION_VERSION: str = 'v1'

_LOGGER: logging.Logger = logging.getLogger(__name__)


class DmApi:
    """Simplified API access methods.
    """

    # The default DM API is extracted from the environment,
    # otherwise it can be set using 'set_api_url()'
    _dm_api_url: str = os.environ.get('SQUONK_API_URL', '')

    @classmethod
    @synchronized
    def set_api_url(cls, url: str) -> None:
        """Replaces the class API URL value.
        """
        assert url
        DmApi._dm_api_url = url

    @classmethod
    @synchronized
    def get_access_token(cls,
                         keycloak_url: str,
                         keycloak_realm: str,
                         keycloak_client_id: str,
                         username: str,
                         password: str,
                         timeout_s: int = 4) -> Optional[str]:
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
    def _put_project_file(cls,
                          access_token: str,
                          project_id: str,
                          project_file: str,
                          project_path: Optional[str] = None,
                          timeout_s: int = 120) -> bool:

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
                                timeout=timeout_s)
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
                          project_path: Optional[str] = None,
                          force: bool = False,
                          timeout_s: int = 120):
        """Puts a file, or list of files, into a DM Project
        using an optional path. The files can include relative or absolute
        paths but are written to the same path in the project.
        """

        assert access_token
        assert project_id
        assert project_files
        assert isinstance(project_files, (list, str))

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg='No API URL defined')

        headers: Dict[str, Any] = {'Authorization': 'Bearer ' + access_token}

        existing_path_files: List[str] = []
        if not force:

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
                                 timeout=timeout_s)
            except:
                msg: str = 'Exception getting files'
                _LOGGER.exception(msg)
                return DmApiRv(success=False, msg=msg)

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
            if src_file not in existing_path_files:
                if not DmApi._put_project_file(access_token,
                                               project_id,
                                               src_file,
                                               project_path):
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

        if not DmApi._dm_api_url:
            return DmApiRv(success=False, msg='No API URL defined')

        _LOGGER.debug('Starting Job instance (project_id=%s)', project_id)

        headers: Dict[str, Any] = {'Authorization': 'Bearer ' + access_token}

        data: Dict[str, Any] =\
            {'application_id': _DM_JOB_APPLICATION_ID,
             'application_version': _DM_JOB_APPLICATION_VERSION,
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
                              timeout=timeout_s)
        except:
            msg: str = 'Exception starting instance'
            _LOGGER.exception(msg)
            return DmApiRv(success=False,msg=msg)
        if resp.status_code not in [201]:
            return DmApiRv(success=False,
                           msg=f'Failed to star instance [{resp.status_code}]')

        # OK if we get here

        _LOGGER.debug('Started Job instance (project_id=%s)', project_id)

        instance_id: str = resp.json()['instance_id']
        task_id: str = resp.json()['task_id']
        return DmApiRv(success=True,
                       msg=f'instance_id={instance_id} task_id={task_id}')
