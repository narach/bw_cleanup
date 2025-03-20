import boto3
import time
from aws_resource_fetcher import get_resources_by_tag,get_id_from_arn

session = boto3.Session(profile_name="idt-qa")
cloudfront_client = session.client("cloudfront")
tagging_client = session.client("resourcegroupstaggingapi")


def wait_for_cloudfront_disabled(distribution_id, max_attempts=30, wait_time=20):
    """Waits until the CloudFront distribution is fully disabled before deleting it."""
    attempts = 0
    while attempts < max_attempts:
        response = cloudfront_client.get_distribution(Id=distribution_id)
        status = response["Distribution"]["Status"]
        enabled = response["Distribution"]["DistributionConfig"]["Enabled"]

        print(f"Checking CloudFront distribution {distribution_id} status: {status}, Enabled: {enabled}")

        if not enabled and status == "Deployed":
            print(f"✅ CloudFront Distribution {distribution_id} is now disabled and ready for deletion.")
            return True

        time.sleep(wait_time)
        attempts += 1

    print(f"⚠️ Timeout: CloudFront distribution {distribution_id} is still not disabled after {max_attempts * wait_time} seconds.")
    return False

def disable_and_delete_cloudfront_distribution(distribution_id):
    """Disables and deletes a CloudFront distribution safely."""
    try:
        # Step 1: Get distribution config
        response = cloudfront_client.get_distribution_config(Id=distribution_id)
        etag = response["ETag"]
        config = response["DistributionConfig"]

        # Step 2: Disable distribution if not already disabled
        if config["Enabled"]:
            print(f"Disabling CloudFront Distribution {distribution_id}...")
            config["Enabled"] = False  # Modify config to disable

            # Step 3: Disable distribution
            cloudfront_client.update_distribution(
                Id=distribution_id, DistributionConfig=config, IfMatch=etag
            )

            # Step 4: Wait for CloudFront to fully disable
            if not wait_for_cloudfront_disabled(distribution_id):
                print(f"❌ Failed to disable CloudFront distribution {distribution_id}.")
                return

        # Step 5: Get new ETag and delete distribution
        etag = cloudfront_client.get_distribution_config(Id=distribution_id)["ETag"]
        cloudfront_client.delete_distribution(Id=distribution_id, IfMatch=etag)
        print(f"✅ Deleted CloudFront Distribution: {distribution_id}")

    except Exception as e:
        print(f"❌ Error deleting CloudFront Distribution {distribution_id}: {e}")

tag_key = "tech:team_name"
tag_values = ["team_boss_wireless", "team_brmobile"]
resource_type = "cloudfront:distribution"  # AWS ResourceTypeFilters format
aws_profile = "idt-qa"

cf_distrs = get_resources_by_tag(tag_key, tag_values, resource_type, aws_profile)
# Print results
print(f"Total CloudFront distributions found: {len(cf_distrs)}")
for cf in cf_distrs:
    cf_id = get_id_from_arn(cf)
    disable_and_delete_cloudfront_distribution(cf_id)
