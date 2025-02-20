from flask import Flask, request, Response
import boto3
import os
from concurrent.futures import ThreadPoolExecutor

# ---------- Configuration ----------
ASU_ID = "1230415071"
S3_BUCKET_NAME = f"{ASU_ID}-in-bucket"
SIMPLEDB_DOMAIN = f"{ASU_ID}-simpleDB"
PORT = 8000
executor = ThreadPoolExecutor(max_workers=50)

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

def upload_to_s3(file_obj, filename):
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=filename, Body=file_obj)

def query_simpledb(filename):
    response = sdb.select(
        SelectExpression=f"SELECT * FROM `{SIMPLEDB_DOMAIN}` WHERE itemName() = '{filename}'"
    )
    return response['Items'][0]['Attributes'][0]['Value']


@app.route("/", methods=["POST"])
def handle_request():
    file = request.files['inputFile']
    filename = os.path.splitext(file.filename)[0]
    
    executor.submit(upload_to_s3, file, filename)
    prediction = query_simpledb(filename)

    result = f"{filename}:{prediction}"
    return Response(result, status=200, mimetype='text/plain')


# ---------- Run Server ----------
if __name__ == "__main__":
    print(f"Server running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
