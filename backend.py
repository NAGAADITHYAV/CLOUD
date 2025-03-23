
from face_recognition import face_match
import boto3
import os

# ---------- Configuration ----------
ASU_ID = "1230415071"
S3_IN_BUCKET = f"{ASU_ID}-in-bucket"
S3_OUT_BUCKET = f"{ASU_ID}-in-bucket"
SIMPLEDB_DOMAIN = f"{ASU_ID}-simpleDB"
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
REQ_QUEUE = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-req-queue'
RESP_QUEUE = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-resp-queue'

# ---------- AWS Setup ----------
session = boto3.Session(
    aws_access_key_id = AWS_ACCESS_KEY_ID,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
    region_name = "us-east-1"
)
s3 = session.client('s3')
sqs = session.client('sqs')

def send_to_response_queue(result):
    sqs.send_message(QueueUrl=RESP_QUEUE, MessageBody=result)

def upload_results_to_s3(filename, result):
    s3.put_object(Bucket=S3_OUT_BUCKET, Key=filename, Body=result)
    
def download_image_from_s3(filename):
    s3.download_file(S3_IN_BUCKET, filename, filename)
    return filename


def perform_face_recognition(filename, image_path):
    return f"{filename}:{face_match(image_path)[0]}"

def fetch_request():
    response = sqs.receive_message(
        QueueUrl=REQ_QUEUE,
        MaxNumberOfMessages=1,
        VisibilityTimeout= 15,
    )
    messages = response.get('Messages', [])
    if not messages:
        return None
    message = messages[0]
    receipt_handle = message['ReceiptHandle']
    filename = message['Body']
    return filename, receipt_handle


def process_requests():
    while(True):
        request = fetch_request()
        if not request:
            continue
        filename, receipt_handle = request
        image_path = download_image_from_s3(filename)
        result = perform_face_recognition(filename, image_path)
        print('result',result)
        upload_results_to_s3(filename, result)
        send_to_response_queue(result)
        os.remove(image_path)
        sqs.delete_message(QueueUrl=REQ_QUEUE, ReceiptHandle=receipt_handle)

if __name__ == '__main__':
    process_requests()