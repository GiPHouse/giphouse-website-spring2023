"""Framework for synchronisation with Amazon Web Services (AWS)."""
from mailing_lists.models import MailingList

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

    def button_pressed(self):
        """
        Print debug message to show that the button has been pressed.

        :return: True if function executes successfully
        """
        print("Pressed button")
        print(self.get_emails_with_teamids())
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
        Create a tuple with email and corresponding teamID, where teamID is a concatenation of ID and semesterID.

        :param email_address: Email address of the team
        :return: (email, teamid)
        """
        mailing_lists = MailingList.objects.all()
        email_id = []
        for ml in mailing_lists:
            project = ml.projects.all()
            project_id = [(p.id, p.semester.id) for p in project]
            project_id = int(str(project_id[0][0]) + str(project_id[0][1]))
            email_id.append((ml.email_address, project_id))
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
