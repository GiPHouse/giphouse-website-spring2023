import logging

import boto3

from botocore.exceptions import ClientError


class AWSSync:
    """Synchronise with Amazon Web Services."""

    def __init__(self):
        """Create an AWSSync instance."""
        self.logger = logging.getLogger("django.aws")
        self.org_info = None
        self.iterationOU_info = None
        self.fail = False
        self.logger.info("Created AWSSync instance.")

    def button_pressed(self):
        """
        Print debug message to show that the button has been pressed.

        :return: True if function executes successfully
        """
        self.logger.info("Pressed button")
        return True

    def create_aws_organization(self):
        """Create an AWS organization with the current user as the management account."""
        client = boto3.client("organizations")
        try:
            response = client.create_organization(FeatureSet="ALL")
            self.org_info = response["Organization"]
            self.logger.info("Created an AWS organization and saved organization info.")
        except ClientError as error:
            self.fail = True
            self.logger.error("Something went wrong creating an AWS organization.")
            self.logger.debug(f"{error}")
            self.logger.debug(f"{error.response}")

    def create_course_iteration_OU(self, iteration_id):
        """
        Create an OU for the course iteration.

        :param iteration_id: The ID of the course iteration

        :return: The ID of the OU
        """
        client = boto3.client("organizations")
        if self.org_info is None:
            self.create_aws_organization()
        try:
            response = client.create_organizational_unit(
                ParentId=self.org_info["Id"],
                Name=f"Course Iteration {iteration_id}",
            )
            self.logger.info(f"Created an OU for course iteration {iteration_id}.")
            self.iterationOU_info = response["OrganizationalUnit"]
            return response["OrganizationalUnit"]["Id"]
        except ClientError as error:
            self.fail = True
            self.logger.error(f"Something went wrong creating an OU for course iteration {iteration_id}.")
            self.logger.debug(f"{error}")
            self.logger.debug(f"{error.response}")

    def create_team_OU(self, team_id):
        """
        Create an OU for the team.

        :param team_id: The ID of the team

        :return: The ID of the OU
        """
        client = boto3.client("organizations")
        if self.iterationOU_info is None:
            self.create_course_iteration_OU(1)  # Needs to be figured out
        try:
            response = client.create_organizational_unit(
                ParentId=self.iterationOU_info["Id"],
                Name=f"{team_id}",
            )
            self.logger.info(f"Created an OU for team {team_id}.")
            return response["OrganizationalUnit"]["Id"]
        except ClientError as error:
            self.fail = True
            self.logger.error(f"Something went wrong creating an OU for team {team_id}.")
            self.logger.debug(f"{error}")
            self.logger.debug(f"{error.response}")
