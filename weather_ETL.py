from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timezone
import requests
import requests
import boto3
import json


#Archive the existing files so that we have the latest files on the landing zone
def archive_existing_landingzone_files():

    s3 = boto3.client('s3')
    bucket_name = 'weather-project-gaurav'
    landing_prefix = 'LandingZone/'
    archive_prefix = 'Archive/'

    # List objects under LandingZone/
    response = s3.list_objects_v2(Bucket=bucket_name, Prefix=landing_prefix)
    contents = response.get('Contents', [])

    for obj in contents:
        source_key = obj['Key']
        if source_key.endswith('/'):  # Skip folders
            continue

        # Maintain folder structure under archive/
        archive_key = source_key.replace(landing_prefix, archive_prefix, 1)

        # Copy to archive/
        s3.copy_object(
            Bucket=bucket_name,
            CopySource={'Bucket': bucket_name, 'Key': source_key},
            Key=archive_key
        )

        # Delete from LandingZone/
        s3.delete_object(Bucket=bucket_name, Key=source_key)

        print(f"Moved: {source_key} → {archive_key}")

#python function to store data on the S3 bucket
def run_openweather_etl_S3():
    now = datetime.now(timezone.utc)
    timestamp = int(now.timestamp())
    City = [
    "Delhi",
    "Mumbai",
    "Kolkata",
    "Bangalore",
    "Chennai",
    "Hyderabad",
    "Ahmedabad",
    "Surat",
    "Pune",
    "Jaipur"
    ]
    headers = {
    "Accept" :"application/json",
    "Content-Type" : "application/json" 
    }
    bucket_name = 'weather-project-gaurav'
    appid="2e642a52f72d3a3de63372bd15347196" #add your appidkey


    for city in City:
        print(city)
        api = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={appid}"
        response = requests.get(api, headers=headers)

        if response.status_code == 200:
            myData = response.json()
            s3 = boto3.client('s3')
            s3_key = f"LandingZone/{city}/{city}_weather_{now.year}_{now.month}_{now.day}_{timestamp}.json"

            s3.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=json.dumps(myData, indent=4),
                ContentType='application/json'
            )
            print(f"Uploaded: {s3_key}")
        else:
            print(f"Failed to fetch data for {city}: {response.status_code}")
           
default_args = {
    'owner': 'Gaurav',
    'start_date': datetime(2025, 6, 21),
    'retries': 1,
}

           
with DAG(
    dag_id='Weather_Data_Fetch',
    default_args=default_args,
    schedule_interval=None,
    catchup=False
) as dag:

    upload_task = PythonOperator(
        task_id='fetch_data_and_upload',
        python_callable=run_openweather_etl_S3
    )

    archive_task = PythonOperator(
    task_id='archive_old_files',
    python_callable=archive_existing_landingzone_files
    )

    archive_task >> upload_task


# DAG