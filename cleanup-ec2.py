import boto3
import time

session = boto3.Session(profile_name="idt-qa")
ec2_session = session.client("ec2")
tagging_client = session.client("resourcegroupstaggingapi")
ec2_client = session.client("ec2")

rt_instance = "ec2:instance"
rt_network_interface = "ec2:network-interface"
rt_security_group = "ec2:security-group"
rt_volume = "ec2:volume"

tag = "to_delete"
value = "yes"

def get_ec2_resources_by_tag(tag_key, tag_values, resource_type):
    res_arns = []
    try:
        response = tagging_client.get_resources(
            TagFilters=[{"Key": tag_key, "Values": tag_values}],
            ResourceTypeFilters=[resource_type]
        )

        # Extract ARNs
        for resource in response["ResourceTagMappingList"]:
            ec2_arn = resource["ResourceARN"]
            print(f"EC2 Resource marked for deletion: {ec2_arn}")
            res_arns.append(ec2_arn)

    except Exception as e:
        print(f"Error fetching tagged EC2 resources: {e}")

    return res_arns


def get_id_from_arn(arn):
    return arn.split("/")[-1]


def check_instance_exists(instance_id):
    """Checks if an EC2 instance exists before attempting to terminate it."""
    try:
        response = ec2_client.describe_instances(InstanceIds=[instance_id])

        # If Reservations list is not empty, instance exists
        if response["Reservations"]:
            print(f"Instance {instance_id} exists.")
            return True
        else:
            print(f"Instance {instance_id} does NOT exist.")
            return False

    except ec2_client.exceptions.ClientError as e:
        if "InvalidInstanceID.NotFound" in str(e):
            print(f"Instance {instance_id} does not exist or is already terminated.")
            return False
        else:
            print(f"Error checking instance {instance_id}: {e}")
            return False


def delete_instances(instances_to_delete):
    for instance_arn in instances_to_delete:
        try:
            instance_id = get_id_from_arn(instance_arn)
            if check_instance_exists(instance_id):
                terminate_instance_and_wait(instance_id)
        except Exception as e:
            print(f"Error terminating EC2 instance {instance_arn}: {e}")

def terminate_instance_and_wait(instance_id):
    try:
        # Step 1: Terminate the instance
        print(f"Terminating EC2 instance: {instance_id}")
        ec2_client.terminate_instances(InstanceIds=[instance_id])
        # Step 2: Wait for instance to be fully terminated
        print(f"Waiting for EC2 instance {instance_id} to be terminated...")
        waiter = ec2_client.get_waiter("instance_terminated")
        waiter.wait(InstanceIds=[instance_id])
        print(f"EC2 instance {instance_id} is now terminated.")
    except Exception as e:
        print(f"Error terminating EC2 instance {instance_id}: {e}")


def wait_for_network_interface_deletion(network_interface_id, max_attempts=30, wait_time=5):
    attempts = 0
    while attempts < max_attempts:
        try:
            response = ec2_client.describe_network_interfaces(NetworkInterfaceIds=[network_interface_id])
            status = response["NetworkInterfaces"][0]["Status"]
            print(f"Waiting for ENI {network_interface_id} deletion. Current status: {status}")

            if status == "deleted":
                print(f"Network Interface {network_interface_id} deleted successfully.")
                return True
        except ec2_client.exceptions.ClientError as e:
            if "InvalidNetworkInterfaceID.NotFound" in str(e):
                print(f"Network Interface {network_interface_id} is fully deleted.")
                return True  # ENI does not exist anymore
            else:
                print(f"Error checking ENI {network_interface_id}: {e}")

        time.sleep(wait_time)
        attempts += 1

    print(f"Network Interface {network_interface_id} did not delete in time.")
    return False


def wait_for_security_group_deletion(security_group_id, max_attempts=30, wait_time=5):
    """Waits until the security group is fully deleted."""
    attempts = 0
    while attempts < max_attempts:
        try:
            response = ec2_client.describe_security_groups(GroupIds=[security_group_id])
            print(f"Waiting for Security Group {security_group_id} deletion. Still exists.")
        except ec2_client.exceptions.ClientError as e:
            if "InvalidGroup.NotFound" in str(e):
                print(f"Security Group {security_group_id} deleted successfully.")
                return True  # SG does not exist anymore
            else:
                print(f"Error checking Security Group {security_group_id}: {e}")

        time.sleep(wait_time)
        attempts += 1

    print(f"Security Group {security_group_id} did not delete in time.")
    return False


def wait_for_volume_deletion(volume_id):
    """Waits until the volume is fully deleted using AWS waiters."""
    print(f"Waiting for Volume {volume_id} to be deleted...")
    waiter = ec2_client.get_waiter("volume_deleted")
    waiter.wait(VolumeIds=[volume_id])
    print(f"Volume {volume_id} deleted successfully.")


def delete_network_interfaces(interfaces):
    for ni in interfaces:
        try:
            ni_id = get_id_from_arn(ni)
            wait_for_network_interface_deletion(ni_id)
        except Exception as e:
            print(f"Error: {e}")


def delete_security_groups(s_groups):
    for sg in s_groups:
        try:
            sg_id = get_id_from_arn(sg)
            wait_for_security_group_deletion(sg_id)
        except Exception as e:
            print(f"Error: {e}")


def delete_volumes(vols):
    for vol in vols:
        try:
            vol_id = get_id_from_arn(vol)
            wait_for_volume_deletion(vol_id)
        except Exception as e:
            print(f"Error: {e}")


# Get ARNs for EC2 resources types which should be deleted.
instances = get_ec2_resources_by_tag("tech:team_name", ["team_boss_wireless"], rt_instance)
# print(f"BW EC2 instances to delete: {instances}")
network_interfaces = get_ec2_resources_by_tag("tech:team_name", ["team_boss_wireless"], rt_network_interface)
# print(f"Network Interfaces to delete: {network_interfaces}")
volumes = get_ec2_resources_by_tag("tech:team_name", ["team_boss_wireless"], rt_volume)
# print(f"Volumes to delete: {volumes}")
security_groups = get_ec2_resources_by_tag("tech:team_name", ["team_boss_wireless"], rt_security_group)
# print(f"Security Groups to delete: {security_groups}")

# Delete EC2 resources in proper order(EC2 Instances -> Network Interfaces -> Security Groups -> Volumes)
delete_instances(instances)
delete_network_interfaces(network_interfaces)
delete_security_groups(security_groups)
delete_volumes(volumes)