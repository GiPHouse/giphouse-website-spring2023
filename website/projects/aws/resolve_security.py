import time
import boto3

class SecurityResolving:
    def __init__(self):
        self.ACCOUNT_REQUEST_INTERVAL_SECONDS = 5
        self.ACCOUNT_REQUEST_MAX_ATTEMPTS = 10

    def pipeline_create_account(self, sync_data):
        """
        Create a single new AWS member account in the organization of the API caller.

        The status of the member account request is repeatedly checked based on the class' attributes:
            self.ACCOUNT_REQUEST_INTERVAL_SECONDS: thread sleeping time before each status check
            self.ACCOUNT_REQUEST_MAX_ATTEMPTS:     maximum number of times to thread sleep and check

        :param sync_data: The SyncData object containing account details.
        :returns: (True, account_id) on success and otherwise (False, failure_reason).
        """
        client = boto3.client("organizations")

        try:
            response_create = client.create_account(
                Email=sync_data.project_email,
                AccountName=sync_data.project_slug,
                IamUserAccessToBilling="DENY",
                Tags=[
                    {"Key": "project_slug", "Value": sync_data.project_slug},
                    {"Key": "project_semester", "Value": sync_data.project_semester},
                    {"Key": "course_iteration_tag", "Value": "no-rights"},
                ],
            )
        except client.exceptions.ClientError as error:
            print(error)
            return False, "CLIENTERROR_CREATE_ACCOUNT"

        request_id = response_create["CreateAccountStatus"]["Id"]
        for _ in range(1, self.ACCOUNT_REQUEST_MAX_ATTEMPTS + 1):
            time.sleep(self.ACCOUNT_REQUEST_INTERVAL_SECONDS)

            try:
                response_status = client.describe_create_account_status(CreateAccountRequestId=request_id)
            except client.exceptions.ClientError as error:
                print(error)
                return False, "CLIENTERROR_DESCRIBE_CREATE_ACCOUNT_STATUS"

            request_state = response_status["CreateAccountStatus"]["State"]
            if request_state == "FAILED":
                return False, response_status["CreateAccountStatus"]["FailureReason"]
            elif request_state == "SUCCEEDED":
                return True, response_status["CreateAccountStatus"]["AccountId"]

        return False, "STILL_IN_PROGRESS"

    def pipeline_create_and_move_accounts(self, new_member_accounts, root_id, destination_ou_id):
        """
        Create multiple accounts in the organization of the API caller and move them from the root to a destination OU.

        :param new_member_accounts: List of SyncData objects.
        :param root_id: The organization's root ID.
        :param destination_ou_id: The organization's destination OU ID.
        :returns: True if all new member accounts were created and moved successfully, False otherwise.
        """
        client = boto3.client("organizations")
        overall_success = True

        for new_member in new_member_accounts:
            success, response = self.pipeline_create_account(new_member)
            if success:
                account_id = response
                try:
                    client.move_account(
                        AccountId=account_id, SourceParentId=root_id, DestinationParentId=destination_ou_id
                    )
                    client.untag_resource(ResourceId=account_id, TagKeys=["course_iteration_tag"])
                except client.exceptions.ClientError as error:
                    print(error)
                    overall_success = False
            else:
                failure_reason = response
                print(failure_reason)
                overall_success = False

        return overall_success
