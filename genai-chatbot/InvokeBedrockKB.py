import os
import boto3


boto3_session = boto3.session.Session()
region = boto3_session.region_name

# create a boto3 bedrock client
bedrock_agent_runtime_client = boto3.client('bedrock-agent-runtime')

# get knowledge base id from environment variable
kb_id = os.environ.get("KNOWLEDGE_BASE_ID")

# declare model id for calling RetrieveAndGenerate API
model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
model_arn = f'arn:aws:bedrock:{region}::foundation-model/{model_id}'


def retrieveAndGenerate(input, kbId, model_arn, sessionId):
    print(input, kbId, model_arn)
    if sessionId != "":
        #print("We have a session id!")
        return bedrock_agent_runtime_client.retrieve_and_generate(
            input={
                'text': input
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kbId,
                    'modelArn': model_arn,
                    'retrievalConfiguration': {
                    	'vectorSearchConfiguration': {
                    		'numberOfResults': 50,
                    		'overrideSearchType': 'HYBRID'
                    	}
                    }
                }
            },
            sessionId=sessionId
        )
    else:
        #print("No session id")
        return bedrock_agent_runtime_client.retrieve_and_generate(
            input={
                'text': input
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': kbId,
                    'modelArn': model_arn,
                    'retrievalConfiguration': {
                    	'vectorSearchConfiguration': {
                    		'numberOfResults': 50,
                    		'overrideSearchType': 'HYBRID'
                    	}
                    }
                }
            }
        )


def lambda_handler(event, context):
    print(event)
    query = event["question"]
    session_id = event["sessionId"]
    response = retrieveAndGenerate(query, kb_id, model_arn, session_id)
    #print(response)
    generated_text = response['output']['text']
    session_id = response['sessionId']

    return {
        'statusCode': 200,
        'body': {"question": query.strip(), "answer": generated_text.strip(), "sessionId": session_id}
    }