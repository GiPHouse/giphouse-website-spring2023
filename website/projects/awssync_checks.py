from __future__ import annotations

import logging

from projects.awssync_structs import AWSTree


class Checks:
    """Class for pipline checks."""

    def __init__(self) -> None:
        """Initialize Checks class."""
        self.logger = logging.getLogger("django.aws")
        self.logger.setLevel(logging.DEBUG)

    def check_members_in_correct_iteration(self, AWSdata: AWSTree) -> None:
        """Check if the data from the member tag matches the semester OU it is in."""
        incorrect_emails = []
        for iteration in AWSdata.iterations:
            for member in iteration.members:
                if member.project_semester != iteration.name:
                    incorrect_emails.append(member.project_email)

        if incorrect_emails != []:
            self.logger.error("There are members in a course iteration OU with an inconsistent course iteration tag.")
            self.logger.debug(f"{incorrect_emails}")
            raise Exception("There are members in a course iteration OU with an inconsistent course iteration tag.")

    def check_double_iteration_names(self, AWSdata: AWSTree) -> None:
        """Check if there are multiple OU's with the same name in AWS."""
        names = [iteration.name for iteration in AWSdata.iterations]
        doubles = []

        for name in names:
            if names.count(name) != 1 and name not in doubles:
                doubles.append(name)

        if doubles != []:
            self.logger.error("There are multiple course iteration OUs with the same name.")
            self.logger.debug(f"{doubles}")
            raise Exception("There are multiple course iteration OUs with the same name.")
