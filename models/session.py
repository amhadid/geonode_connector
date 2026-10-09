"""
session.py

Session model for GeoNode Connector.

This module provides a singleton session manager that stores
authentication information during the plugin lifecycle.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class SessionData:
    """
    Authentication session data.
    """

    server_url: str = ""

    username: str = ""

    password: str = ""

    access_token: str = ""

    refresh_token: str = ""

    csrf_token: str = ""

    token_type: str = "Bearer"

    expires_in: Optional[int] = None

    expires_at: Optional[datetime] = None

    login_time: Optional[datetime] = None

    verify_ssl: bool = True

    timeout: int = 30

    is_authenticated: bool = False

    is_staff: bool = False

    is_superuser: bool = False

    user_id: Optional[int] = None

class Session:
    """
    Singleton authentication session.
    """

    _instance = None

    def __new__(cls):

        if cls._instance is None:

            cls._instance = super().__new__(cls)

            cls._instance.data = SessionData()

        return cls._instance

    # ==============================================================
    # Authentication
    # ==============================================================

    def set_authenticated(
        self,
        server_url: str,
        username: str,
        access_token: str,
        refresh_token: str = "",
        csrf_token: str = "",
        token_type: str = "Bearer",
        expires_in: Optional[int] = None,
        expires_at: Optional[datetime] = None,
        password: str = "",
        is_staff: bool = False,
        is_superuser: bool = False,
        user_id: Optional[int] = None,
    ) -> None:
        """
        Store authenticated session.
        """

        self.data.server_url = server_url

        self.data.username = username

        self.data.password = password

        self.data.access_token = access_token

        self.data.refresh_token = refresh_token

        self.data.csrf_token = csrf_token

        self.data.token_type = token_type

        self.data.expires_in = expires_in

        self.data.expires_at = expires_at

        self.data.login_time = datetime.now()

        self.data.is_authenticated = True

        self.data.is_staff = is_staff

        self.data.is_superuser = is_superuser

        self.data.user_id = user_id

    def update(self, **kwargs: Any) -> None:
        """
        Update selected session fields.
        """

        for key, value in kwargs.items():

            if key in self.data.__dataclass_fields__:

                setattr(
                    self.data,
                    key,
                    value,
                )

    def clear(self) -> None:
        """
        Clear authentication information while preserving
        connection configuration.
        """

        verify_ssl = self.data.verify_ssl

        timeout = self.data.timeout

        self.data = SessionData()

        self.data.verify_ssl = verify_ssl

        self.data.timeout = timeout

    # ==============================================================
    # Status
    # ==============================================================

    def is_logged_in(self) -> bool:

        return self.data.is_authenticated

    @property
    def authenticated(self) -> bool:

        return self.data.is_authenticated

    @property
    def is_authenticated(self) -> bool:

        return self.data.is_authenticated

    # ==============================================================
    # Read-only Properties
    # ==============================================================

    @property
    def server_url(self) -> str:

        return self.data.server_url

    @server_url.setter
    def server_url(self, value: str) -> None:

        self.data.server_url = value

    @property
    def username(self) -> str:

        return self.data.username

    @property
    def password(self) -> str:

        return self.data.password

    @property
    def access_token(self) -> str:

        return self.data.access_token

    @property
    def refresh_token(self) -> str:

        return self.data.refresh_token

    @property
    def csrf_token(self) -> str:

        return self.data.csrf_token

    @property
    def token_type(self) -> str:

        return self.data.token_type

    @property
    def expires_in(self) -> Optional[int]:

        return self.data.expires_in

    @property
    def expires_at(self) -> Optional[datetime]:

        return self.data.expires_at

    @property
    def is_staff(self) -> bool:

        return self.data.is_staff

    @property
    def is_superuser(self) -> bool:

        return self.data.is_superuser

    @property
    def user_id(self) -> Optional[int]:

        return self.data.user_id

    # ==============================================================
    # Serialization
    # ==============================================================

    def to_dict(self) -> Dict[str, Any]:

        return asdict(self.data)

    def from_dict(
        self,
        data: Dict[str, Any],
    ) -> None:

        for key, value in data.items():

            if key not in self.data.__dataclass_fields__:

                continue

            setattr(
                self.data,
                key,
                value,
            )

session = Session()