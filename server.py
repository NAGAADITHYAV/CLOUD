from flask import Flask, request, Response
import boto3
import os
import asyncio
import threading
import atexit

# ---------- Configuration ----------
ASU_ID = "1230415071"
S3_BUCKET_NAME = f"{ASU_ID}-in-bucket"
SIMPLEDB_DOMAIN = f"{ASU_ID}-simpleDB"
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
PORT = 8000
RESULTS = {}
QWAIT = {}
server_running = True

# ---------- AWS Setup ----------
session = boto3.Session(
    aws_access_key_id = AWS_ACCESS_KEY_ID,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
    region_name = "us-east-1"
)
s3 = session.client('s3')
sdb = session.client('sdb')
sqs = session.client('sqs')
req_que = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-req-queue'
resp_que = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-resp-queue'

# ---------- Flask App ----------
app = Flask(__name__)

def fetch_messages_from_resp_queue():
    while server_running:
        response = sqs.receive_message(
            QueueUrl=resp_que,
            MaxNumberOfMessages=10,
            VisibilityTimeout= 5,
        )
        messages = response.get('Messages', [])
        if not messages:
            return None
        for message in messages:
            receipt_handle = message['ReceiptHandle']
            result = message['Body']
            filename, classification = result.split(':')
            RESULTS[filename] = f"{os.path.splittext(filename)[0]}:{classification}"
            QWAIT[filename].set()
            sqs.delete_message(
                QueueUrl = resp_que,
                 ReceiptHandle=receipt_handle)

def upload_to_s3(file_obj, filename):
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=filename, Body=file_obj)

def send_to_req_queue(filename):
    sqs.send_message(
        QueueUrl = req_que,
        MessageBody = filename)

@app.route("/", methods=["POST"])
async def predict_image():
    file = request.files['inputFile']
    upload_to_s3(file, file.filename)
    send_to_req_queue(file.filename)

    wait_event = asyncio.Event()
    QWAIT[file.filename] = wait_event

    await wait_event.wait()

    result = RESULTS.pop(file.filename, '' )
    QWAIT.pop(file.filename, '')


    return Response(result, status=200, mimetype='text/plain')

# ---------- Run Server ----------
fetch_thread = threading.Thread(target=fetch_messages_from_resp_queue, daemon=True)
fetch_thread.start()

def shutdown_event():
    global server_running
    server_running = False
    fetch_thread.join()

atexit.register(shutdown_event)

if __name__ == "__main__":
    import uvicorn
    atexit.register(shutdown_event)
    uvicorn.run(app, host="0.0.0.0", port=8000)
