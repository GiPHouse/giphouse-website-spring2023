from mailing_lists.models import MailingList

from projects.models import Project

"""Framework for synchronisation with Amazon Web Services (AWS)."""


class AWSSync:
    """Synchronise with Amazon Web Services."""

    def __init__(self):
        """Create an AWSSync instance."""
        print("Created AWSSync instance")

    def button_pressed(self):
        """
        Print debug message to show that the button has been pressed.

        :return: True if function executes successfully
        """
        print("Pressed button")
        temp_list = self.get_all_mailing_lists()
        print(temp_list)
        print(temp_list[0])
        return True

    def get_all_mailing_lists(self):
        """
        Get all mailing lists from the database.

        :return: List of mailing lists
        """
        mailing_lists = MailingList.objects.all()
        mailing_list_names = [ml.email_address for ml in mailing_lists]
        return mailing_list_names

    def get_email_with_teamid(self, email_address):
        """
        Create a tuple with email and corresponding teamID

        :param email_address: Email address of the team
        :return: (email, teamid)
        """
        project = Project.objects.get(email=email_address)
        return (email_address,project.github_team_id)


