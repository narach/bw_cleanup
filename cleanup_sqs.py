import boto3
import time
import concurrent.futures
from aws_resource_fetcher import get_resources_by_tag, get_id_from_arn

session = boto3.Session(profile_name="idt-qa")
sqs_client = session.client("sqs")

tag_key = "tech:team_name"
tag_values = ["team_boss_wireless", "team_brmobile"]
resource_type = "sqs:queue"  # AWS ResourceTypeFilters format
aws_profile = "idt-qa"

def get_sqs_queue_url(queue_arn):
    """
    Converts an SQS ARN to a Queue URL.

    Example:
    Input: arn:aws:sqs:us-east-1:123456789012:my-queue
    Output: https://sqs.us-east-1.amazonaws.com/123456789012/my-queue
    """
    arn_parts = queue_arn.split(":")
    if len(arn_parts) < 6 or arn_parts[2] != "sqs":
        raise ValueError(f"Invalid SQS ARN: {queue_arn}")

    region = arn_parts[3]
    account_id = arn_parts[4]
    queue_name = arn_parts[5]
    return f"https://sqs.{region}.amazonaws.com/{account_id}/{queue_name}"


def wait_for_sqs_deletion(queue_url, max_attempts=30, wait_time=5):
    """
    Waits until an SQS queue is fully deleted by polling get_queue_attributes().

    :param queue_url: The full SQS Queue URL.
    :param max_attempts: Maximum number of times to check before timeout.
    :param wait_time: Time (seconds) to wait between checks.
    :return: True if queue is deleted, False if timeout.
    """
    attempts = 0
    while attempts < max_attempts:
        try:
            sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["QueueArn"])
            print(f"⏳ Queue {queue_url} still exists. Waiting for deletion... ({attempts + 1}/{max_attempts})")
        except sqs_client.exceptions.QueueDoesNotExist:
            print(f"✅ Queue {queue_url} successfully deleted.")
            return True
        except Exception as e:
            print(f"⚠️ Error checking queue deletion status: {e}")
            return False

        time.sleep(wait_time)
        attempts += 1

    print(f"❌ Timeout: Queue {queue_url} was not deleted after {max_attempts * wait_time} seconds.")
    return False


def delete_sqs_queue(queue_arn):
    """
    Deletes an SQS queue and waits until it is fully removed.

    :param queue_url: The full SQS Queue URL.
    """
    try:
        queue_url = get_sqs_queue_url(queue_arn)
        sqs_client.delete_queue(QueueUrl=queue_url)
        print(f"🚀 Requested deletion of SQS Queue: {queue_url}")
        wait_for_sqs_deletion(queue_url)  # Wait until it's fully deleted
    except Exception as e:
        print(f"❌ Error deleting SQS Queue {queue_arn}: {e}")


sqs_queues = get_resources_by_tag(tag_key, tag_values, resource_type, aws_profile)
# Print results
print(f"Total SQS queues found: {len(sqs_queues)}")


# Delete alarms in parallel using ThreadPoolExecutor
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(delete_sqs_queue, get_id_from_arn(que)): que for que in sqs_queues}

    for future in concurrent.futures.as_completed(futures):
        try:
            future.result()  # Raise exceptions if any occurred
        except Exception as e:
            print(f"❌ Error in thread: {e}")