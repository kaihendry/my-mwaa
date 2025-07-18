from datetime import datetime, timedelta
import json
import random

from airflow import DAG
from airflow.decorators import task
from airflow.providers.amazon.aws.hooks.sqs import SqsHook
from airflow.providers.amazon.aws.sensors.sqs import SqsSensor

QUEUE_NAME = "Airflow-Batch-Job-Queue"
RESULT_QUEUE_NAME = "Airflow-Batch-Result-Queue"
AWS_CONN_ID = "aws_default"




@task(task_id="send_completion_notification")
def send_completion_notification(result_data):
    """Send completion notification to the result queue"""
    print(f"🔍 DEBUG: send_completion_notification received: {result_data}")
    
    # Skip if no result data (no job was processed)
    if result_data is None:
        print("❌ No result data to send - skipping notification (no job was found in queue)")
        return None
    
    hook = SqsHook()
    
    # Get the result queue URL
    result_queue_url = hook.create_queue(queue_name=RESULT_QUEUE_NAME)["QueueUrl"]
    
    # Send completion message
    message_content = json.dumps(result_data)
    
    print(f"📤 Sending completion notification: {message_content}")
    
    hook.get_conn().send_message(
        QueueUrl=result_queue_url,
        MessageBody=message_content,
        MessageAttributes={
            "job_id": {
                "StringValue": result_data["job_id"],
                "DataType": "String"
            },
            "status": {
                "StringValue": result_data["status"],
                "DataType": "String"
            },
            "secret_word": {
                "StringValue": result_data["secret_word"],
                "DataType": "String"
            }
        }
    )
    
    print(f"✅ Sent completion notification for job_id: {result_data['job_id']}")
    print(f"🔐 Secret word included: {result_data['secret_word']}")
    return result_data


with DAG(
    dag_id="batch_job_consumer",
    schedule_interval=None,  # Manual trigger only
    start_date=datetime(2021, 1, 1),
    dagrun_timeout=timedelta(minutes=10),
    tags=["batch", "consumer"],
    catchup=False,
) as dag:
    
    # Monitor the job queue for new messages
    check_for_jobs = SqsSensor(
        task_id="check_for_batch_jobs",
        sqs_queue=QUEUE_NAME,
        max_messages=1,
        wait_time_seconds=20,
        timeout=60,  # 1 minute timeout
        poke_interval=10,  # Check every 10 seconds
        visibility_timeout=None,  # Use default visibility timeout
        message_filtering=None,
        message_filtering_match_values=None,
        message_filtering_config=None,
    )
    
    # Process the job - SqsSensor stores message in XCom under 'messages' key
    @task(task_id="process_job")
    def process_batch_job(**context):
        """Process the batch job"""
        # Get the message from XCom
        messages = context['task_instance'].xcom_pull(task_ids='check_for_batch_jobs', key='messages')
        
        print(f"🔍 DEBUG: XCom messages: {messages}")
        print(f"🔍 DEBUG: XCom messages type: {type(messages)}")
        
        if not messages or len(messages) == 0:
            print("❌ No job messages found in XCom")
            return None
        
        # Get the first message
        message = messages[0]
        job_message = message.get('Body') if isinstance(message, dict) else str(message)
        
        print(f"🔍 DEBUG: Received job_message type: {type(job_message)}")
        print(f"🔍 DEBUG: job_message value: {job_message}")
        
        # Check if we got a message
        if job_message is None:
            print("❌ No job message received from SQS sensor - queue might be empty")
            return None
        
        print(f"✅ Raw job message: {job_message}")
        
        # Parse the job message
        try:
            job_data = json.loads(job_message)
        except (json.JSONDecodeError, TypeError) as e:
            print(f"❌ Failed to parse job message as JSON: {e}")
            print(f"Message content: {job_message}")
            return None
        
        job_id = job_data.get("job_id")
        
        print(f"Starting batch job processing for job_id: {job_id}")
        print(f"Job data: {job_data}")
        
        # Simulate batch processing work
        input_value = job_data.get("data", {}).get("input_value", 0)
        processed_result = input_value * 2  # Simple processing
        
        print(f"Completed batch job processing for job_id: {job_id}")
        print(f"Input: {input_value}, Output: {processed_result}")
        
        # Generate a random secret word
        words = ["BANANA", "ELEPHANT", "PURPLE", "ROCKET", "WIZARD", "DIAMOND", "THUNDER", "GALAXY", "PHOENIX", "CRYSTAL"]
        secret_word = f"{random.choice(words)}_{random.randint(100, 999)}"
        
        print(f"🔐 GENERATED SECRET WORD: {secret_word}")
        
        # Return result data
        return {
            "job_id": job_id,
            "status": "completed",
            "processed_at": datetime.now().isoformat(),
            "input_value": input_value,
            "output_value": processed_result,
            "result": f"Successfully processed job {job_id}",
            "secret_word": secret_word
        }
    
    process_job = process_batch_job()
    
    # Send completion notification
    notify_completion = send_completion_notification(process_job)
    
    # Define task dependencies
    check_for_jobs >> process_job >> notify_completion