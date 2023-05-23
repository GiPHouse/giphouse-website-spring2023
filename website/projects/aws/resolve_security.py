import boto3

class YourClass:
    def add_and_remove_tags(self, account_id, destination_ou_id):
        """
        :param account_id:         The ID of the member account
        :param destination_ou_id:  The organization's destination OU ID
        :returns:                  True if the tags were added and removed successfully
    
        """
    
        client = boto3.client("organizations")

        client.tag_resource(ResourceId=account_id, Tags=[{"Key": "CourseIteration", "Value": "Temporary"}])
        
        root_id = client.list_roots()["Roots"][0]["Id"]
        client.move_account(
            AccountId=account_id, SourceParentId=root_id, DestinationParentId=destination_ou_id
        )

        client.untag_resource(ResourceId=account_id, TagKeys=["CourseIteration"])

        return True


