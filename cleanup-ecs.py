import time
import boto3
from botocore.exceptions import ClientError

session = boto3.Session(profile_name="idt-qa")
ecs_client = session.client('ecs')
tagging_client = session.client("resourcegroupstaggingapi")

def get_task_definitions_to_delete():
    task_definitions = []
    try:
        response = tagging_client.get_resources(
            TagFilters=[{"Key": "to_delete", "Values": ["yes"]}],
            ResourceTypeFilters=["ecs:task-definition"]
        )

        # Extract ESC task definition names from ARN
        for resource in response["ResourceTagMappingList"]:
            task_def = resource["ResourceARN"].split("/")[-1]  # Corrected split method
            task_definitions.append(task_def)

    except ClientError as e:
        print(f"Error fetching tagged ECS task definitions buckets: {e}")

    return task_definitions

def deregister_task_definitions(task_defs):
    for task in task_defs:
        try:
            ecs_client.deregister_task_definition(taskDefinition=task)
        except ClientError as e:
            print(f"Unable to deregister task %s: {e}" % task)

def delete_task_definitions_in_batches(task_definitions, batch_size=10):
    """Deletes ECS task definitions in batches of 10 (AWS limit)."""
    for i in range(0, len(task_definitions), batch_size):
        batch = task_definitions[i:i+batch_size]  # Get batch of 10
        try:
            delete_response = ecs_client.delete_task_definitions(taskDefinitions=batch)
            print(f"Deleted task definitions batch: {batch}")
        except ClientError as e:
            print(f"Error deleting task definitions {batch}: {e}")



task_defs_to_delete = get_task_definitions_to_delete()
print("ECS tasks definitions to delete: %d" % len(task_defs_to_delete))
deregister_task_definitions(task_defs_to_delete)
delete_task_definitions_in_batches(task_defs_to_delete)
print("Task definitions should be deleted successfully")


