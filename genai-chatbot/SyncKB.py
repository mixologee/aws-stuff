import json
import boto3
import uuid
import os

bedrock = boto3.client('bedrock-agent')

def lambda_handler(event, context):
    # Replace with your knowledge base ID
    knowledge_base_id = os.environ['KB_ID']

    # Replace with your data source ID
    data_source_id = os.environ['DATASOURCE_ID']

    # Generate a unique client token
    client_token = str(uuid.uuid4())

    # Optional description for the ingestion job
    description = 'Lambda function to run a sync job on the KB datasource.'

    try:
        # Create an ingestion job
        response = bedrock.start_ingestion_job(
            clientToken=client_token,
            dataSourceId=data_source_id,
            description=description,
            knowledgeBaseId=knowledge_base_id
        )

        # Check if the ingestion job was created successfully
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            ingestion_job_id = response['IngestionJobId']
            print(f'Ingestion job {ingestion_job_id} created successfully.')
        else:
            print(f'Failed to create ingestion job for data source {data_source_id}.')
        return {
            'statusCode': 200,
            'body': json.dumps('Lambda function executed successfully.')
        }
    except Exception as e:
        print(f'Error creating ingestion job: {e}')
        
    