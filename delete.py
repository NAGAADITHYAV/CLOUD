import boto3

# AWS Credentials (if not using default profile)
import os
aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')

session = boto3.Session(
    aws_access_key_id = aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name="us-east-1"
)

sdb = session.client('sdb')
domain_name = "1230415071-simpleDB"  # Your domain name

def delete_all_items(domain):
    print(f" Fetching items from domain: {domain}")
    select_expression = f"SELECT itemName() FROM `{domain}`"
    next_token = None
    total_deleted = 0

    while True:
      if next_token:
        response = sdb.select(SelectExpression=select_expression, NextToken=next_token)
      else:
        response = sdb.select(SelectExpression=select_expression)

      items = response.get('Items', [])
      for item in items:
        item_name = item['Name']
        sdb.delete_attributes(DomainName=domain, ItemName=item_name)
        total_deleted += 1
        print(f" Deleted item: {item_name}")

      next_token = response.get('NextToken')
      if not next_token:
        break

    print(f"Completed deletion. Total items deleted: {total_deleted}")

# Run the deletion
delete_all_items(domain_name)
