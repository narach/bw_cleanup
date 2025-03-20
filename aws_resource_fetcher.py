import boto3


def get_resources_by_tag(tag_key, tag_values, resource_type, aws_profile):
    session = boto3.Session(profile_name=aws_profile)
    tagging_client = session.client("resourcegroupstaggingapi")
    """
    Fetches all AWS resources of a specific type that have a given tag and tag_values list.
    Handles pagination to ensure all resources are retrieved.
    """
    res_arns = []
    next_token = None

    try:
        while True:
            # Fetch resources (handle pagination)
            response = tagging_client.get_resources(
                TagFilters=[{"Key": tag_key, "Values": tag_values}],
                ResourceTypeFilters=[resource_type],
                PaginationToken=next_token if next_token else ""
            )

            # Extract ARNs
            for resource in response.get("ResourceTagMappingList", []):
                resource_arn = resource["ResourceARN"]
                print(f"Found resource: {resource_arn}")
                res_arns.append(resource_arn)

            # Check if there are more pages
            next_token = response.get("PaginationToken")
            if not next_token:
                break  # Exit loop if no more pages

    except Exception as e:
        print(f"❌ Error fetching resources for {resource_type}: {e}")

    return res_arns


def get_id_from_arn(arn):
    """
    Extracts the resource ID from an AWS ARN, handling different ARN formats.

    :param arn: The AWS resource ARN (string)
    :return: Extracted resource ID (string)
    """
    # Split ARN into parts
    arn_parts = arn.split(":")

    if len(arn_parts) < 6:
        raise ValueError(f"Invalid ARN format: {arn}")

    service = arn_parts[2]  # Extract the AWS service name
    resource_part = arn_parts[5]  # The part containing the resource identifier

    # Handle common formats
    if service in ["ec2", "elasticloadbalancing", "rds", "dynamodb", "elasticache"]:
        return resource_part.split("/")[-1]  # Last part after "/"

    elif service in ["s3"]:
        return resource_part  # S3 ARN contains bucket name directly

    elif service in ["lambda", "sqs", "sns", "cloudwatch"]:
        return resource_part.split(":")[-1]  # Last part after ":"

    elif service in ["cloudfront"]:
        return resource_part.split("/")[-1]  # CloudFront has "distribution/<id>"

    else:
        raise ValueError(f"Unsupported ARN service: {service}")