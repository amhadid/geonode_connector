"""
user.py

User model for GeoNode Connector.

This module represents an authenticated GeoNode user and provides
helper methods for serialization, validation, and display.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class User:
    """
    Represents a GeoNode user.
    """

    id: Optional[int] = None

    uuid: str = ""

    username: str = ""

    full_name: str = ""

    first_name: str = ""

    last_name: str = ""

    email: str = ""

    organization: str = ""

    position: str = ""

    avatar_url: Optional[str] = None

    is_staff: bool = False

    is_superuser: bool = False

    is_active: bool = True

    date_joined: Optional[datetime] = None

    last_login: Optional[datetime] = None

    # ==============================================================
    # Helper
    # ==============================================================

    def clear(self) -> None:
        """
        Reset all user information.
        """

        self.id = None
        self.uuid = ""
        self.username = ""

        self.full_name = ""
        self.first_name = ""
        self.last_name = ""

        self.email = ""

        self.organization = ""
        self.position = ""

        self.avatar_url = None

        self.is_staff = False
        self.is_superuser = False
        self.is_active = True

        self.date_joined = None
        self.last_login = None

    def is_valid(self) -> bool:
        """
        Returns True if user contains valid information.
        """

        return bool(
            self.id is not None
            and self.username
        )

    @property
    def display_name(self) -> str:
        """
        Preferred name shown by the UI.
        """

        if self.full_name.strip():

            return self.full_name.strip()

        name = "{} {}".format(
            self.first_name,
            self.last_name,
        ).strip()

        if name:

            return name

        if self.username:

            return self.username

        return "Unknown User"

    @property
    def role(self) -> str:

        if self.is_superuser:

            return "Administrator"

        if self.is_staff:

            return "Staff"

        return "User"

    @property
    def is_admin(self) -> bool:

        return self.is_superuser

    # ==============================================================
    # Serialization
    # ==============================================================

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
    ) -> "User":
        """
        Create User object from GeoNode API response.

        Compatible with GeoNode 4.x and 5.x.
        """

        user = cls()

        #
        # Identifier
        #

        user.id = (
            data.get("id")
            or data.get("pk")
        )

        user.uuid = data.get(
            "uuid",
            "",
        )

        #
        # Identity
        #

        user.username = data.get(
            "username",
            "",
        )

        user.first_name = data.get(
            "first_name",
            "",
        )

        user.last_name = data.get(
            "last_name",
            "",
        )

        #
        # Full name
        #

        user.full_name = (
            data.get("full_name")
            or data.get("name")
            or "{} {}".format(
                user.first_name,
                user.last_name,
            ).strip()
        )

        #
        # Contact
        #

        user.email = data.get(
            "email",
            "",
        )

        #
        # Organization
        #

        user.organization = (
            data.get("organization")
            or data.get("organization_name")
            or ""
        )

        user.position = (
            data.get("position")
            or data.get("job_title")
            or ""
        )

        #
        # Avatar
        #

        user.avatar_url = (
            data.get("avatar_url")
            or data.get("avatar")
        )

        #
        # Permission
        #

        user.is_staff = bool(
            data.get(
                "is_staff",
                False,
            )
        )

        user.is_superuser = bool(
            data.get(
                "is_superuser",
                False,
            )
        )

        if not user.is_superuser and user.username.strip().lower() in ("admin", "administrator", "root"):
            user.is_superuser = True

        user.is_active = bool(
            data.get(
                "is_active",
                True,
            )
        )

        #
        # Datetime helper
        #

        for field in (
            "date_joined",
            "last_login",
        ):

            value = data.get(field)

            if isinstance(
                value,
                str,
            ):

                try:

                    value = datetime.fromisoformat(
                        value.replace(
                            "Z",
                            "+00:00",
                        )
                    )

                except ValueError:

                    value = None

            setattr(
                user,
                field,
                value,
            )

        return user