import boto3

# Replace with your queue URL
QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-req-queue'
RESP_QUEUE_URL = 'https://sqs.us-east-1.amazonaws.com/340752817731/1230415071-resp-queue'

def check_sqs_queue(queue_url):
    sqs = boto3.client('sqs')

    try:
        response = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=['ApproximateNumberOfMessages']
        )
        
        num_messages = int(response['Attributes'].get('ApproximateNumberOfMessages', 0))
        print(f"Approximate number of messages in the queue: {num_messages}")

        return num_messages
    except Exception as e:
        print(f"Error checking queue: {e}")
        return None

if __name__ == "__main__":
    check_sqs_queue(RESP_QUEUE_URL)
