"""Framework for synchronisation with Amazon Web Services (AWS)."""
from mailing_lists.models import MailingList
from django.db import models

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
        print(self.get_all_mailing_lists())
        print(self.get_all_managers())

        return True

    def get_all_mailing_lists(self):
        """
        Get all mailing lists from the database.
        """
        mailing_lists = MailingList.objects.all()
        mailing_list_names = [mailing_list.email_address for mailing_list in mailing_lists]
        print(mailing_list_names)
        return mailing_list_names


    

        
