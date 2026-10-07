"""
about_controller.py
"""

from ...utils.logger import logger


class AboutController:

    def __init__(self, widget):

        self.widget = widget

        self.initialize()

    # =====================================================

    def initialize(self):

        logger.info("About Controller Initialized")

    # =====================================================

    def open_documentation(self):

        print("OPEN DOCUMENTATION")

    # =====================================================

    def open_repository(self):

        print("OPEN REPOSITORY")

    # =====================================================

    def open_homepage(self):

        print("OPEN HOMEPAGE")