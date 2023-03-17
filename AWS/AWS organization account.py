import boto3

client = boto3.client('organizations',
                      aws_access_key_id='<AWS_ACCESS_KEY>',
                      aws_secret_access_key='<AWS_SECRET_KEY>',
                      region_name='<AWS_REGION>')
response = client.create_account(
    Email='member-account-email@example.com',
    AccountName='Member Account Name',
    RoleName='OrganizationAccountAccessRole',
    IamUserAccessToBilling='ALLOW',
    Tags=[
        {
            'Key': 'Tag1',
            'Value': 'Value1'
        },
        {
            'Key': 'Tag2',
            'Value': 'Value2'
        },
    ]
)
account_id = response['CreateAccountStatus']['AccountId']
client = boto3.client('organizations',
                      aws_access_key_id='<AWS_ACCESS_KEY>',
                      aws_secret_access_key='<AWS_SECRET_KEY>',
                      region_name='<AWS_REGION>',
                      account_id=account_id)

