"""Python utilities to simplify calls to some parts of the Data Manager API that
interact with **Projects**, **Instances** (**Jobs**) and **Files**.

.. note::
    The URL to the DM API is automatically picked up from the environment variable
    ``SQUONK2_DMAPI_URL``, expected to be of the form **https://example.com/data-manager-api**.
    If the variable isn't set the user must set it programmatically
    using :py:meth:`DmApi.set_api_url()`.
"""

import contextlib
from dataclasses import dataclass
import decimal
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

from munch import DefaultMunch
from wrapt import synchronized
import requests


@dataclass
class DmApiRv:
    """The return value from most of the the DmApi class public methods.

    :param success: True if the call was successful, False otherwise.
    :param msg: API request response content
    :param munch_msg: A DefaultMunch object for the API request response content
    :param http_status_code: An HTTPS status code (0 if not available)
    """

    success: bool
    msg: Dict[Any, Any]
    defaultmunch_msg: DefaultMunch
    http_status_code: int


TEST_PRODUCT_ID: str = "product-11111111-1111-1111-1111-111111111111"
"""A test Account Server (AS) Product ID. This ID does not actually exist in the AS
but is accepted as valid by the Data Manager for Administrative users and used for
testing purposes. It allows the creation of Projects without the need of an AS Product.
"""
TEST_ORG_ID: str = "org-11111111-1111-1111-1111-111111111111"
TEST_UNIT_ID: str = "unit-11111111-1111-1111-1111-111111111111"

# The Job instance Application ID - a 'well known' identity.
_DM_JOB_APPLICATION_ID: str = "datamanagerjobs.squonk.it"
# The Data Manager API URL environment variable,
# You can set the API manually with set_apu_url() if this is not defined.
_API_URL_ENV_NAME: str = "SQUONK2_DMAPI_URL"
_API_VERIFY_SSL_CERT_ENV_NAME: str = "SQUONK2_DMAPI_VERIFY_SSL_CERT"

# A common read timeout
_READ_TIMEOUT_S: int = 4
# A longer timeout
_READ_LONG_TIMEOUT_S: int = 12

# Debug request times?
# If set the duration of each request call is logged.
_DEBUG_REQUEST_TIME: bool = False
# Debug request calls?
# If set the arguments and response of each request call is logged.
_DEBUG_REQUEST: bool = (
    os.environ.get("SQUONK2_API_DEBUG_REQUESTS", "no").lower() == "yes"
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


class DmApi:
    """The DmAPI class provides high-level, simplified access to the DM REST API.
    You can use the request module directly for finer control. This module
    provides a wrapper around the handling of the request, returning a simplified
    namedtuple response value ``DmApiRv``
    """

    # The default DM API is extracted from the environment,
    # otherwise it can be set using 'set_api_url()'
    __dm_api_url: str = os.environ.get(_API_URL_ENV_NAME, "")
    # Do we expect the DM API to be secure?
    # Normally yes, but this can be disabled using 'set_api_url()'
    __verify_ssl_cert: bool = (
        os.environ.get(_API_VERIFY_SSL_CERT_ENV_NAME, "yes").lower() == "yes"
    )
    # An object to return in DefaultMunch objects
    __undefined: object = object()

    @classmethod
    def __request(
        cls,
        method: str,
        endpoint: str,
        *,
        error_message: str,
        access_token: Optional[str] = None,
        expected_response_codes: Optional[List[int]] = None,
        headers: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = _READ_TIMEOUT_S,
    ) -> Tuple[DmApiRv, Optional[requests.Response]]:
        """Sends a request to the DM API endpoint. The caller normally has to provide
        an oauth-like access token but this is not mandated. Some DM API methods
        use DM-generated tokens rather than access tokens. If so the caller will pass
        this through via the URL or 'params' - whatever is appropriate for the call.

        All the public API methods pass control to this method,
        returning its result to the user.
        """
        assert method in {"GET", "POST", "PUT", "PATCH", "DELETE"}
        assert endpoint
        assert isinstance(expected_response_codes, (type(None), list))

        msg: Dict[Any, Any] = {}
        if not DmApi.__dm_api_url:
            msg = {"error": "No API URL defined"}
            return (
                DmApiRv(
                    success=False,
                    msg=msg,
                    defaultmunch_msg=DefaultMunch.fromDict(msg, DmApi.__undefined),
                    http_status_code=0,
                ),
                None,
            )

        url: str = DmApi.__dm_api_url + endpoint

        # if we have it, add the access token to the headers,
        # or create a headers block
        use_headers = headers.copy() if headers else {}
        if access_token:
            if headers:
                use_headers["Authorization"] = f"Bearer {access_token}"
            else:
                use_headers = {"Authorization": f"Bearer {access_token}"}

        if _DEBUG_REQUEST:
            print("# ---")
            print(f"# method={method}")
            print(f"# url={url}")
            print(f"# headers={use_headers}")
            print(f"# params={params}")
            print(f"# data={data}")
            print(f"# timeout={timeout}")
            print(f"# verify={DmApi.__verify_ssl_cert}")

        expected_codes = expected_response_codes or [200]
        resp: Optional[requests.Response] = None

        if _DEBUG_REQUEST_TIME:
            request_start: float = time.perf_counter()
        try:
            # Send the request (displaying the request/response)
            # and returning the response, whatever it is.
            resp = requests.request(
                method.upper(),
                url,
                headers=use_headers,
                params=params,
                data=data,
                files=files,
                timeout=timeout,
                verify=DmApi.__verify_ssl_cert,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            _LOGGER.exception("Request failed")

        # Try and decode the response,
        # replacing with empty dictionary on failure.
        if resp:
            with contextlib.suppress(Exception):
                msg = resp.json()
        http_status_code: int = 0 if resp is None else resp.status_code
        if _DEBUG_REQUEST:
            if resp is not None:
                print(
                    f"# request() status_code={resp.status_code} msg={msg}"
                    f" resp.text={resp.text}"
                )
            else:
                print("# request() resp=None")

        if _DEBUG_REQUEST_TIME:
            assert request_start
            request_finish: float = time.perf_counter()
            print(f"# request() duration={request_finish - request_start} seconds")

        if resp is None or resp.status_code not in expected_codes:
            msg = {"error": f"{error_message} (resp={resp})"}
            return (
                DmApiRv(
                    success=False,
                    msg=msg,
                    defaultmunch_msg=DefaultMunch.fromDict(msg, DmApi.__undefined),
                    http_status_code=http_status_code,
                ),
                resp,
            )

        return (
            DmApiRv(
                success=True,
                msg=msg,
                defaultmunch_msg=DefaultMunch.fromDict(msg, DmApi.__undefined),
                http_status_code=http_status_code,
            ),
            resp,
        )

    @classmethod
    def __put_unmanaged_project_file(
        cls,
        access_token: str,
        *,
        project_id: str,
        project_file: str,
        project_path: str = "/",
        timeout_s: int = 120,
    ) -> DmApiRv:
        """Puts an individual file into a DM project."""
        data: Dict[str, Any] = {}
        if project_path:
            data["path"] = project_path
        files = {
            "file": open(project_file, "rb")  # pylint: disable=consider-using-with
        }

        ret_val, resp = DmApi.__request(
            "PUT",
            f"/project/{project_id}/file",
            access_token=access_token,
            data=data,
            files=files,
            expected_response_codes=[201],
            error_message=f"Failed putting file {project_file} -> {project_path}",
            timeout=timeout_s,
        )

        if not ret_val.success:
            _LOGGER.debug(
                "Failed putting file %s -> %s (resp=%s project_id=%s)",
                project_file,
                project_path,
                resp,
                project_id,
            )
        return ret_val

    @classmethod
    def __set_job_exchange_rate(
        cls,
        access_token: str,
        *,
        rate: Dict[str, str],
        timeout_s: int = 120,
    ) -> DmApiRv:
        """Sets a single Job exchange rate."""
        assert isinstance(rate, dict)
        assert "collection" in rate
        assert "job" in rate
        assert "version" in rate
        assert "rate" in rate

        # The rate must be a decimal string.
        # Convert it to test this.
        rate_value = decimal.Decimal(rate["rate"])
        assert isinstance(rate_value, decimal.Decimal)

        # We're given a collection/job/version.
        # Try to get the Job ID from this information.
        collection: str = rate["collection"]
        job: str = rate["job"]
        version: str = rate["version"]
        params: Dict[str, str] = {
            "collection": collection,
            "job": job,
            "version": version,
        }
        ret_val, resp = DmApi.__request(
            "GET",
            "/job/get-by-version",
            access_token=access_token,
            params=params,
            expected_response_codes=[200],
            error_message=f"Failed getting job by version {collection}/{job}/{version}",
            timeout=timeout_s,
        )
        if not ret_val.success:
            _LOGGER.debug(
                "Failed to get Job ID %s (resp=%s)",
                rate,
                resp,
            )
            return ret_val

        assert resp
        assert resp.json()
        job_id: int = resp.json()["id"]
        data: Dict[str, str] = {"rate": rate["rate"]}
        if "comment" in rate:
            data["comment"] = rate["comment"]
        ret_val, resp = DmApi.__request(
            "PUT",
            f"/job/{job_id}/exchange-rate",
            access_token=access_token,
            data=data,
            expected_response_codes=[204],
            error_message=f"Failed setting rate for job {job_id} ({collection}/{job}/{version})"
            f" rate={rate}",
            timeout=timeout_s,
        )

        if not ret_val.success:
            _LOGGER.debug(
                "Failed putting rate %s (resp=%s)",
                rate,
                resp,
            )
        return ret_val

    @classmethod
    @synchronized
    def set_api_url(cls, url: str, *, verify_ssl_cert: bool = True) -> None:
        """Replaces the API URL value, which is otherwise set using
        the ``SQUONK2_DMAPI_URL`` environment variable.

        :param url: The API endpoint, typically **https://example.com/data-manager-api**
        :param verify_ssl_cert: Use False to avoid SSL verification in request calls
        """
        assert url
        DmApi.__dm_api_url = url
        DmApi.__verify_ssl_cert = verify_ssl_cert

        # Disable the 'InsecureRequestWarning'?
        if not verify_ssl_cert:
            disable_warnings(InsecureRequestWarning)

    @classmethod
    @synchronized
    def get_api_url(cls) -> Tuple[str, bool]:
        """Return the API URL and whether validating the SSL layer."""
        return DmApi.__dm_api_url, DmApi.__verify_ssl_cert

    @classmethod
    @synchronized
    def ping(cls, access_token: str, *, timeout_s: int = _READ_TIMEOUT_S) -> DmApiRv:
        """A handy API method that calls the DM API to ensure the server is
        responding.

        :param access_token: A valid DM API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return DmApi.__request(
            "GET",
            "/account-server/namespace",
            access_token=access_token,
            error_message="Failed ping",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_version(
        cls, access_token: Optional[str] = None, *, timeout_s: int = _READ_TIMEOUT_S
    ) -> DmApiRv:
        """Returns the DM-API service version.

        :param access_token: An optional valid DM API access token (deprecated)
        :param timeout_s: The underlying request timeout
        """

        return DmApi.__request(
            "GET",
            "/version",
            access_token=access_token,
            error_message="Failed getting version",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_job_definition_schema_version(
        cls, access_token: Optional[str] = None, *, timeout_s: int = _READ_TIMEOUT_S
    ) -> DmApiRv:
        """Returns the DM-API Job Definition schema version.

        :param access_token: An optional valid DM API access token (deprecated)
        :param timeout_s: The underlying request timeout
        """

        return DmApi.__request(
            "GET",
            "/job-definition-schema/version",
            access_token=access_token,
            error_message="Failed getting version",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_workflow_engine_version(
        cls, access_token: Optional[str] = None, *, timeout_s: int = _READ_TIMEOUT_S
    ) -> DmApiRv:
        """Returns the DM-API workflow engine version.

        :param access_token: An optional valid DM API access token (deprecated)
        :param timeout_s: The underlying request timeout
        """

        return DmApi.__request(
            "GET",
            "/workflow-engine/version",
            access_token=access_token,
            error_message="Failed getting version",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def create_project(
        cls,
        access_token: str,
        *,
        project_name: str,
        as_tier_product_id: str,
        private: bool = False,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Creates a Project, which requires a name and a Product ID
        (a Data Manger Project Tier Product) obtained from
        the Account Server.

        :param access_token: A valid DM API access token.
        :param project_name: A unique name.
        :param as_tier_product_id: If no account server is
            attached any suitable value can be used. If you are an admin user
            you can also use the reserved value of
            ``product-11111111-1111-1111-1111-111111111111``
            which is automatically accepted.
        :param timeout_s: The API request timeout
        """
        assert access_token
        assert project_name
        assert as_tier_product_id

        data: Dict[str, Any] = {
            "tier_product_id": as_tier_product_id,
            "name": project_name,
        }
        if private:
            data["private"] = True

        return DmApi.__request(
            "POST",
            "/project",
            access_token=access_token,
            data=data,
            expected_response_codes=[201],
            error_message="Failed creating project",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def delete_project(
        cls, access_token: str, *, project_id: str, timeout_s: int = _READ_TIMEOUT_S
    ) -> DmApiRv:
        """Deletes a project.

        :param access_token: A valid DM API access token
        :param project_id: The DM-API project id to delete
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert project_id

        return DmApi.__request(
            "DELETE",
            f"/project/{project_id}",
            access_token=access_token,
            error_message="Failed deleting project",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def add_project_editor(
        cls,
        access_token: str,
        *,
        project_id: str,
        editor: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Adds a user to a Project as an Editor.

        :param access_token: A valid DM API access token.
        :param project_id: The Project UUID.
        :param editor: The username to add.
        :param timeout_s: The API request timeout
        """
        assert access_token
        assert project_id
        assert editor

        return DmApi.__request(
            "PUT",
            f"/project/{project_id}/editor/{editor}",
            access_token=access_token,
            expected_response_codes=[201],
            error_message="Failed adding project editor",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def remove_project_editor(
        cls,
        access_token: str,
        *,
        project_id: str,
        editor: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Removes a user as an Editor from a Project.

        :param access_token: A valid DM API access token.
        :param project_id: The Project UUID.
        :param editor: The username to remove.
        :param timeout_s: The API request timeout
        """
        assert access_token
        assert project_id
        assert editor

        return DmApi.__request(
            "DELETE",
            f"/project/{project_id}/editor/{editor}",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed removing project editor",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def add_project_observer(
        cls,
        access_token: str,
        *,
        project_id: str,
        observer: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Adds a user to a Project as an Observer.

        :param access_token: A valid DM API access token.
        :param project_id: The Project UUID.
        :param editor: The username to add.
        :param timeout_s: The API request timeout
        """
        assert access_token
        assert project_id
        assert observer

        return DmApi.__request(
            "PUT",
            f"/project/{project_id}/observer/{observer}",
            access_token=access_token,
            expected_response_codes=[201],
            error_message="Failed adding project observer",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def remove_project_observer(
        cls,
        access_token: str,
        *,
        project_id: str,
        observer: str,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Removes a user as an Observer from a Project.

        :param access_token: A valid DM API access token.
        :param project_id: The Project UUID.
        :param observer: The username to remove.
        :param timeout_s: The API request timeout
        """
        assert access_token
        assert project_id
        assert observer

        return DmApi.__request(
            "DELETE",
            f"/project/{project_id}/observer/{observer}",
            access_token=access_token,
            expected_response_codes=[204],
            error_message="Failed removing project observer",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def put_unmanaged_project_files(
        cls,
        access_token: str,
        *,
        project_id: str,
        project_files: Union[str, List[str]],
        project_path: str = "/",
        force: bool = False,
        timeout_per_file_s: int = 120,
    ) -> DmApiRv:
        """Puts a file, or list of files, into a DM Project
        using an optional path.

        :param access_token: A valid DM API access token
        :param project_id: The project where the files are to be written
        :param project_files: A file or list of files. Leading paths are stripped
            so the two file files ``['dir/file-a.txt', 'file-b.txt']`` would
            be written to the same project directory, i.e. appearing as
            ``/file-a.txt`` and ``/file-b.txt`` in the project
        :param project_path: The path in the project to write the files.
            The path is relative to the project root and must begin ``/``
        :param force: Files are not written to the project if a file of the
            same name exists. Here ``force`` can be used to over-write files.
            Files on the server that are immutable cannot be over-written,
            and doing so will result in an error
        :param timeout_per_file_s: The underlying request timeout
        """

        assert access_token
        assert project_id
        assert project_files
        assert isinstance(project_files, (list, str))
        assert (
            project_path
            and isinstance(project_path, str)
            and project_path.startswith("/")
        )

        if not DmApi.__dm_api_url:
            msg = {"error": "No API URL defined"}
            return DmApiRv(
                success=False,
                msg=msg,
                defaultmunch_msg=DefaultMunch.fromDict(msg, DmApi.__undefined),
                http_status_code=0,
            )

        # If we're not forcing the files collect the names
        # of every file on the path - we use this to skip files that
        # are already present.
        existing_path_files: List[str] = []
        http_status_code: int = 0
        if not force:
            # What files already exist on the path?
            # To save time we avoid putting files that appear to exist.
            params: Dict[str, Any] = {"project_id": project_id}
            if project_path:
                params["path"] = project_path

            ret_val, resp = DmApi.__request(
                "GET",
                "/file",
                access_token=access_token,
                expected_response_codes=[200, 404],
                error_message="Failed getting existing project files",
                params=params,
            )
            if not ret_val.success:
                return ret_val

            assert resp is not None
            http_status_code = resp.status_code
            if resp.status_code in [200]:
                existing_path_files.extend(
                    item["file_name"] for item in resp.json()["files"]
                )

        # Now post every file that's not in the existing list
        if isinstance(project_files, str):
            src_files = [project_files]
        else:
            src_files = project_files
        for src_file in src_files:
            # Source file has to exist
            # whether we end up sending it or not.
            if not os.path.isfile(src_file):
                msg = {"error": f"No such file ({src_file})"}
                return DmApiRv(
                    success=False,
                    msg=msg,
                    defaultmunch_msg=DefaultMunch.fromDict(msg, DmApi.__undefined),
                    http_status_code=http_status_code,
                )
            if os.path.basename(src_file) not in existing_path_files:
                ret_val = DmApi.__put_unmanaged_project_file(
                    access_token,
                    project_id=project_id,
                    project_file=src_file,
                    project_path=project_path,
                    timeout_s=timeout_per_file_s,
                )

                if not ret_val.success:
                    return ret_val

        # OK if we get here
        return DmApiRv(
            success=True,
            msg={},
            defaultmunch_msg=DefaultMunch.fromDict({}, DmApi.__undefined),
            http_status_code=http_status_code,
        )

    @classmethod
    @synchronized
    def delete_unmanaged_project_files(
        cls,
        access_token: str,
        *,
        project_id: str,
        project_files: Union[str, List[str]],
        project_path: str = "/",
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Deletes an unmanaged project file, or list of files, on a project path.

        :param access_token: A valid DM API access token
        :param project_id: The project where the files are present
        :param project_files: A file or list of files. Leading paths are stripped
            so the two file files ``['dir/file-a.txt', 'file-b.txt']`` would
            be expected to be in the same project directory, i.e. appearing as
            ``/file-a.txt`` and ``/file-b.txt`` in the project
        :param project_path: The path in the project where the files are located.
            The path is relative to the project root and must begin ``/``
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert project_id
        assert isinstance(project_files, (list, str))
        assert (
            project_path
            and isinstance(project_path, str)
            and project_path.startswith("/")
        )

        if isinstance(project_files, str):
            files_to_delete = [project_files]
        else:
            files_to_delete = project_files

        for file_to_delete in files_to_delete:
            params: Dict[str, Any] = {
                "project_id": project_id,
                "path": project_path,
                "file": file_to_delete,
            }
            ret_val, _ = DmApi.__request(
                "DELETE",
                "/file",
                access_token=access_token,
                params=params,
                expected_response_codes=[204],
                error_message="Failed to delete project file",
                timeout=timeout_s,
            )
            if not ret_val.success:
                return ret_val

        # OK if we get here
        return DmApiRv(
            success=True,
            msg={},
            defaultmunch_msg=DefaultMunch.fromDict({}, DmApi.__undefined),
            http_status_code=0,
        )

    @classmethod
    @synchronized
    def list_project_files(
        cls,
        access_token: str,
        *,
        project_id: str,
        project_path: str = "/",
        include_hidden: bool = False,
        timeout_s: int = _READ_LONG_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets a list of project files on a path.

        :param access_token: A valid DM API access token
        :param project_id: The project where the files are present
        :param project_path: The path in the project to search for files.
            The path is relative to the project root and must begin ``/``
        :param include_hidden: Include hidden files in the response
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert project_id
        assert (
            project_path
            and isinstance(project_path, str)
            and project_path.startswith("/")
        )

        params: Dict[str, Any] = {
            "project_id": project_id,
            "path": project_path,
            "include_hidden": include_hidden,
        }
        return DmApi.__request(
            "GET",
            "/file",
            access_token=access_token,
            params=params,
            error_message="Failed to list project files",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_unmanaged_project_file(
        cls,
        access_token: str,
        *,
        project_id: str,
        project_file: str,
        local_file: str,
        project_path: str = "/",
        timeout_s: int = _READ_LONG_TIMEOUT_S,
    ) -> DmApiRv:
        """Get a single unmanaged file from a project path, save it to
        the filename defined in local_file.

        :param access_token: A valid DM API access token
        :param project_id: The project where the files are present
        :param project_file: The name of the file to get
        :param local_file: The name to use to write the file to on the client
        :param project_path: The path in the project to search for files.
            The path is relative to the project root and must begin ``/``
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert project_id
        assert project_file
        assert local_file
        assert (
            project_path
            and isinstance(project_path, str)
            and project_path.startswith("/")
        )

        params: Dict[str, Any] = {"path": project_path, "file": project_file}
        ret_val, resp = DmApi.__request(
            "GET",
            f"/project/{project_id}/file",
            access_token=access_token,
            params=params,
            error_message="Failed to get file",
            timeout=timeout_s,
        )
        if not ret_val.success:
            return ret_val

        # OK if we get here
        assert resp is not None
        with open(local_file, "wb") as file_handle:
            file_handle.write(resp.content)
        return ret_val

    @classmethod
    @synchronized
    def get_unmanaged_project_file_with_token(
        cls,
        *,
        token: str,
        project_id: str,
        project_file: str,
        local_file: str,
        project_path: str = "/",
        timeout_s: int = _READ_LONG_TIMEOUT_S,
    ) -> DmApiRv:
        """Like :py:meth:`~DmApi.get_unmanaged_project_file()`, this method
        gets a single unmanaged file from a project path. The method uses an
        Instance-generated callback token rather than a user-access token.

        This method is particularly useful in callback routines where a user
        access token may not be available. Callback tokens expire and can be
        deleted, and so this function should only be used when a user access
        token is not available.

        :param token: A DM-generated token, optionally generated when
            launching instances in the project
        :param project_id: The project where the files are present
        :param project_file: The name of the file to get
        :param local_file: The name to use to write the file to on the client
        :param project_path: The path in the project to search for files.
            The path is relative to the project root and must begin ``/``
        :param timeout_s: The underlying request timeout
        """
        assert token
        assert project_id
        assert project_file
        assert local_file
        assert (
            project_path
            and isinstance(project_path, str)
            and project_path.startswith("/")
        )

        params: Dict[str, Any] = {
            "path": project_path,
            "file": project_file,
            "token": token,
        }
        ret_val, resp = DmApi.__request(
            "GET",
            f"/project/{project_id}/file-with-token",
            params=params,
            error_message="Failed to get file",
            timeout=timeout_s,
        )
        if not ret_val.success:
            return ret_val

        # OK if we get here
        assert resp is not None
        with open(local_file, "wb") as file_handle:
            file_handle.write(resp.content)
        return ret_val

    @classmethod
    @synchronized
    def dry_run_job_instance(
        cls,
        access_token: str,
        *,
        project_id: str,
        name: str,
        specification: Dict[str, Any],
        callback_url: Optional[str] = None,
        callback_token: Optional[str] = None,
        callback_context: Optional[str] = None,
        generate_callback_token: bool = False,
        debug: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Optionally used prior to starting a Job instance, this method
        checks that Job Instance can be started in a Project, returning the
        Job command.

        :param access_token: A valid DM API access token
        :param project_id: The project where the files are present
        :param name: A name to associate with the Job
        :param specification: The Job specification, it must contain
            keys that define the Job's ``collection``, ``job name`` and
            ``version``. Job-specific variables are passed in using a ``variables``
            map in the specification
        :param callback_url: An optional URL capable of handling Job callbacks.
            Must be set if ``generate_callback_token`` is used
        :param callback_token: An optional callback token as an alternative to
            using ``generate_callback_token``
        :param callback_context: An optional context string passed to the
            callback URL
        :param generate_callback_token: True to instruct the DM to generate
            a token that can be used with some methods instead of a
            user access token
        :param debug: Used to prevent the automatic removal of the Job instance.
            Only use this if you need to
        :param timeout_s: The underlying request timeout
        """

        assert access_token
        assert project_id
        assert name
        assert isinstance(specification, (type(None), dict))

        data: Dict[str, Any] = {
            "application_id": _DM_JOB_APPLICATION_ID,
            "as_name": name,
            "project_id": project_id,
            "specification": json.dumps(specification),
        }
        if debug:
            data["debug"] = debug
        if callback_url:
            data["callback_url"] = callback_url
            if callback_context:
                data["callback_context"] = callback_context
            if generate_callback_token:
                data["generate_callback_token"] = True
            if callback_token:
                data["callback_token"] = callback_token

        return DmApi.__request(
            "POST",
            "/instance/dry-run",
            access_token=access_token,
            expected_response_codes=[201],
            error_message="Failed to start instance",
            data=data,
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def start_job_instance(
        cls,
        access_token: str,
        *,
        project_id: str,
        name: str,
        specification: Dict[str, Any],
        callback_url: Optional[str] = None,
        callback_token: Optional[str] = None,
        callback_context: Optional[str] = None,
        generate_callback_token: bool = False,
        debug: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Instantiates a Job Instance in a Project.

        :param access_token: A valid DM API access token
        :param project_id: The project where the files are present
        :param name: A name to associate with the Job
        :param specification: The Job specification, it must contain
            keys that define the Job's ``collection``, ``job name`` and
            ``version``. Job-specific variables are passed in using a ``variables``
            map in the specification
        :param callback_url: An optional URL capable of handling Job callbacks.
            Must be set if ``generate_callback_token`` is used
        :param callback_token: An optional callback token as an alternative to
            using ``generate_callback_token``
        :param callback_context: An optional context string passed to the
            callback URL
        :param generate_callback_token: True to instruct the DM to generate
            a token that can be used with some methods instead of a
            user access token
        :param debug: Used to prevent the automatic removal of the Job instance.
            Only use this if you need to
        :param timeout_s: The underlying request timeout
        """

        assert access_token
        assert project_id
        assert name
        assert isinstance(specification, (type(None), dict))

        data: Dict[str, Any] = {
            "application_id": _DM_JOB_APPLICATION_ID,
            "as_name": name,
            "project_id": project_id,
            "specification": json.dumps(specification),
        }
        if debug:
            data["debug"] = debug
        if callback_url:
            data["callback_url"] = callback_url
            if callback_context:
                data["callback_context"] = callback_context
            if generate_callback_token:
                data["generate_callback_token"] = True
            if callback_token:
                data["callback_token"] = callback_token

        return DmApi.__request(
            "POST",
            "/instance",
            access_token=access_token,
            expected_response_codes=[201],
            error_message="Failed to start instance",
            data=data,
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_available_projects(
        cls,
        access_token: str,
        *,
        project_name: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets information about all projects available to you.

        :param access_token: A valid DM API access token
        :param project_name: An optional project name to use as a filter
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        params: Dict[str, Any] = {}
        if project_name:
            params["project_name"] = project_name
        return DmApi.__request(
            "GET",
            "/project",
            access_token=access_token,
            params=params,
            error_message="Failed to get projects",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_project(
        cls, access_token: str, *, project_id: str, timeout_s: int = _READ_TIMEOUT_S
    ) -> DmApiRv:
        """Gets detailed information about a specific project.

        :param access_token: A valid DM API access token
        :param project_id: The specific project to retrieve
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert project_id

        return DmApi.__request(
            "GET",
            f"/project/{project_id}",
            access_token=access_token,
            error_message="Failed to get project",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_instance(
        cls, access_token: str, *, instance_id: str, timeout_s: int = _READ_TIMEOUT_S
    ) -> DmApiRv:
        """Gets information about an instance (Application or Job).

        :param access_token: A valid DM API access token
        :param instance_id: The specific instance to retrieve
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert instance_id

        return DmApi.__request(
            "GET",
            f"/instance/{instance_id}",
            access_token=access_token,
            error_message="Failed to get instance",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_project_instances(
        cls, access_token: str, *, project_id: str, timeout_s: int = _READ_TIMEOUT_S
    ) -> DmApiRv:
        """Gets information about all instances available to you.

        :param access_token: A valid DM API access token
        :param project_id: A valid DM project
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert project_id

        params: Dict[str, Any] = {"project_id": project_id}
        return DmApi.__request(
            "GET",
            "/instance",
            access_token=access_token,
            params=params,
            error_message="Failed to get project instances",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_available_instances(
        cls, access_token: str, *, timeout_s: int = _READ_TIMEOUT_S
    ) -> DmApiRv:
        """Gets information about all instances available to you.

        :param access_token: A valid DM API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return DmApi.__request(
            "GET",
            "/instance",
            access_token=access_token,
            error_message="Failed to get instances",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_available_tasks(
        cls,
        access_token: str,
        *,
        exclude_done: bool = False,
        exclude_purpose: Optional[str] = None,
        project_id: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets information about all tasks available to you.

        :param access_token: A valid DM API access token
        :param exclude_done: Set if you want to omit tasks that are 'done'
        :param exclude_purpose: A comma-separated list of purposes to exclude.
                          Any supported, e.g. DATASET, FILE, INSTANCE, PROJECT
        :param project_id: An optional project ID to limit tasks to
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        params: Dict[str, Any] = {}
        if exclude_done:
            params["exclude_done"] = True
        if exclude_purpose:
            params["exclude_purpose"] = exclude_purpose
        if project_id:
            params["project_id"] = project_id
        return DmApi.__request(
            "GET",
            "/task",
            access_token=access_token,
            params=params,
            error_message="Failed to get tasks",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def delete_instance(
        cls, access_token: str, *, instance_id: str, timeout_s: int = _READ_TIMEOUT_S
    ) -> DmApiRv:
        """Deletes an Instance (Application or Job).

        When instances are deleted the container is removed along with
        the instance-specific directory that is automatically created
        in the root of the project. Any files in the instance-specific
        directory will be removed.

        :param access_token: A valid DM API access token
        :param instance_id: The instance to delete
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert instance_id

        return DmApi.__request(
            "DELETE",
            f"/instance/{instance_id}",
            access_token=access_token,
            error_message="Failed to delete instance",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def delete_instance_token(
        cls, *, instance_id: str, token: str, timeout_s: int = _READ_TIMEOUT_S
    ) -> DmApiRv:
        """Deletes a DM API Instance **callback token**. This API method is not
        authenticated and therefore does not need an access token. Once the token is
        deleted no further calls to :py:meth:`DmApi.get_unmanaged_project_file_with_token()`
        will be possible. Once deleted the token cannot be re-instantiated.

        :param instance_id: A valid DM API instance
        :param token: The callback Token associated with the instance
        :param timeout_s: The API request timeout
        """
        assert instance_id
        assert token

        return DmApi.__request(
            "DELETE",
            f"/instance/{instance_id}/token/{token}",
            error_message="Failed to delete instance token",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_task(
        cls,
        access_token: str,
        *,
        task_id: str,
        event_prior_ordinal: int = 0,
        event_limit: int = 0,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets information about a specific Task

        :param access_token: A valid DM API access token
        :param task_id: The task
        :param event_prior_ordinal: The event prior ordinal, Use 0 for the first
        :param event_limit: The number of events to return. Use 0 for the default,
            which depends on the environment, and is typically 500
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert task_id
        assert event_prior_ordinal >= 0
        assert event_limit >= 0

        params: Dict[str, Any] = {}
        if event_prior_ordinal:
            params["event_prior_ordinal"] = event_prior_ordinal
        if event_limit:
            params["event_limit"] = event_limit
        return DmApi.__request(
            "GET",
            f"/task/{task_id}",
            access_token=access_token,
            params=params,
            error_message="Failed to get task",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_tasks(
        cls,
        access_token: str,
        *,
        exclude_done: bool = False,
        exclude_removal: bool = False,
        exclude_purpose: Optional[str] = None,
        project_id: Optional[str] = None,
        instance_callback_context: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets information about a range of Tasks

        :param access_token: A valid DM API access token
        :param exclude_done: Set if you do not want to see completed Tasks
        :param exclude_removal: Set if you do not want to see removal Tasks
        :param exclude_purpose: A dot-separated string of purposes to exclude.
                                From INSTANCE, FILE or DATASET
        :param project_id: Limit tasks to the given Project
        :param instance_callback_context: Limit tasks to those for Instances
                                          with the given callback context
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        params: Dict[str, Any] = {}
        if exclude_done:
            params["exclude_done"] = True
        if exclude_removal:
            params["exclude_removal"] = True
        if exclude_purpose:
            params["exclude_purpose"] = exclude_purpose
        if project_id:
            params["project_id"] = project_id
        if instance_callback_context:
            params["instance_callback_context"] = instance_callback_context
        return DmApi.__request(
            "GET",
            "/task",
            access_token=access_token,
            params=params,
            error_message="Failed to get tasks",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_available_jobs(
        cls, access_token: str, *, timeout_s: int = _READ_TIMEOUT_S
    ) -> DmApiRv:
        """Gets a summary list of available Jobs.

        :param access_token: A valid DM API access token.
        :param timeout_s: The API request timeout
        """
        assert access_token

        return DmApi.__request(
            "GET",
            "/job",
            access_token=access_token,
            error_message="Failed to get available jobs",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_jobs(
        cls,
        access_token: str,
        *,
        project_id: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets summary information about all Jobs.

        :param access_token: A valid DM API access token.
        :param project_id: An optional Project the Job is to be run in, e.g. ``project-0000``
        :param timeout_s: The API request timeout
        """
        assert access_token

        params = (
            {
                "project_id": project_id,
            }
            if project_id
            else None
        )
        return DmApi.__request(
            "GET",
            "/job",
            access_token=access_token,
            params=params,
            error_message="Failed to get jobs",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_job(
        cls,
        access_token: str,
        *,
        job_id: int,
        project_id: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets detailed information about a specific Job
        using the numeric Job record identity.

        :param access_token: A valid DM API access token.
        :param job_id: The numeric Job identity
        :param project_id: An optional Project the Job is to be run in, e.g. ``project-0000``
        :param timeout_s: The API request timeout
        """
        assert access_token
        assert job_id > 0

        params = (
            {
                "project_id": project_id,
            }
            if project_id
            else None
        )
        return DmApi.__request(
            "GET",
            f"/job/{job_id}",
            access_token=access_token,
            params=params,
            error_message="Failed to get job",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_job_by_version(
        cls,
        access_token: str,
        *,
        job_collection: str,
        job_job: str,
        job_version: str,
        project_id: str = "",
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets detailed information about a specific Job
        using its ``collection``, ``job`` and ``version``, using an optional
        target ``project_id``.

        :param access_token: A valid DM API access token.
        :param job_collection: The Job collection, e.g. ``im-test``
        :param job_job: The Job, e.g. ``nop``
        :param job_version: The Job version, e.g. ``1.0.0``
        :param project_id: An optional Project the Job is to be run in, e.g. ``project-0000``
        :param timeout_s: The API request timeout
        """
        assert access_token
        assert job_collection
        assert job_job
        assert job_version

        params: Dict[str, Any] = {
            "collection": job_collection,
            "job": job_job,
            "version": job_version,
        }
        if project_id:
            params["project_id"] = project_id

        return DmApi.__request(
            "GET",
            "/job/get-by-version",
            access_token=access_token,
            params=params,
            error_message="Failed to get job",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def set_admin_state(
        cls,
        access_token: str,
        *,
        admin: bool,
        impersonate: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Adds or removes the ``become-admin`` state of your account.
        Only users whose accounts offer administrative capabilities
        can use this method.

        :param access_token: A valid DM API access token.
        :param admin: True to set admin state
        :param impersonate: An optional username to switch to
        :param timeout_s: The API request timeout
        """
        assert access_token

        data: Dict[str, Any] = {"become_admin": admin}
        if impersonate:
            data["impersonate"] = impersonate

        return DmApi.__request(
            "PATCH",
            "/user/account",
            access_token=access_token,
            data=data,
            expected_response_codes=[204],
            error_message="Failed to set the admin state",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_service_errors(
        cls,
        access_token: str,
        *,
        include_acknowledged: bool = False,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets service errors. You need admin rights to use this method.

        :param access_token: A valid DM API access token
        :param include_acknowledged: True to include acknowledged errors
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        params: Dict[str, Any] = {}
        if include_acknowledged:
            params["include_acknowledged"] = True

        return DmApi.__request(
            "GET",
            "/admin/service-error",
            access_token=access_token,
            params=params,
            error_message="Failed to get service errors",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_job_exchange_rates(
        cls,
        access_token: str,
        *,
        only_undefined: bool = False,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets exchange rates for Jobs.

        :param access_token: A valid DM API access token
        :param only_undefined: True to only include jobs that have no exchange rate
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        params: Dict[str, Any] = {}
        if only_undefined:
            params["only_undefined"] = True

        return DmApi.__request(
            "GET",
            "/job/exchange-rate",
            access_token=access_token,
            params=params,
            error_message="Failed to get exchange rates",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def set_job_exchange_rates(
        cls,
        access_token: str,
        *,
        rates: Union[Dict[str, str], List[Dict[str, str]]],
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Sets exchange rates for Jobs, given one rate or a list of rates.

        A rate is a dictionary with keys 'collection', 'job', 'version', and 'rate'.
        An optional 'comment' can also be provided. The rate is expected to be a string
        representation of a decimal, i.e. '0.05'.

        :param access_token: A valid DM API access token
        :param rates: A rate or a list of rates
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert isinstance(rates, (dict, list))

        put_rates: List[Dict[str, str]] = []
        if isinstance(rates, dict):
            put_rates.append(rates)
        else:
            put_rates = rates

        for put_rate in put_rates:
            ret_val = DmApi.__set_job_exchange_rate(
                access_token,
                rate=put_rate,
                timeout_s=timeout_s,
            )
            if not ret_val.success:
                return ret_val

        # OK if we get here
        return DmApiRv(
            success=True,
            msg={},
            defaultmunch_msg=DefaultMunch.fromDict({}, DmApi.__undefined),
            http_status_code=0,
        )

    @classmethod
    @synchronized
    def put_job_manifest(
        cls,
        access_token: str,
        *,
        url: str,
        header: Optional[str] = None,
        params: Optional[str] = None,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Puts a Job Manifest onto server. The action requires the token to be
        that of an admin user.

        :param access_token: A valid DM API access token
        :param url: The location of the Manifest (typically a GitHub repository URL)
        :param header: An optional JSON string of header keys and values
        :param params: An optional JSON string of parameter keys and values
        :param timeout_s: The underlying request timeout
        """
        assert access_token
        assert url

        data: Dict[str, Any] = {"url": url}
        if header:
            data["header"] = header
        if params:
            data["params"] = params

        return DmApi.__request(
            "PUT",
            "/admin/job-manifest",
            data=data,
            access_token=access_token,
            expected_response_codes=[200],
            error_message="Failed to put job manifest",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_available_datasets(
        cls,
        access_token: str,
        *,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets Datasets available to the caller.

        :param access_token: A valid DM API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return DmApi.__request(
            "GET",
            "/dataset",
            access_token=access_token,
            error_message="Failed to get datasets",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_account_server_registration(
        cls,
        access_token: str,
        *,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets Datasets available to the caller.

        :param access_token: A valid DM API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return DmApi.__request(
            "GET",
            "/account-server/registration",
            access_token=access_token,
            error_message="Failed to get AS registration",
            timeout=timeout_s,
        )[0]

    @classmethod
    @synchronized
    def get_account_server_namespace(
        cls,
        access_token: str,
        *,
        timeout_s: int = _READ_TIMEOUT_S,
    ) -> DmApiRv:
        """Gets Datasets available to the caller.

        :param access_token: A valid DM API access token
        :param timeout_s: The underlying request timeout
        """
        assert access_token

        return DmApi.__request(
            "GET",
            "/account-server/namespace",
            access_token=access_token,
            error_message="Failed to get AS namespace",
            timeout=timeout_s,
        )[0]
