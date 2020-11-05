from __future__ import print_function

import os
import json
import botocore.vendored.requests as requests
import boto3

print('Loading function')


def lambda_handler(event, context):
    #Read the json url key from the AWS SNS IP ranges notification.
    print("Received event: " + json.dumps(event, indent=2))
    url = event['url']
    print("From SNS url: " + url)
    
    #Load the json content from the url
    r = requests.get(url)
    data = json.loads(r.content)
    ipv4addresses = data["prefixes"]
    newIps = []

    # Iterate over the ip addresses and filter the required ip addresses. 
    # The region and service are supplied as environment variables to the lambda function
    for item in ipv4addresses:
        ip = item['ip_prefix']
        region = item['region']
        service = item['service']
        if region == os.environ['region'] and service == os.environ['service'] :
            print("ip:" + ip + "  Region:" + region + "  Service:" + service)
            newIps.append(ip)
            
    # Print the new IP ranges for S3 service
    for ip in newIps:
        print("New Ip: ", ip)
        
    # Load the previous/current IPs stored in the S3 text file.
    s3 = boto3.client('s3')
    bucket = os.environ['bucket']
    key = os.environ['key']
    print("bucket: "+ bucket + " File: "+key)
    data = s3.get_object(Bucket=bucket, Key=key)
    contents = data['Body'].read().decode('utf-8')
    currentIps = contents.split('\n')
    for ip in currentIps:
        print("Current Ip: ", ip)
    
    #check if exisitngs ips in s3 file and current ips are same.
    if set(newIps) == set(currentIps) :
        print("There are no changes in cloudfront IP Ranges")
    else:
        print("Cloudfront IP Ranges changed")
        newIpsLength = len(newIps)
        index = 0
        # Write the new IPS to a temporary file in Lambda. 
        with open('/tmp/awsips.txt', 'w') as data:
            for ip in newIps:
                if index == (newIpsLength - 1) :
                    data.write(ip)
                else:
                    data.write(ip+ "\n")
                index = index + 1
        
        # Upload the temporary file to S3
        with open('/tmp/awsips.txt', "rb") as f:
            s3.upload_fileobj(f, bucket, key)
        print("S3 File upload successful.")

        # Send SNS notification to notify about the IP address changes.
        publishToSNSTopic(newIps)

    return url


def publishToSNSTopic(cloudfrontips):
    message = {"foo": "bar"}
    arn = os.environ['snsarn']
    client = boto3.client('sns')
    response = client.publish(
        TargetArn=arn,
        Message=json.dumps({'default': json.dumps(message),
                            'sms': 'here a short version of the message',
                            'email': 'AWS Cloudfront IP Ranges Changed. New IPs are in "awscloudfrontips" s3 bucket. New Ips: '+ ', '.join(cloudfrontips)}),
        Subject='AWS Cloudfront IPs Changed',
        MessageStructure='json'
    )