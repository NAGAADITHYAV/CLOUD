
import boto3
import os
import asyncio
import threading
from fastapi import FastAPI, UploadFile, File
from starlette.responses import PlainTextResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware


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
REQ_QUEUE = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-req-queue'
RESP_QUEUE = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-resp-queue'

# ---------- AWS Setup ----------
session = boto3.Session(
    aws_access_key_id = AWS_ACCESS_KEY_ID,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
    region_name = "us-east-1"
)
s3 = session.client('s3')
sdb = session.client('sdb')
sqs = session.client('sqs')


# ---------- Flask App ----------
app = FastAPI()
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

def fetch_messages_from_resp_queue():
    print(server_running)
    while server_running:
        print(server_running)
        response = sqs.receive_message(
            QueueUrl=RESP_QUEUE,
            MaxNumberOfMessages=10,
            VisibilityTimeout= 5,
        )
        messages = response.get('Messages', [])
        if not messages:
            continue
        for message in messages:
            receipt_handle = message['ReceiptHandle']
            result = message['Body']
            filename, classification = result.split(':')
            RESULTS[filename] = f"{os.path.splitext(filename)[0]}:{classification}"
            if filename in QWAIT:
               QWAIT[filename].set()
            sqs.delete_message(QueueUrl = RESP_QUEUE, ReceiptHandle=receipt_handle)

def upload_to_s3(file_obj, filename):
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=filename, Body=file_obj)

def send_to_req_queue(filename):
    sqs.send_message(
        QueueUrl = REQ_QUEUE,
        MessageBody = filename)

@app.post("/", response_class=PlainTextResponse)
async def predict_image(inputFile: UploadFile = File(...)):
    file_content = await inputFile.read()
    filename = inputFile.filename 
    upload_to_s3(file_content, filename)
    send_to_req_queue(filename)

    wait_event = asyncio.Event()
    QWAIT[filename] = wait_event

    await wait_event.wait()

    result = RESULTS.pop(filename, '' )
    QWAIT.pop(filename, '')

    return result

# ---------- Run Server ----------
fetch_thread = threading.Thread(target=fetch_messages_from_resp_queue, daemon=True)
fetch_thread.start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
