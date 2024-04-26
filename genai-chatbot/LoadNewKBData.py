import boto3
import os
from datetime import datetime

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock')

def lambda_handler(event, context):
    # Get the bucket name and file key from the event
    bucket_name = event['Records'][0]['s3']['bucket']['name']
    file_key = event['Records'][0]['s3']['object']['key']
    file_name = os.path.basename(file_key)

    # Check if the file is a PDF
    if file_key.endswith('.pdf'):
        # Get the current date and time
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d%H%M%S")

        # Construct the unique file name with timestamp
        unique_file_name = f"{os.path.splitext(file_name)[0]}_{timestamp}{os.path.splitext(file_name)[1]}"

        # Move the file to the knowledgebase dataset folder
        copy_source = {
            'Bucket': bucket_name,
            'Key': file_key
        }
        destination_bucket = os.environ['DESTINATION_BUCKET']
        destination_key_dataset = f'{os.environ['DESTINATION_PATH']}/dataset/{unique_file_name}'
        s3.copy_object(CopySource=copy_source, Bucket=destination_bucket, Key=destination_key_dataset)
        s3.delete_object(Bucket=bucket_name, Key=file_key)
    else:
        # Move the file to the processed data folder
        copy_source = {
            'Bucket': bucket_name,
            'Key': file_key
        }
        destination_bucket = os.environ['FAILED_BUCKET']
        destination_key_processed = f'{file_name}'
        s3.copy_object(CopySource=copy_source, Bucket=destination_bucket, Key=destination_key_processed)
        s3.delete_object(Bucket=bucket_name, Key=file_key)
        print('not a pdf')
