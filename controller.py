import boto3
import os
from time import sleep
# ---------- Configuration ----------
ASU_ID = '1230415071'
REQ_QUEUE = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-req-queue'
RESP_QUEUE = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-resp-queue'
MAX_INSTANCES = 15
AMI_ID = 'ami-0b6fbc8df0a65b120'
# ---------- AWS Setup ----------
session = boto3.Session(
    region_name = "us-east-1"
)
sqs = session.client('sqs')
ec2 = boto3.resource(
    'ec2',
    region_name="us-east-1"
)

def get_queue_length():
    attributes = sqs.get_queue_attributes(
        QueueUrl=REQ_QUEUE,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(attributes['Attributes'].get('ApproximateNumberOfMessages', '0'))

def fetch_instances():
    return list(ec2.instances.filter(
        Filters=[
            {'Name': 'tag:AppTier', 'Values': ['true']},
            {'Name': 'instance-state-name', 'Values': ['running', 'pending']}
            ]))

def create_instance(instance_number):
    print("launching instance:",instance_number)
    return ec2.create_instances(
        ImageId=AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        KeyName='project1',
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [
                {'Key': 'Name', 'Value': f'app-tier-instance-{instance_number}'},
                {'Key': 'AppTier', 'Value': 'true'}
            ]
        }],
        UserData="""#!/bin/bash
                cd /home/ubuntu/
                source /home/ubuntu/myenv/bin/activate
                cd /home/ubuntu/CLOUD
                nohup python3 backend.py > backend.log 2>&1 &
                """
    )

def autoscale_instances(queue_count):
    required_count = min(MAX_INSTANCES, queue_count)
    if queue_count==0 and required_count>0:
        required_count=0
    current_instances = fetch_instances()
    if len(current_instances) < required_count:
        more_required = required_count - len(current_instances)
        for i in range(more_required):
            create_instance(len(current_instances) + 1 + i)
            print("Launched insrtance sucessfully")
    elif len(current_instances) > required_count:
        instances_to_terminate = []
        for inst in current_instances[required_count:]:
            instances_to_terminate.append(inst.id)
        ec2.instances.filter(InstanceIds=instances_to_terminate).terminate()

if __name__ == "__main__":
    while True:
        autoscale_instances(get_queue_length())
        sleep(1)