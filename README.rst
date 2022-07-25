This is a very simple application that parses Wikipedia's change history pages based on requested title.
It returns date of the latest change for this page in ISO format.
Also, returns number of updates made during last 30 days.

All results are stored in JSON format.

As additional functionality, it's filtering number of updates made during last 30 days with 2+ changes
and calculates sum of these changes and a mean value for these changes.

Tools & services used:
AWS S3, CloudFormation, API Gateway, IAM, AWS Lambda, Serverless framework, Python 3.8, pandas

Prerequisites

For environment setup it's recommended to activate virtual environment:
    - Follow official guide for more details:
      https://docs.python.org/3/tutorial/venv.html

After virtualenv activation install all required dependencies:

    `pip install -t src/vendor -r aws_requirements.txt`


For the very basic local setup (without using AWS services, serverless deployment, etc.) we can just run it:

    `python src/handler.py --local True --title "Washington,_D.C."`

For using AWS services some additional setup is required for Serverless framework.
Details can be found in official guide:
    https://www.serverless.com/framework/docs/providers/aws/guide/credentials/

User/profile should be used with access to use CloudFormation, put items to S3 buckets, execute lambda functions, etc.

For local triggering AWS lambda function using serverless you can use the following:

    `sls invoke local --function wiki_handler --data '{"queryStringParameters":{"title": "Iceland"}}' --region eu-central-1 --aws-profile serverless`

    where `eu-central-1` should be valid for the region where environment has been created
    
    `serverless` (optional) name of profile for AWS user with valid credentials.

TO deploy everything to AWS use:

    `sls deploy --region eu-central-1 --aws-profile serverless`
    region and aws-profile options are optional (if not set via env variables, etc.)

After a global deployment to AWS it can be used via API calls with a query instring in the following format:
    `curl https://<api_hostname>/dev/parse-wiki?title=Spain`

Public JSON file with results can be found here:
    https://parsed-wiki.s3.eu-central-1.amazonaws.com/parsed_wiki.json
