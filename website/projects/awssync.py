"""Framework for synchronisation with Amazon Web Services (AWS)."""
from __future__ import annotations

import json
import logging
import time

import boto3

from botocore.exceptions import ClientError
from botocore.exceptions import NoCredentialsError

from courses.models import Semester

from mailing_lists.models import MailingList

from projects.models import Project


class SyncData:
    """Structure for AWS giphouse sync data."""

    def __init__(self, project_email, project_slug, project_semester):
        """Create SyncData instance."""
        self.project_email = project_email
        self.project_slug = project_slug
        self.project_semester = project_semester

    def __eq__(self, other):
        """Overload equals for SyncData type."""
        if not isinstance(other, SyncData):
            raise TypeError("Must compare to object of type SyncData")
        return (
            self.project_email == other.project_email
            and self.project_slug == other.project_slug
            and self.project_semester == other.project_semester
        )

    def __repr__(self):
        """Overload to string function for SyncData type."""
        return f"SyncData('{self.project_email}', '{self.project_slug}', '{self.project_semester}')"


class Iteration:
    """Datatype for AWS data in the Course iteration OU."""

    def __init__(self, name, ou_id, members: list[SyncData]):
        """Initialize Iteration object."""
        self.name = name
        self.ou_id = ou_id
        self.members = members

    def __repr__(self):
        """Overload to string function for Iteration datatype."""
        return f"Iteration('{self.name}', '{self.ou_id}', {self.members})"

    def __eq__(self, other: Iteration) -> bool:
        """Overload equals operator for Iteration objects."""
        if not isinstance(other, Iteration):
            raise TypeError("Must compare to object of type Iteration")
        return self.name == other.name and self.ou_id == other.ou_id and self.members == other.members


class AWSTree:
    """Tree structure for AWS data."""

    def __init__(self, name, ou_id, iterations: list[Iteration]):
        """Initialize AWSTree object."""
        self.name = name
        self.ou_id = ou_id
        self.iterations = iterations

    def __repr__(self):
        """Overload to string function for AWSTree object."""
        return f"AWSTree('{self.name}', '{self.ou_id}', {self.iterations})"

    def __eq__(self, other: AWSTree) -> bool:
        """Overload equals operator for AWSTree objects."""
        if not isinstance(other, AWSTree):
            raise TypeError("Must compare to object of type AWSTree")
        return self.name == other.name and self.ou_id == other.ou_id and self.iterations == other.iterations

    def awstree_to_syncdata_list(self):
        """Convert AWSTree to list of SyncData elements."""
        awslist = []

        for iteration in self.iterations:
            for member in iteration.members:
                awslist.append(member)

        return awslist


class AWSSync:
    """Synchronise with Amazon Web Services."""

    def __init__(self):
        """Create an AWSSync instance."""
        self.ACCOUNT_REQUEST_INTERVAL_SECONDS = 5
        self.ACCOUNT_REQUEST_MAX_ATTEMPTS = 3

        self.logger = logging.getLogger("django.aws")
        self.logger.setLevel(logging.DEBUG)
        self.org_info = None
        self.iterationOU_info = None
        self.fail = False
        self.required_aws_actions = [
            # "organizations:AcceptHandshake",
            "organizations:AttachPolicy",
            # "organizations:CancelHandshake",
            # "organizations:CloseAccount",
            "organizations:CreateAccount",
            # "organizations:CreateGovCloudAccount",
            "organizations:CreateOrganization",
            "organizations:CreateOrganizationalUnit",
            "organizations:CreatePolicy",
            # "organizations:DeclineHandshake",
            # "organizations:DeleteOrganization",
            "organizations:DeleteOrganizationalUnit",
            "organizations:DeletePolicy",
            "organizations:DeleteResourcePolicy",
            # "organizations:DeregisterDelegatedAdministrator",
            "organizations:DescribeAccount",
            "organizations:DescribeCreateAccountStatus",
            "organizations:DescribeEffectivePolicy",
            # "organizations:DescribeHandshake",
            "organizations:DescribeOrganization",
            "organizations:DescribeOrganizationalUnit",
            "organizations:DescribePolicy",
            "organizations:DescribeResourcePolicy",
            "organizations:DetachPolicy",
            # "organizations:DisableAWSServiceAccess",
            "organizations:DisablePolicyType",
            # "organizations:EnableAWSServiceAccess",
            # "organizations:EnableAllFeatures",
            "organizations:EnablePolicyType",
            # "organizations:InviteAccountToOrganization",
            # "organizations:LeaveOrganization",
            # "organizations:ListAWSServiceAccessForOrganization",
            "organizations:ListAccounts",
            "organizations:ListAccountsForParent",
            "organizations:ListChildren",
            "organizations:ListCreateAccountStatus",
            # "organizations:ListDelegatedAdministrators",
            # "organizations:ListDelegatedServicesForAccount",
            # "organizations:ListHandshakesForAccount",
            # "organizations:ListHandshakesForOrganization",
            "organizations:ListOrganizationalUnitsForParent",
            "organizations:ListParents",
            "organizations:ListPolicies",
            "organizations:ListPoliciesForTarget",
            "organizations:ListRoots",
            "organizations:ListTagsForResource",
            "organizations:ListTargetsForPolicy",
            "organizations:MoveAccount",
            "organizations:PutResourcePolicy",
            # "organizations:RegisterDelegatedAdministrator",
            # "organizations:RemoveAccountFromOrganization",
            "organizations:TagResource",
            "organizations:UntagResource",
            "organizations:UpdateOrganizationalUnit",
            "organizations:UpdatePolicy",
        ]
        self.logger.info("Created AWSSync instance.")

    def button_pressed(self):
        """
        Print debug message to show that the button has been pressed.

        :return: True if function executes successfully
        """
        self.logger.info("Pressed button")
        self.logger.info(self.get_emails_with_teamids())
        self.logger.debug(f"Pipeline check result: {self.pipeline_preconditions()}")

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
        Create a list of SyncData struct containing email, slug and semester.

        Slug and semester combined are together an uniqueness constraint.

        :return: list of SyncData structs with email, slug and semester
        """
        email_ids = []

        for project in (
            Project.objects.filter(mailinglist__isnull=False)
            .filter(semester=Semester.objects.get_or_create_current_semester())
            .values("slug", "semester", "mailinglist")
        ):
            project_slug = project["slug"]
            project_semester = str(Semester.objects.get(pk=project["semester"]))
            project_email = MailingList.objects.get(pk=project["mailinglist"]).email_address

            sync_data = SyncData(project_email, project_slug, project_semester)
            email_ids.append(sync_data)
        return email_ids

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
            self.logger.info("No organization info found. Creating an AWS organization.")
            self.fail = True
        else:
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

    def generate_aws_sync_list(self, giphouse_data: list[SyncData], aws_data: list[SyncData]):
        """
        Generate the list of users that are registered on the GiPhouse website, but are not yet invited for AWS.

        This includes their ID and email address, to be able to put users in the correct AWS organization later.
        """
        sync_list = [x for x in giphouse_data if x not in aws_data]
        return sync_list

    def create_scp_policy(self, policy_name, policy_description, policy_content):
        """
        Create an SCP policy.

        :param policy_name: The policy name.
        :param policy_description: The policy description.
        :param policy_content: The policy configuration as a dictionary.
        The policy is automatically converted to JSON format, including escaped quotation marks.
        :return: Details of newly created policy as a dict on success and NoneType object otherwise.
        """
        client = boto3.client("organizations")
        try:
            response = client.create_policy(
                Content=json.dumps(policy_content),
                Description=policy_description,
                Name=policy_name,
                Type="SERVICE_CONTROL_POLICY",
            )
        except ClientError as error:
            self.fail = True
            self.logger.error("Something went wrong creating an SCP policy.")
            self.logger.error(error)
        else:
            return response["Policy"]

    def attach_scp_policy(self, policy_id, target_id):
        """
        Attaches an SCP policy to a target (root, OU, or member account).

        :param policy_id: The ID of the policy to be attached.
        :param target_id: The ID of the target root, OU, or member account.
        """
        client = boto3.client("organizations")
        try:
            client.attach_policy(PolicyId=policy_id, TargetId=target_id)
        except ClientError as error:
            self.fail = True
            self.logger.error("Something went wrong attaching an SCP policy to a target.")
            self.logger.debug(f"{error}")
            self.logger.debug(f"{error.response}")

    def check_aws_api_connection(self):
        """
        Check whether boto3 can connect to AWS API with current credentials.

        :returns: First tuple element always exists and indicates success.
                  Second tuple element is contains information about the entity
                  who made the successful API call and None otherwise.
        """
        client_sts = boto3.client("sts")
        try:
            caller_identity_info = client_sts.get_caller_identity()
        except (NoCredentialsError, ClientError) as error:
            self.logger.info("Establishing AWS API connection failed.")
            self.logger.debug(error)
            return False, None
        else:
            self.logger.info("Establishing AWS API connection succeeded.")

        return True, caller_identity_info

    def check_iam_policy(self, iam_user_arn, desired_actions):
        """
        Check for the specified IAM user ARN whether the actions in list \
        desired_actions are allowed according to its IAM policy.

        :param iam_user_arn: ARN of the IAM user being checked.
        :param iam_actions: List of AWS API actions to check.
        :returns: True iff all actions in desired_actions are allowed.
        """
        client_iam = boto3.client("iam")

        try:
            response = client_iam.simulate_principal_policy(PolicySourceArn=iam_user_arn, ActionNames=desired_actions)
        except ClientError as error:
            self.logger.info("AWS API actions check failed.")
            self.logger.debug(error)
            return False

        success = True
        for evaluation_result in response["EvaluationResults"]:
            action_name = evaluation_result["EvalActionName"]
            if evaluation_result["EvalDecision"] != "allowed":
                self.logger.debug(f"The AWS API action {action_name} is denied for IAM user {iam_user_arn}.")
                success = False

        if success:
            self.logger.info("AWS API actions check succeeded.")

        return success

    def check_organization_existence(self):
        """
        Check whether an AWS organization exists for the AWS API caller's account.

        :returns: First tuple element always exists and indicates success.
                  Second tuple element is describes properties of the organization and None otherwise.
        """
        client_organizations = boto3.client("organizations")

        try:
            response_org = client_organizations.describe_organization()
        except ClientError as error:
            self.logger.info("AWS organization existence check failed.")
            self.logger.debug(error)
            return False, None
        else:
            self.logger.info("AWS organization existence check succeeded.")

        return True, response_org["Organization"]

    def check_is_management_account(self, api_caller_info, organization_info):
        """
        Check whether caller of AWS API has organization's management account ID.

        :returns: True iff the current organization's management account ID equals the AWS API caller's account ID.
        """
        management_account_id = organization_info["MasterAccountId"]
        api_caller_account_id = api_caller_info["Account"]
        is_management_account = management_account_id == api_caller_account_id

        if is_management_account:
            self.logger.info("Management account check succeeded.")
        else:
            self.logger.info("Management account check failed.")
            self.logger.debug(f"The organization's management account ID is: '{management_account_id}'.")
            self.logger.debug(f"The AWS API caller account ID is:            '{api_caller_account_id}'.")

        return is_management_account

    def check_scp_enabled(self, organization_info):
        """
        Check whether the SCP policy type is an enabled feature for the AWS organization.

        :returns: True iff the SCP policy type feature is enabled for the organization.
        """
        scp_is_enabled = False
        for policy in organization_info["AvailablePolicyTypes"]:
            if policy["Type"] == "SERVICE_CONTROL_POLICY" and policy["Status"] == "ENABLED":
                scp_is_enabled = True
                break

        if not scp_is_enabled:
            self.logger.info("The SCP policy type is disabled for the organization.")
            self.logger.debug(organization_info["AvailablePolicyTypes"])
        else:
            self.logger.info("Organization SCP policy status check succeeded.")

        return scp_is_enabled

    def pipeline_preconditions(self):
        """
        Check all crucial pipeline preconditions.

        1. Locatable boto3 credentials and successful AWS API connection
        2. Check allowed AWS API actions based on IAM policy of caller
        3. Existing organization for AWS API caller
        4. AWS API caller acts under same account ID as organization's management account ID
        5. SCP policy type feature enabled for organization

        :return: True iff all pipeline preconditions are met.
        """
        check_api_connection, api_caller_info = self.check_aws_api_connection()
        if not check_api_connection:
            return False

        check_api_actions = self.check_iam_policy(api_caller_info["Arn"], self.required_aws_actions)
        if not check_api_actions:
            return False

        check_org_existence, organization_info = self.check_organization_existence()
        if not check_org_existence:
            return False

        check_acc_management = self.check_is_management_account(api_caller_info, organization_info)
        if not check_acc_management:
            return False

        check_scp_enabled = self.check_scp_enabled(organization_info)
        if not check_scp_enabled:
            return False

        return True

    def pipeline_create_scp_policy(self):
        """
        Creates an SCP policy to be attached to the organizational unit of the current semester.

        :return: Details of newly created policy as a dict on success and NoneType object otherwise.
        """
        # attach dummy policy (deny all)
        policy_name = "DenyAll"
        policy_description = "Deny all access."
        policy_content = {"Version": "2012-10-17", "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]}
        return self.create_scp_policy(policy_name, policy_description, policy_content)

    def pipeline_policy(self, OU):
        """
        Creates an SCP policy and attaches it to the organizational unit of the current semester.

        :param OU: organizational unit of the current semester.
        :return: True iff policy was successfully created and attached.
        """
        self.logger.info("Creating SCP policy to be attached to organizational unit for current semester.")
        policy = self.pipeline_create_scp_policy()
        if policy is None:
            self.logger.info("Failed to create SCP policy.")
            return False
        self.logger.info("Successfully created SCP policy.")

        self.logger.info("Attaching SCP policy to organizational unit for current semester.")
        self.attach_scp_policy(policy["PolicySummary"]["Id"], OU["Id"])
        if self.fail:
            self.logger.info("Failed to attach SCP policy.")
            return False
        self.logger.info("Successfully attached SCP policy.")
        return True

    def pipeline_create_account(self, email, username):
        """
        Create a single new AWS member account in the organization of the API caller.

        The status of the member account request is repeatedly checked based on the class' attributes:
            self.ACCOUNT_REQUEST_INTERVAL_SECONDS: thread sleeping time before each status check
            self.ACCOUNT_REQUEST_MAX_ATTEMPTS:     maximum number of times to thread sleep and check

        :param email:    The e-mail address of the new member account.
        :param username: The username of the new member account.
        :returns:        (True, account_id) on success and otherwise (False, failure_reason).
        """
        client = boto3.client("organizations")

        # Request new member account.
        try:
            response_create = client.create_account(Email=email, AccountName=username, IamUserAccessToBilling="DENY")
        except ClientError as error:
            self.logger.debug(error)
            return False, "CLIENTERROR_CREATE_ACCOUNT"

        # Repeatedly check status of new member account request.
        request_id = response_create["CreateAccountStatus"]["Id"]
        for _ in range(1, self.ACCOUNT_REQUEST_MAX_ATTEMPTS + 1):
            time.sleep(self.ACCOUNT_REQUEST_INTERVAL_SECONDS)

            try:
                response_status = client.describe_create_account_status(CreateAccountRequestId=request_id)
            except ClientError as error:
                self.logger.debug(error)
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

        :param new_member_accounts: List of 2-tuples with the e-mail address and username respectively, as strings.
        :param root_id:             The organization's root ID.
        :param destination_ou_id:   The organization's destination OU ID.
        :returns:                   True iff **all** new member accounts were created and moved successfully.
        """
        client = boto3.client("organizations")
        overall_success = True

        for email, name in new_member_accounts:
            success, response = self.pipeline_create_account(email, name)
            if success:
                account_id = response
                try:
                    client.move_account(
                        AccountId=account_id, SourceParentId=root_id, DestinationParentId=destination_ou_id
                    )
                except ClientError as error:
                    self.logger.debug(error)
                    overall_success = False
            else:
                failure_reason = response
                self.logger.debug(failure_reason)
                overall_success = False

        return overall_success

    def pipeline_update_current_course_iteration_ou(self, aws_tree):
        """
        Update the AWS tree with the new course iteration OU's.

        :param aws_tree:               The AWS tree to be checked.
        :returns:                      True, iteration_id on success and otherwise False, failure_reason.
        """

        is_current_iteration, iteration_id = self.check_current_ou(aws_tree)

        if not is_current_iteration:
            iteration_id = self.create_course_iteration_OU(iteration_id)

        if not self.fail:
            return True, iteration_id
        else:
            return False, "ITERATION_OU_CREATION_FAILED"

    def pipeline(self):
        """
        Single pipeline that integrates all buildings blocks for the AWS integration process.

        :return: True iff all pipeline stages successfully executed.
        """
        # Check preconditions.
        if not self.pipeline_preconditions():
            return False

        # TODO: Get synchronization data.
        # TODO: Check/create course iteration OU.
        course_iteration_ou_id = None

        aws_tree = None
        current_course_iteration_exists, response = self.pipeline_update_current_course_iteration_ou(aws_tree)
        if not current_course_iteration_exists:
            failure_reason = response
            self.logger.debug(failure_reason)
            return False

        course_iteration_ou_id = response

        # Attach SCP policy to course iteration OU.
        if not self.pipeline_policy(course_iteration_ou_id):
            return False

        # Create new member accounts and move to course iteration OU.
        # Temporary dummy variables (dependent on other in-progress tasks).
        member_accounts = [("alice@example.com", "alice"), ("bob@example.com", "bob")]
        client = boto3.client("organizations")
        root_id = client.list_roots()["Roots"][0]["Id"]

        if not self.pipeline_create_and_move_accounts(member_accounts, root_id, course_iteration_ou_id):
            return False

        return True

    # TODO: check if this function is really needed

    def check_for_double_member_email(self, aws_list: list[SyncData], sync_list: list[SyncData]):
        """Check if no users are assigned to multiple projects."""
        sync_emails = [x.project_email for x in sync_list]
        aws_emails = [x.project_email for x in aws_list]

        duplicates = [email for email in sync_emails if email in aws_emails]

        for duplicate in duplicates:
            error = f"Email address {duplicate} is already in the list of members in AWS"
            self.logger.info("An email clash occured while syncing.")
            self.logger.debug(error)

        if duplicates != []:
            return True
        return False

    def check_current_ou_exists(self, AWSdata: AWSTree):
        """
        Check if the the OU (organizational unit) for the current semester already exists in AWS.

        Get data in tree structure (dictionary) defined in the function that retrieves the AWS data
        """
        current = Semester.objects.get_or_create_current_semester()

        for iteration in AWSdata.iterations:
            if current == iteration.name:
                return (True, iteration.ou_id)

        return (False, None)

    # TODO: Do we want to check for this?
    def check_members_in_correct_iteration(self, AWSdata: AWSTree):
        """Check if the data from the member tag matches the semester OU it is in."""
        incorrect_emails = []
        for iteration in AWSdata.iterations:
            for member in iteration.members:
                if member.project_semester != iteration.name:
                    incorrect_emails.append(member.project_email)

        if incorrect_emails != []:
            return (False, incorrect_emails)

        return (True, None)

    def check_double_iteration_names(self, AWSdata: AWSTree):
        """Check if there are multiple OU's with the same name in AWS."""
        names = [iteration.name for iteration in AWSdata.iterations]
        doubles = []

        for name in names:
            if names.count(name) != 1 and name not in doubles:
                doubles.append(name)

        if doubles != []:
            return (True, doubles)
        return (False, None)

    def extract_aws_setup(self, parent_ou_id):
        """
        Give a list of all the children of the parent OU.

        :param parent_ou_id: The ID of the parent OU.
        """
        client = boto3.client("organizations")
        try:
            response = client.list_organizational_units_for_parent(ParentId=parent_ou_id)
            aws_tree = AWSTree("root", parent_ou_id, [])
            for iteration in response["OrganizationalUnits"]:
                ou_id = iteration["Id"]
                ou_name = iteration["Name"]
                response = client.list_accounts_for_parent(ParentId=ou_id)
                children = response["Accounts"]
                syncData = []
                for child in children:
                    account_id = child["Id"]
                    account_email = child["Email"]
                    response = client.list_tags_for_resource(ResourceId=account_id)
                    tags = response["Tags"]
                    merged_tags = {d["Key"]: d["Value"] for d in tags}
                    self.logger.debug(merged_tags)
                    if all(key in merged_tags for key in ["project_slug", "project_semester"]):
                        syncData.append(
                            SyncData(account_email, merged_tags["project_slug"], merged_tags["project_semester"])
                        )
                    else:
                        self.logger.error(
                            "Could not find project_slug or project_semester tag for account with ID: " + account_id
                        )
                        self.fail = True

                aws_tree.iterations.append(Iteration(ou_name, ou_id, syncData))
            return aws_tree
        except ClientError as error:
            self.fail = True
            self.logger.error("Something went wrong extracting the AWS setup.")
            self.logger.debug(f"{error}")
            self.logger.debug(f"{error.response}")
