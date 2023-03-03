import logging

import boto3

from botocore.exceptions import ClientError


class AWSSync:
    """Synchronise with Amazon Web Services."""

    def __init__(self):
        """Create an AWSSync instance."""
        self.logger = logging.getLogger("django.aws")
        self.org_info = None
        self.fail = False
        self.logger.info("Created AWSSync instance.")
        self.client = boto3.client("organizations")

    def button_pressed(self):
        """
        Print debug message to show that the button has been pressed.

        :return: True if function executes successfully
        """
        self.logger.info("Pressed button")
        return True

    def create_aws_organization(self):
        """Create an AWS organization with the current user as the management account."""
        try:
            response = self.client.create_organization(FeatureSet="ALL")
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
        try:
            response = self.client.create_organizational_unit(
                ParentId=f'r-{self.org_info["Id"]}',
                Name=f"Course Iteration {iteration_id}",
            )
            self.logger.info(f"Created an OU for course iteration {iteration_id}.")
            return response["OrganizationalUnit"]["Id"]
        except ClientError as error:
            self.fail = True
            self.logger.error(f"Something went wrong creating an OU for course iteration {iteration_id}.")
            self.logger.debug(f"{error}")
            self.logger.debug(f"{error.response}")
