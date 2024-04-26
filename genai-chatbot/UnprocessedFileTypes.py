import boto3
import json
import re
import os
from urllib.request import urlopen
import io
from fpdf import FPDF

s3_client = boto3.client('s3')

def create_and_upload_pdf(text, bucket_name, object_key):
    print("Creating PDF file")
    # Create a PDF from the input text
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=text)
    pdf_data = pdf.output(dest="S").encode("latin-1")
    
    print("PDF Created, going to move it now")
    # Upload the PDF to S3
    s3 = boto3.client('s3')
    s3.put_object(Bucket=bucket_name, Key=object_key, Body=pdf_data)
    
    return {
        'statusCode': 200,
        'body': f"PDF uploaded to S3 bucket '{bucket_name}' with key '{object_key}'"
    }

def bedrock_job(str_transcript):
    html_remover = re.compile('<[^>]*>')
    filler_remover = re.compile('(^| )([Uu]m|[Uu]h|[Ll]ike|[Mm]hm)[,]?')
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    generated_text = str_transcript.replace('```','')
    generated_text = re.sub(html_remover, '', str_transcript)
    generated_text = re.sub(filler_remover, '', str_transcript)
    global email_body
    print("In Bedrock Job")
    prompt =  """<Inputs>{$TRANSCRIPT}</Inputs>

                <Instructions Structure>
                1. Provide keywords and definitions from the transcript
                2. Summarize the agenda of the document
                3. Provide a bulleted summary of the call
                4. List any decisions made during the call
                5. List any action items assigned and to whom
                6. Provide any other valuable information from the transcript
                </Instructions Structure>
                
                <Instructions>
                You will be summarizing a document. Here are the steps to follow:
                
                1. Read the transcript provided below:
                <transcript>""" + generated_text + """</transcript>
                
                2. Identify important keywords mentioned in the transcript and provide definitions for them if possible. Write these under the heading:
                
                Keywords and Assumed Definitions:
                [List keywords and definitions here]
                
                3. In 10 sentences or less, summarize the agenda or main purpose of the document. Write this under the heading: 
                
                Agenda:
                [Summarize agenda here]
                
                4. Provide a bulleted summary of the key points and discussion from the call. Write this under the heading:
                
                Call Summary:
                [Bulleted summary here]
                
                5. List any business decisions or personal decisions that were explicitly made during the transcript. Write these under the heading:
                
                Decisions Made:
                [List decisions here]
                
                6. List any action items that were assigned to specific people, including who they were assigned to. Write these under the heading:
                
                Action Items:
                [List action items and who they were assigned to]
                
                7. Provide any other information from the transcript that you think is valuable or noteworthy. Write this under the heading:
                
                Other Valuable Information:
                [Other valuable information here]
                
                Please format your response clearly with proper headings and bullet points where applicable. Be concise but include all relevant details from the transcript.
                </Instructions>"""

    bedrock = boto3.client(service_name="bedrock-runtime")
    body = json.dumps({
        "max_tokens": 4096,
        "temperature": 0,
        "messages": [{"role": "user", "content": prompt}],
        "anthropic_version": "bedrock-2023-05-31"
    })
    
    response = bedrock.invoke_model(body=body, modelId=model_id)
    response_body = json.loads(response.get("body").read())
    email_body = (response_body.get('content', [])[0].get('text', ''))
    return email_body


def lambda_handler(event, context):
    #accept a file from s3 that was uploaded
    source_bucket_name = event['Records'][0]['s3']['bucket']['name']
    file_key = event['Records'][0]['s3']['object']['key']
    file_name = file_key.split('/')[-1]
    file_name_only = file_name.split('.')[0]
    
    # Download the file from S3
    obj = s3_client.get_object(Bucket=source_bucket_name, Key=file_key)
    file_content = obj['Body'].read()

    # Determine the file type
    file_type = file_key.split('.')[-1].lower()

    copy_source = {
        'Bucket': source_bucket_name,
        'Key': file_key
    }
    
    # Process the file based on its type
    if file_type in ['txt', 'csv']:
        print("Found txt or csv")
        content_text = file_content.decode('utf-8')
    else:
        print("Found unsupported file type")
        destination_key_processed = f"{file_name}"
        s3_client.copy_object(CopySource=copy_source, Bucket=os.environ['FAILED_BUCKET'], Key=destination_key_processed)
        s3_client.delete_object(Bucket=source_bucket_name, Key=file_key)
        return {
            'statusCode': 500,
            'body': f"Unsupported file"
        }
    
    #send to bedrock
    print("Sending Bedrock Job")
    summary = bedrock_job(content_text)
    print("Returned from Bedrock job")
    print("Entering PDF writer")
    target_key = f"{os.environ['DESTINATION_FOLDER']}/{file_name_only}.pdf"
    results = create_and_upload_pdf(summary, os.environ['DESTINATION_BUCKET'], target_key)
    
    if results['statusCode'] == 200:
        print("Moving original file to bucket")
        destination_key_processed = f"non-pdf-processed-originals/processed_{file_name}"
        s3_client.copy_object(CopySource=copy_source, Bucket=os.environ['DESTINATION_BUCKET'], Key=destination_key_processed)
        s3_client.delete_object(Bucket=source_bucket_name, Key=file_key)