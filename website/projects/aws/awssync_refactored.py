from __future__ import annotations

import logging

from projects.aws.awsapitalker import AWSAPITalker


class AWSSyncRefactored:
    """Synchronise with Amazon Web Services."""

    def __init__(self):
        """Create an AWSSync instance."""
        self.api_talker = AWSAPITalker()

        self.logger = logging.getLogger("django.aws")
        self.logger.setLevel(logging.DEBUG)
