import boto3
import os
# ---------- Configuration ----------
ASU_ID = '1230415071'
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
REQ_QUEUE = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-req-queue'
RESP_QUEUE = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-resp-queue'
MAX_INSTANCES = 15
AMI_ID = 'ami-03f5b9cd81d07aaef'
# ---------- AWS Setup ----------
session = boto3.Session(
    aws_access_key_id = AWS_ACCESS_KEY_ID,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
    region_name = "us-east-1"
)
sqs = session.client('sqs')
ec2 = session.resource('ec2')
input_bucket = f'{ASU_ID}-in-bucket'


def get_queue_length():
    attributes = sqs.get_queue_attributes(
        QueueUrl=REQ_QUEUE,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(attributes['Attributes'].get('ApproximateNumberOfMessages', '0'))

def autoscale_instances(queue_count):
    target_instance_count = min(MAX_INSTANCES, queue_count)
    if queue_count == 0:
        target_instance_count = 0
    existing_instances = list(ec2.instances.filter(
        Filters=[
            {'Name': 'tag:AppTier', 'Values': ['true']},
            {'Name': 'instance-state-name', 'Values': ['running', 'pending']}
        ]
    ))
    active_instance_count = len(existing_instances)
    if active_instance_count < target_instance_count:
        instances_needed = target_instance_count - active_instance_count
        for i in range(instances_needed):
            instance_number = active_instance_count + i + 1
            ec2.create_instances(
                ImageId=AMI_ID,
                MinCount=1,
                MaxCount=1,
                InstanceType='t2.micro',
                KeyName='Project1',
                IamInstanceProfile={'Name': 'IAM-DEV-ADI'},
                TagSpecifications=[{
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': f'app-tier-instance-{instance_number}'},
                        {'Key': 'AppTier', 'Value': 'true'}
                    ]
                }],
                UserData="""#!/bin/bash
                cd ~
                source myenv/bin/activate
                export AWS_SECRET_ACCESS_KEY={AWS_SECRET_ACCESS_KEY}
                export AWS_ACCESS_KEY_ID={AWS_ACCESS_KEY_ID}
                cd CLOUD/
                nohup python3 backend.py &
                """
            )
            print(f"Started app-tier-instance-{instance_number}.")
    elif active_instance_count > target_instance_count:
        instances_to_stop = [inst.id for inst in existing_instances[target_instance_count:]]
        ec2.instances.filter(InstanceIds=instances_to_stop).stop()
        print(f"Stopped {len(instances_to_stop)} excess App Tier instances.")

    

if __name__ == "__main__":
    while True:
        autoscale_instances(get_queue_length())