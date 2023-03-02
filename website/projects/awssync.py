"""Framework for synchronisation with Amazon Web Services (AWS)."""

import logging

import boto3

from botocore.exceptions import ClientError

from mailing_lists.models import MailingList


class AWSSync:
    """Synchronise with Amazon Web Services."""

    def __init__(self):
        """Create an AWSSync instance."""
        self.logger = logging.getLogger("django.aws")
        self.logger.setLevel(logging.DEBUG)
        self.org_info = None
        self.fail = False
        self.logger.info("Created AWSSync instance.")

    def button_pressed(self):
        """
        Print debug message to show that the button has been pressed.

        :return: True if function executes successfully
        """
        self.logger.info("Pressed button")
        self.logger.info(self.get_emails_with_teamids())
        return True

    def get_all_mailing_lists(self):
        """
        Get all mailing lists from the database.

        :return: List of mailing lists
        """
        mailing_lists = MailingList.objects.all()
        mailing_list_names = [ml.email_address for ml in mailing_lists]
        return mailing_list_names

    def get_emails_with_teamids(self):
        """
        Create a tuple with email and corresponding ID, where ID is the project slug and semester.

        :return: list of (email, teamid)
        """
        mailing_lists = MailingList.objects.all()
        email_id = []
        for ml in mailing_lists:
            for project in ml.projects.values("semester", "slug"):
                project_semester = project["semester"]
                project_slug = project["slug"]
                team_id = f"{project_slug}{project_semester}"
                email_id.append((ml.email_address, team_id))
        return email_id

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
