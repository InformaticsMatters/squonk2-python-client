"""Environment module.

Reads the environment file exposing the values for the chosen environment.

The environment files is a convenient KUBECONFIG-like file
that allows you to have all the variables set for all your environments,
so you need only create a single file and not have to painfully create
environment variables each time you want to interact wih the corresponding
API. All you need to do, if you don't have your environment files
in '~/.squonk2' is to set the variable SQUONK2_ENVIRONMENTS_FILE to identify
your chosen file.
"""
import os
from typing import Any, Dict, List, Optional

from yaml import FullLoader, load

# The environments file (YAML) is typically expected in the user's '~/.squonk2'
# directory. It contains 'environments' that define the connection details
# for the various Keycloak, Data Manager and Account Server services.
# This default is replaced with the value of the environment variable
# 'SQUONK2_ENVIRONMENTS_FILE'.
#
# See the project's 'environments' file for an example of the content of the file.
_ENVIRONMENT_DIRECTORY: str = "~/.squonk2"
_ENVIRONMENT_FILE: str = os.environ.get(
    "SQUONK2_ENVIRONMENTS_FILE", f"{_ENVIRONMENT_DIRECTORY}/environments"
)

# The key for the block of environments
_ENVIRONMENTS_KEY: str = "environments"
# The key for the 'default' environment
_DEFAULT_KEY: str = "default"

# Keys required in each environment.
_KEYCLOAK_HOSTNAME_KEY: str = "keycloak-hostname"
_KEYCLOAK_REALM_KEY: str = "keycloak-realm"
_KEYCLOAK_DM_CLIENT_ID_KEY: str = "keycloak-dm-client-id"
_DM_HOSTNAME_KEY: str = "dm-hostname"
# Optional keys (extracted from ENV if not present)
_ADMIN_USER_KEY: str = "admin-user"
_ADMIN_PASSWORD_KEY: str = "admin-password"
# Optional keys
_KEYCLOAK_AS_CLIENT_ID_KEY: str = "keycloak-as-client-id"
_AS_HOSTNAME_KEY: str = "as-hostname"


class Environment:
    """Loads the values from the environment file for the given environment."""

    # Location of the file
    __environments_file: str = os.path.expandvars(os.path.expanduser(_ENVIRONMENT_FILE))
    # Dictionary-form of the entire file
    __environments_config: Dict[str, Any] = {}
    # List of names in the configuration
    __environment_names: List[str] = []
    # The default environment, set during a call to load()
    __default_environment: Optional[str] = None

    @classmethod
    def load(cls) -> List[str]:
        """Load the environments file.
        This is done simply to provide the caller with the list
        of environments that can be used, returning their names.
        The default environment is the first in the list.
        """
        # Return names if we've already loaded them.
        if Environment.__environment_names:
            return Environment.__environment_names

        # Regardless, if there is no default environment directory, create one.
        # During CI this will fail, so we avoid creating the
        # directory if CI is set.
        if not os.environ.get("CI"):
            os.makedirs(os.path.expanduser(_ENVIRONMENT_DIRECTORY), exist_ok=True)

        if not os.path.exists(Environment.__environments_file):
            raise Exception(f"{Environment.__environments_file} does not exist")
        with open(Environment.__environments_file, encoding="utf8") as config_file:
            Environment.__environments_config = load(config_file, Loader=FullLoader)
        # Does it look like YAML?
        if not Environment.__environments_config:
            raise Exception(f"{Environment.__environments_file} is empty")
        if not isinstance(Environment.__environments_config, dict):
            raise Exception(
                f"{Environment.__environments_file} is not formatted correctly"
            )
        if _DEFAULT_KEY not in Environment.__environments_config:
            raise Exception(
                f"{Environment.__environments_file} does not have a '{_DEFAULT_KEY}'"
            )
        if _ENVIRONMENTS_KEY not in Environment.__environments_config:
            raise Exception(
                f"{Environment.__environments_file} does not have a '{_ENVIRONMENTS_KEY}' section"
            )

        Environment.__default_environment = Environment.__environments_config[
            _DEFAULT_KEY
        ]
        assert Environment.__default_environment
        found_default: bool = False
        Environment.__environment_names = [Environment.__default_environment]
        for environment in Environment.__environments_config[_ENVIRONMENTS_KEY]:
            if environment == Environment.__default_environment:
                found_default = True
            else:
                Environment.__environment_names.append(environment)

        if not found_default:
            raise Exception(
                f"{Environment.__environments_file} default is not in '{_ENVIRONMENTS_KEY}'"
            )

        assert Environment.__environment_names
        return Environment.__environment_names

    def __get_config_value(
        self,
        key: str,
        optional: bool = False,
        permit_environment_variable: bool = False,
    ) -> Optional[str]:
        """Gets the configuration key's value for the configured environment.
        If optional is False we assert if a value cannot be found.

        If 'permit_environment_variable' is True then if no key is found
        in the file, a corresponding value will be sought from the environment.
        If the config value is `admin-user` then the environment variable that will be
        inspected will be SQUONK2_ENVIRONMENT_{name}_ADMIN_USER).
        """
        assert Environment.__environments_config
        value: Any = Environment.__environments_config[_ENVIRONMENTS_KEY][
            self.__environment
        ].get(key)

        if not value and permit_environment_variable:
            # No key/value in the file but allowed to check the environment.
            translated_environment: str = self.__environment.upper().replace("-", "_")
            translated_key: str = key.upper().replace("-", "_")
            env_key: str = (
                f"SQUONK2_ENVIRONMENT_{translated_environment}_{translated_key}"
            )
            value = os.environ.get(env_key)

        if not optional and not value:
            raise Exception(
                f"{Environment.__environments_file} '{self.__environment}'"
                f" could not determine value for '{key}'"
            )

        return str(value) if value else None

    def __init__(self, environment: Optional[str]):
        """Prepare the environment object. The user is expected to have called
        'Environment.load()' first. If an environment is not named the default is used.
        """
        if environment:
            # User has named an environment,
            # use it
            self.__environment: str = environment
            if not environment in Environment.__environment_names:
                raise Exception(
                    f"{Environment.__environments_file} '{environment}'"
                    " environment does not exist"
                )
        else:
            # Nothing named - use the default
            assert Environment.__default_environment
            self.__environment = Environment.__default_environment

        # Get the required key values...
        # We assert if these cannot be found.
        self.__keycloak_hostname: str = str(
            self.__get_config_value(_KEYCLOAK_HOSTNAME_KEY)
        )
        self.__keycloak_realm: str = str(self.__get_config_value(_KEYCLOAK_REALM_KEY))
        self.__keycloak_dm_client_id: str = str(
            self.__get_config_value(_KEYCLOAK_DM_CLIENT_ID_KEY)
        )
        self.__dm_hostname: str = str(self.__get_config_value(_DM_HOSTNAME_KEY))

        # Get required keys, but allowing environment variables
        # if not present in the file...
        self.__admin_user: str = str(
            self.__get_config_value(_ADMIN_USER_KEY, permit_environment_variable=True)
        )
        self.__admin_password = str(
            self.__get_config_value(
                _ADMIN_PASSWORD_KEY, permit_environment_variable=True
            )
        )

        # Get the optional key values...
        self.__keycloak_as_client_id: Optional[str] = self.__get_config_value(
            _KEYCLOAK_AS_CLIENT_ID_KEY, optional=True
        )
        self.__as_hostname: Optional[str] = self.__get_config_value(
            _AS_HOSTNAME_KEY, optional=True
        )

    @property
    def environment(self) -> str:
        """Return the environment name."""
        return self.__environment

    @property
    def keycloak_hostname(self) -> str:
        """Return the keycloak hostname. This is the unmodified
        value found in the environment.
        """
        return self.__keycloak_hostname

    @property
    def keycloak_url(self) -> str:
        """Return the keycloak URL. This is the hostname
        plus the 'http' prefix and '/auth' postfix.
        """
        if not self.__keycloak_hostname.startswith("http"):
            ret_val: str = f"https://{self.__keycloak_hostname}"
        else:
            ret_val = self.__keycloak_hostname
        if not ret_val.endswith("/auth"):
            ret_val += "/auth"
        return ret_val

    @property
    def keycloak_realm(self) -> str:
        """Return the keycloak realm."""
        return self.__keycloak_realm

    @property
    def keycloak_as_client_id(self) -> Optional[str]:
        """Return the keycloak Account Server client ID."""
        return self.__keycloak_as_client_id

    @property
    def keycloak_dm_client_id(self) -> str:
        """Return the keycloak Data Manager client ID."""
        return self.__keycloak_dm_client_id

    @property
    def admin_user(self) -> str:
        """Return the keycloak username."""
        return self.__admin_user

    @property
    def admin_password(self) -> str:
        """Return the keycloak user's password."""
        return self.__admin_password

    @property
    def as_hostname(self) -> Optional[str]:
        """Return the keycloak hostname. This is the unmodified
        value found in the environment but can be None
        """
        return self.__as_hostname

    @property
    def as_api(self) -> Optional[str]:
        """Return the AS API. This is the environment hostname
        with a 'http' prefix and '/account-server-api' postfix.
        """
        if not self.__as_hostname:
            return None
        if not self.__as_hostname.startswith("http"):
            ret_val: str = f"https://{self.__as_hostname}"
        else:
            ret_val = self.__as_hostname
        if not ret_val.endswith("/account-server-api"):
            ret_val += "/account-server-api"
        return ret_val

    @property
    def dm_hostname(self) -> str:
        """Return the keycloak hostname. This is the unmodified
        value found in the environment.
        """
        return self.__dm_hostname

    @property
    def dm_api(self) -> str:
        """Return the DM API. This is the environment hostname
        with a 'http' prefix and '/data-manager-api' postfix.
        """
        if not self.__dm_hostname.startswith("http"):
            ret_val: str = f"https://{self.__dm_hostname}"
        else:
            ret_val = self.__dm_hostname
        if not ret_val.endswith("/data-manager-api"):
            ret_val += "/data-manager-api"
        return ret_val
