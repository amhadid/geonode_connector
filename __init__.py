# -*- coding: utf-8 -*-
"""
GeoNode Connector

QGIS plugin entry point.

This module is loaded by QGIS when the plugin is enabled.
Its only responsibility is to instantiate the plugin class.
"""

from __future__ import annotations

from qgis.gui import QgisInterface

from .utils.logger import get_logger


logger = get_logger(__name__)


def classFactory(iface: QgisInterface):
    """
    Create and return the GeoNode Connector plugin instance.

    Parameters
    ----------
    iface : QgisInterface
        QGIS application interface.

    Returns
    -------
    GeoNodeConnector
        Plugin instance.
    """

    try:

        from .GeoNode_connector import GeoNodeConnector

        logger.info(
            "Loading GeoNode Connector plugin."
        )

        return GeoNodeConnector(iface)

    except Exception as exc:

        logger.exception(
            "Unable to load GeoNode Connector plugin."
        )

        raise