## setup Athena sql query 
Set Up Amazon Athena
Go to the Athena Console:

In the AWS Management Console, search for and select Athena.

Set a Query Result Location:

If prompted, specify an S3 bucket to store query results.

Create a Database:

In the Query Editor, run:

sql
CREATE DATABASE s3_access_logs_db;
This creates a database to hold your log tables.

Select the Database:

In the left panel, under Database, choose the database you just created.

4. Create a Table for S3 Access Logs
Run a CREATE TABLE Statement:

Use a statement like the following (adjust LOCATION to your logs bucket and prefix):

sql
CREATE EXTERNAL TABLE s3_access_logs_db.mybucket_logs (
  bucketowner STRING,
  bucket_name STRING,
  requestdatetime STRING,
  remoteip STRING,
  requester STRING,
  requestid STRING,
  operation STRING,
  key STRING,
  request_uri STRING,
  httpstatus STRING,
  errorcode STRING,
  bytessent BIGINT,
  objectsize BIGINT,
  totaltime STRING,
  turnaroundtime STRING,
  referrer STRING,
  useragent STRING,
  versionid STRING,
  hostid STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.RegexSerDe'
WITH SERDEPROPERTIES (
  'input.regex' = '([^ ]*) ([^ ]*) \\[(.*?)\\] ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*) (\"[^\"]*\") ([^ ]*) ([^ ]*) ([-]|[0-9]*) ([-]|[0-9]*) ([-]|[0-9]*) ([-]|[0-9]*) (\"[^\"]*\") (\"[^\"]*\") ([-]|[0-9]*)(?: ([^ ]*) ([^ ]*) ([^ ]*))?.*$'
)
LOCATION 's3://zerotrust-demo-logs-k4tvd3da/access-logs/';
Adjust the LOCATION to match your logs bucket and prefix.

Verify the Table:

In the left panel, under Tables, select your table.

Click Preview table to see sample data.

5. Query the Logs
Sample Query (Find All Uploads):

To find all uploads (PUT requests) from a specific IP and IAM role:

sql
SELECT *
FROM s3_access_logs_db.mybucket_logs
WHERE operation = 'REST.PUT.OBJECT'
  AND remoteip = '13.210.102.244'
  AND requester LIKE '%assumed-role/ROLE_NAME%';

To find all uploads (PUT requests) 
sql
SELECT *
FROM s3_access_logs_db.mybucket_logs
WHERE operation = 'REST.PUT.OBJECT'