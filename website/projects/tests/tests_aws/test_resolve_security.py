import unittest
from unittest.mock import MagicMock, patch 
import boto3
from projects.aws.resolve_security import MyClass


class MyClassTestCase(unittest.TestCase):
    @patch('boto3.client')
    def test_add_and_remove_tags(self, mock_client):
        client_mock = MagicMock()
        client_mock.tag_resource.return_value = {}
        client_mock.list_roots.return_value = {"Roots": [{"Id": "root_id"}]}
        client_mock.move_account.return_value = {}
        client_mock.untag_resource.return_value = {}

        mock_client.return_value = client_mock

        my_object = MyClass()

        account_id = "your_account_id"
        destination_ou_id = "your_destination_ou_id"

        result = my_object.add_and_remove_tags(account_id, destination_ou_id)

        client_mock.tag_resource.assert_called_once_with(
            ResourceId=account_id, Tags=[{"Key": "CourseIteration", "Value": "Temporary"}]
        )
        client_mock.list_roots.assert_called_once_with()
        client_mock.move_account.assert_called_once_with(
            AccountId=account_id, SourceParentId="root_id", DestinationParentId=destination_ou_id
        )
        client_mock.untag_resource.assert_called_once_with(
            ResourceId=account_id, TagKeys=["CourseIteration"]
        )

        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()