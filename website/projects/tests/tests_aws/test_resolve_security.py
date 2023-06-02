import unittest
from unittest.mock import MagicMock
from projects.aws.resolve_security import ResolveSecurity

class ResolveSecurityTestCase(unittest.TestCase):

    def setUp(self):
        self.your_class = ResolveSecurity()
        self.new_member_accounts = [...]  #List of SyncData objects
        self.root_id = "your_root_id"
        self.destination_ou_id = "your_destination_ou_id"

    def test_pipeline_create_and_move_accounts(self):

        self.your_class.pipeline_create_account = MagicMock(return_value=(True, "account_id"))
        client_mock = MagicMock()
        client_mock.move_account = MagicMock()
        client_mock.untag_resource = MagicMock()
        self.your_class.boto3.client = MagicMock(return_value=client_mock)

        result = self.your_class.pipeline_create_and_move_accounts(
            self.new_member_accounts, self.root_id, self.destination_ou_id
        )

        self.assertTrue(result)  #Overall success should be True
        self.assertEqual(self.your_class.pipeline_create_account.call_count, len(self.new_member_accounts))
        client_mock.move_account.assert_called_with(
            AccountId="account_id", SourceParentId=self.root_id, DestinationParentId=self.destination_ou_id
        )
        client_mock.untag_resource.assert_called_with(ResourceId="account_id", TagKeys=["course_iteration_tag"])

if __name__ == "__main__":
    unittest.main()
