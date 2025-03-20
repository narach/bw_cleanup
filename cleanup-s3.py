import time
import boto3
from botocore.exceptions import ClientError

session = boto3.Session(profile_name="idt-qa")
# ec2_client = session.client("ec2")

# response = ec2_client.describe_instances()
# print(response)

s3_client = session.client('s3')
tagging_client = session.client("resourcegroupstaggingapi")
s3_buckets = s3_client.list_buckets()['Buckets']

def get_buckets_to_delete():
    buckets_to_delete = []
    try:
        response = tagging_client.get_resources(
            TagFilters=[{"Key": "to_delete", "Values": ["yes"]}],
            ResourceTypeFilters=["s3"]
        )

        # Extract S3 bucket names from ARN
        for resource in response["ResourceTagMappingList"]:
            bucket_name = resource["ResourceARN"].split(":::")[-1]
            print(f"Bucket marked for deletion: {bucket_name}")
            buckets_to_delete.append(bucket_name)

    except ClientError as e:
        print(f"Error fetching tagged S3 buckets: {e}")

    return buckets_to_delete

def empty_bucket(bucket_name):
    """Fully empty an S3 bucket, including all versions and delete markers, handling pagination correctly."""
    print(f"Emptying bucket: {bucket_name}")

    try:
        # Step 1: Delete all non-versioned objects
        while True:
            objects = s3_client.list_objects_v2(Bucket=bucket_name)
            if "Contents" not in objects:
                break  # No more non-versioned objects

            object_keys = [{"Key": obj["Key"]} for obj in objects["Contents"]]
            s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": object_keys})
            print(f"Deleted {len(object_keys)} non-versioned objects from {bucket_name}")

        # Step 2: Handle versioned objects & delete markers
        versioning_status = s3_client.get_bucket_versioning(Bucket=bucket_name)
        if versioning_status.get("Status") in ["Enabled", "Suspended"]:
            print(f"Bucket {bucket_name} has versioning {versioning_status.get('Status')}. Deleting all object versions and delete markers.")

            # Force pagination handling
            while True:
                versions = s3_client.list_object_versions(Bucket=bucket_name)

                # Collect delete keys
                delete_keys = []
                if "Versions" in versions:
                    delete_keys.extend([{"Key": v["Key"], "VersionId": v["VersionId"]} for v in versions["Versions"]])
                if "DeleteMarkers" in versions:
                    delete_keys.extend([{"Key": dm["Key"], "VersionId": dm["VersionId"]} for dm in versions["DeleteMarkers"]])

                if delete_keys:
                    s3_client.delete_objects(Bucket=bucket_name, Delete={"Objects": delete_keys})
                    print(f"Deleted {len(delete_keys)} object versions/delete markers from {bucket_name}")

                # Ensure we get the next batch
                if "NextKeyMarker" in versions and "NextVersionIdMarker" in versions:
                    next_key_marker = versions["NextKeyMarker"]
                    next_version_marker = versions["NextVersionIdMarker"]
                else:
                    break  # Exit loop when all versions are deleted

                # Small delay to prevent AWS throttling
                time.sleep(0.5)

    except ClientError as e:
        print(f"Error emptying bucket {bucket_name}: {e}")

def delete_bucket(bucket_name):
    try:
        s3_client.delete_bucket(Bucket=bucket_name)
        print(f"Deleted bucket: {bucket_name}")
    except ClientError as e:
        print(f"Error deleting bucket {bucket_name}: {e}")


buckets_to_delete = get_buckets_to_delete()
print(buckets_to_delete)

for bucket in buckets_to_delete:
    empty_bucket(bucket)
    delete_bucket(bucket)


print("S3 cleanup completed!") 