# -*- coding: utf-8 -*-
"""
GeoNode Connector

Main plugin implementation.

This module is responsible for integrating the plugin into
the QGIS application lifecycle.
"""

from __future__ import annotations

import os

from qgis.PyQt.QtCore import (
    QCoreApplication,
    QLocale,
    Qt,
    QTranslator,
)

from qgis.PyQt.QtGui import QIcon

from qgis.PyQt.QtWidgets import QAction

from qgis.core import (
    QgsSettings,
    Qgis,
)

from .GeoNode_connector_dockwidget import (
    GeoNodeConnectorDialog,
)

from .utils.config import (
    DEFAULT_SERVER,
    ICON_PATH,
    PLUGIN_NAME,
)

from .utils.logger import get_logger

from .utils.settings import PluginSettings

from .utils.validator import Validator


logger = get_logger(__name__)


class GeoNodeConnector:
    """
    Main QGIS plugin implementation.
    """

    def __init__(self, iface):
        """
        Initialize plugin.

        Parameters
        ----------
        iface : QgisInterface
            QGIS interface.
        """

        self.iface = iface

        self.plugin_dir = os.path.dirname(__file__)

        self.actions = []

        self.menu = self.tr(
            PLUGIN_NAME
        )

        self.toolbar = self.iface.addToolBar(
            PLUGIN_NAME
        )

        self.toolbar.setObjectName(
            PLUGIN_NAME
        )

        self.plugin_is_active = False

        self.dockwidget = None

        self.translator = None

        self._load_translator()

    # ==============================================================
    # Translation
    # ==============================================================

    def _load_translator(self):
        """
        Load translation file if available.
        """

        locale = QgsSettings().value(
            "locale/userLocale",
            QLocale().name()
        )[:2]

        locale_path = os.path.join(
            self.plugin_dir,
            "i18n",
            "{}.qm".format(locale),
        )

        if not os.path.exists(
            locale_path
        ):

            return

        self.translator = QTranslator()

        if self.translator.load(
            locale_path
        ):

            QCoreApplication.installTranslator(
                self.translator
            )

            logger.info(
                "Translation loaded: %s",
                locale,
            )

    # ==============================================================
    # Helper
    # ==============================================================

    @staticmethod
    def tr(message):
        """
        Translate message.
        """

        return QCoreApplication.translate(
            "GeoNodeConnector",
            message,
        )

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """
        Create QAction.
        """

        action = QAction(
            QIcon(icon_path),
            text,
            parent,
        )

        action.triggered.connect(
            callback
        )

        action.setEnabled(
            enabled
        )

        if status_tip:

            action.setStatusTip(
                status_tip
            )

        if whats_this:

            action.setWhatsThis(
                whats_this
            )

        if add_to_toolbar:

            self.toolbar.addAction(
                action
            )

        if add_to_menu:

            self.iface.addPluginToMenu(
                self.menu,
                action,
            )

        self.actions.append(
            action
        )

        return action

    # ==============================================================
    # QGIS GUI
    # ==============================================================

    def initGui(self):
        """
        Initialize QGIS GUI.
        """

        logger.info(
            "Initializing %s",
            PLUGIN_NAME,
        )

        self.add_action(
            icon_path=ICON_PATH,
            text=self.tr(PLUGIN_NAME),
            callback=self.run,
            parent=self.iface.mainWindow(),
        )

    # ==============================================================
    # Dock Widget
    # ==============================================================

    def _create_dockwidget(self):
        """
        Create dock widget if necessary.
        """

        if self.dockwidget is not None:

            return

        logger.debug(
            "Creating dock widget."
        )

        self.dockwidget = GeoNodeConnectorDialog(
            iface=self.iface,
            parent=self.iface.mainWindow() if self.iface else None,
        )

        self.dockwidget.closingPlugin.connect(
            self.on_close_plugin
        )

    # ==============================================================
    # Plugin
    # ==============================================================

    def run(self):
        """
        Start plugin.
        """

        if self.plugin_is_active:

            if self.dockwidget:

                self.dockwidget.raise_()

                self.dockwidget.activateWindow()

            return

        logger.info(
            "========================================"
        )

        logger.info(
            "%s started.",
            PLUGIN_NAME,
        )

        logger.info(
            "QGIS Version : %s",
            Qgis.QGIS_VERSION,
        )

        logger.info(
            "========================================"
        )

        #
        # Initialize settings.
        #

        if not PluginSettings.contains(
            "server"
        ):

            PluginSettings.set_value(
                "server",
                DEFAULT_SERVER,
            )

        server = PluginSettings.server_url()

        logger.info(
            "Server : %s",
            server,
        )

        logger.info(
            "Valid URL : %s",
            Validator.validate_url(
                server,
            ),
        )

        #
        # Create dock widget.
        #

        self._create_dockwidget()

        self.dockwidget.show()

        self.dockwidget.raise_()

        self.dockwidget.activateWindow()

        self.plugin_is_active = True

        logger.info(
            "Dock widget displayed."
        )

    # ==============================================================
    # Close
    # ==============================================================

    def on_close_plugin(self):
        """
        Handle dock widget closing.
        """

        logger.info(
            "Dock widget closed."
        )

        if self.dockwidget:

            try:

                self.dockwidget.closingPlugin.disconnect(
                    self.on_close_plugin
                )

            except TypeError:

                pass

        self.plugin_is_active = False

    # ==============================================================
    # Cleanup
    # ==============================================================

    def unload(self):
        """
        Unload plugin from QGIS.
        """

        logger.info(
            "Unloading %s",
            PLUGIN_NAME,
        )

        #
        # Remove menu & toolbar actions.
        #

        for action in self.actions:

            self.iface.removePluginMenu(
                self.menu,
                action,
            )

            self.iface.removeToolBarIcon(
                action,
            )

        self.actions.clear()

        #
        # Remove toolbar.
        #

        if self.toolbar is not None:

            del self.toolbar

            self.toolbar = None

        #
        # Remove dock widget.
        #

        if self.dockwidget is not None:

            try:

                self.dockwidget.closingPlugin.disconnect(
                    self.on_close_plugin
                )

            except TypeError:

                pass

            self.dockwidget.close()

            self.dockwidget.deleteLater()

            self.dockwidget = None

        self.plugin_is_active = False

        logger.info(
            "%s unloaded successfully.",
            PLUGIN_NAME,
        )