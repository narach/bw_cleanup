import boto3
import time
import concurrent.futures
from aws_resource_fetcher import get_resources_by_tag, get_id_from_arn

session = boto3.Session(profile_name="idt-qa")
cloudwatch_client = session.client("cloudwatch")

tag_key = "tech:team_name"
tag_values = ["team_boss_wireless", "team_brmobile"]
resource_type = "cloudwatch:alarm"  # AWS ResourceTypeFilters format
aws_profile = "idt-qa"


def wait_for_alarm_deletion(alarm_name, max_attempts=30, wait_time=5):
    """
    Polls CloudWatch to confirm an alarm has been deleted.

    :param alarm_name: The name of the alarm to check.
    :param max_attempts: Max number of polling attempts before timeout.
    :param wait_time: Time (in seconds) to wait between checks.
    :return: True if alarm is deleted, False if timeout reached.
    """
    attempts = 0
    while attempts < max_attempts:
        try:
            response = cloudwatch_client.describe_alarms(AlarmNames=[alarm_name])
            if not response["MetricAlarms"]:
                print(f"✅ Alarm {alarm_name} is fully deleted.")
                return True  # Alarm is gone
        except cloudwatch_client.exceptions.ResourceNotFoundException:
            print(f"✅ Alarm {alarm_name} no longer exists.")
            return True  # AWS officially reports it as deleted
        except Exception as e:
            print(f"⚠️ Error checking alarm {alarm_name}: {e}")

        print(f"⏳ Waiting for alarm {alarm_name} to be deleted... ({attempts + 1}/{max_attempts})")
        time.sleep(wait_time)
        attempts += 1

    print(f"❌ Timeout: Alarm {alarm_name} was not deleted after {max_attempts * wait_time} seconds.")
    return False

def delete_cloudwatch_alarm(alarm_name):
    """Deletes a CloudWatch Alarm."""
    try:
        cloudwatch_client.delete_alarms(AlarmNames=[alarm_name])
        print(f"🚀 Requested deletion of CloudWatch Alarm: {alarm_name}")
        wait_for_alarm_deletion(alarm_name)  # Wait for full deletion
    except Exception as e:
        print(f"Error deleting CloudWatch Alarm {alarm_name}: {e}")

cw_alarms = get_resources_by_tag(tag_key, tag_values, resource_type, aws_profile)
# Print results
print(f"Total CloudWatch Alarms found: {len(cw_alarms)}")

# Delete alarms in parallel using ThreadPoolExecutor
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(delete_cloudwatch_alarm, get_id_from_arn(alarm)): alarm for alarm in cw_alarms}

    for future in concurrent.futures.as_completed(futures):
        try:
            future.result()  # Raise exceptions if any occurred
        except Exception as e:
            print(f"❌ Error in thread: {e}")
