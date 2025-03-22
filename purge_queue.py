import boto3

# Replace with your AWS region and queue URL
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-req-queue'
RESP_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-resp-queue'

def purge_sqs_queue(queue_url):
    # Initialize SQS client
    sqs = boto3.client('sqs')
    
    try:
        # Purge the queue (deletes all messages)
        sqs.purge_queue(QueueUrl=queue_url)
        print(f"Queue {queue_url} purged successfully.")
    except Exception as e:
        print(f"Error purging queue: {e}")

if __name__ == "__main__":
    purge_sqs_queue(RESP_QUEUE_URL)