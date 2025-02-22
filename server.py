from flask import Flask, request, Response
import boto3
import os

# ---------- Configuration ----------
ASU_ID = "1230415071"
S3_BUCKET_NAME = f"{ASU_ID}-in-bucket"
SIMPLEDB_DOMAIN = f"{ASU_ID}-simpleDB"
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
PORT = 8000
RESULTS = {}

# ---------- AWS Setup ----------
session = boto3.Session(
    aws_access_key_id = AWS_ACCESS_KEY_ID,
    aws_secret_access_key = AWS_SECRET_ACCESS_KEY,
    region_name = "us-east-1"
)
s3 = session.client('s3')
sdb = session.client('sdb')

# ---------- Flask App ----------
app = Flask(__name__)

def build_query_hash():
    response = sdb.select(
        SelectExpression=f"SELECT * FROM `{SIMPLEDB_DOMAIN}` LIMIT 1000"
    )
    print(len(response['Items']))
    for item in response['Items']:
        RESULTS[item['Name']] = item['Attributes'][0]['Value']
    
    print(sorted(RESULTS.keys()))

def upload_to_s3(file_obj, filename):
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=filename, Body=file_obj)

@app.route("/", methods=["POST"])
def predict_image():
    file = request.files['inputFile']
    filename = os.path.splitext(file.filename)[0]
    upload_to_s3(file, filename)
    return Response(f"{filename}:{RESULTS[filename]}", status=200, mimetype='text/plain')

# ---------- Run Server ----------
if __name__ == "__main__":
    build_query_hash()
    print(f"Server running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
