# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from datetime import datetime, timedelta
import json

from airflow import DAG
from airflow.decorators import task
from airflow.providers.amazon.aws.hooks.sqs import SqsHook
from airflow.providers.amazon.aws.operators.sqs import SqsPublishOperator
from airflow.providers.amazon.aws.sensors.sqs import SqsSensor

QUEUE_NAME = "Airflow-Batch-Job-Queue"
RESULT_QUEUE_NAME = "Airflow-Batch-Result-Queue"
AWS_CONN_ID = "aws_default"


@task(task_id="create_job_queue")
def create_job_queue_fn():
    """Create the job queue for batch processing"""
    hook = SqsHook()
    result = hook.create_queue(queue_name=QUEUE_NAME)
    return result["QueueUrl"]


@task(task_id="create_result_queue")
def create_result_queue_fn():
    """Create the result queue for completion notifications"""
    hook = SqsHook()
    result = hook.create_queue(queue_name=RESULT_QUEUE_NAME)
    return result["QueueUrl"]


with DAG(
    dag_id="batch_job_producer",
    schedule_interval=None,
    start_date=datetime(2021, 1, 1),
    dagrun_timeout=timedelta(minutes=60),
    tags=["batch", "producer"],
    catchup=False,
) as dag:
    # Create both queues
    create_job_queue = create_job_queue_fn()
    create_result_queue = create_result_queue_fn()

    # Submit a batch job with unique job ID
    submit_job = SqsPublishOperator(
        task_id="submit_batch_job",
        sqs_queue=create_job_queue,
        message_content=json.dumps({
            "job_id": "{{ run_id }}",
            "task_instance": "{{ task_instance }}",
            "execution_date": "{{ execution_date }}",
            "job_type": "batch_processing",
            "data": {"input_value": 42, "description": "Sample batch job"}
        }),
        message_attributes=None,
        delay_seconds=0,
    )

    # Wait for completion notification from the consumer
    wait_for_completion = SqsSensor(
        task_id="wait_for_job_completion",
        sqs_queue=create_result_queue,
        max_messages=1,
        wait_time_seconds=20,
        timeout=300,  # 5 minutes timeout
        poke_interval=60,  # Check every minute
        mode="reschedule",  # Free up worker between checks
        visibility_timeout=None,
        message_filtering=None,  # Remove filtering for now
        message_filtering_match_values=None,
        message_filtering_config=None,
    )

    # Echo the completion response
    @task(task_id="echo_completion_response")
    def echo_completion_response():
        """Echo the completion response to verify alignment"""
        # Get the message from the sensor output
        completion_message = wait_for_completion.output
        if completion_message:
            print(f"🎉 RECEIVED COMPLETION MESSAGE: {completion_message}")
            try:
                completion_data = json.loads(completion_message)
                secret_word = completion_data.get("secret_word", "NOT_FOUND")
                print(f"🔐 SECRET WORD FROM CONSUMER: {secret_word}")
                print(f"📊 PROCESSING RESULT: {completion_data.get('result', 'NO_RESULT')}")
                print(f"✅ PRODUCER-CONSUMER ALIGNMENT VERIFIED!")
                return completion_data
            except (json.JSONDecodeError, TypeError) as e:
                print(f"❌ Failed to parse completion message: {e}")
                return None
        else:
            print("❌ No completion message received")
            return None
    
    echo_response = echo_completion_response()

    # Define task dependencies
    [create_job_queue, create_result_queue] >> submit_job >> wait_for_completion >> echo_response
