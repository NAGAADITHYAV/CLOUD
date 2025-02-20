from flask import Flask, request, Response
import boto3
import os
from threading import Lock
from concurrent.futures import ThreadPoolExecutor

# ---------- Configuration ----------
ASU_ID = "1230415071"
S3_BUCKET_NAME = f"{ASU_ID}-in-bucket"
SIMPLEDB_DOMAIN = f"{ASU_ID}-simpleDB"
PORT = 8000
executor = ThreadPoolExecutor(max_workers=40)

# ---------- AWS Setup ----------
session = boto3.Session(
    aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name = "us-east-1"
)
s3 = session.client('s3')
sdb = session.client('sdb')

# ---------- Flask App ----------
app = Flask(__name__)

# Thread lock for concurrency
lock = Lock()


def upload_to_s3(file_obj, filename):
    """Upload the file to S3 bucket."""
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=filename, Body=file_obj)
    # print(f" Uploaded {filename} to S3 bucket {S3_BUCKET_NAME}")


def query_simpledb(filename):
    """Query SimpleDB for prediction result using filename."""
    response = sdb.select(
        SelectExpression=f"SELECT * FROM `{SIMPLEDB_DOMAIN}` WHERE itemName() = '{filename}'"
    )
    items = response.get('Items', [])
    if items:
        return items[0]['Attributes'][0]['Value']
    return "Unknown"

def upload_to_s3_async(file_obj, filename):
    """Upload the file to S3 asynchronously."""
    return executor.submit(upload_to_s3, file_obj, filename)

def query_simpledb_async(filename):
    """Query SimpleDB asynchronously."""
    return executor.submit(query_simpledb, filename)


@app.route("/", methods=["POST"])
def handle_request():
    """Handle incoming POST requests and return prediction results."""
    # try:
        # Check if 'inputFile' key exists in request
        # if 'inputFile' not in request.files:
            # return Response("⚠️ Missing 'inputFile' in request.", status=400)

    file = request.files['inputFile']
        
    filename = file.filename
    filename = os.path.splitext(filename)[0]

        # Concurrency lock to handle multiple requests
    with lock:
        # Step 1: Upload file to S3 asynchronously and wait for completion
        upload_future = upload_to_s3_async(file, filename)
        upload_future.result()  # Ensure upload completes before querying

        # Step 2: Query SimpleDB for result (asynchronously but awaited)
        prediction_future = executor.submit(query_simpledb, filename)
        prediction = prediction_future.result()

        # Step 3: Return result in plain text
    result = f"{filename}:{prediction}"
        # print(f"Prediction result sent: {result}")
    return Response(result, status=200, mimetype='text/plain')

    # except Exception as e:
    #     # print(f" Error: {str(e)}")
    #     return Response(f" Internal server error: {str(e)}", status=500)


# ---------- Run Server ----------
if __name__ == "__main__":
    print(f"Server running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
