import time
import boto3
from botocore.exceptions import ClientError

session = boto3.Session(profile_name="idt-qa")
elb_client = session.client('elbv2')
tagging_client = session.client("resourcegroupstaggingapi")

def get_lb_to_delete():
    """
    Fetches all Load Balancer V2 (ALB/NLB) ARNs that have a specific tag.
    """
    load_balancers = []
    
    try:
        response = tagging_client.get_resources(
            TagFilters=[{"Key": "to_delete", "Values": ["yes"]}],
            ResourceTypeFilters=["elasticloadbalancing:loadbalancer"]
        )

        # Extract Load Balancer ARNs
        for resource in response["ResourceTagMappingList"]:
            lb_arn = resource["ResourceARN"]
            print(f"Load Balancer marked for deletion: {lb_arn}")
            load_balancers.append(lb_arn)

    except Exception as e:
        print(f"Error fetching tagged Load Balancers: {e}")

    return load_balancers


def is_load_balancer_safe_to_delete(load_balancer_arn):
    """
    Checks if a load balancer has no listeners and is not associated with any target groups.
    Returns True if safe to delete, otherwise False.
    """
    try:
        # 1. Check if the Load Balancer has Listeners
        listeners_response = elb_client.describe_listeners(LoadBalancerArn=load_balancer_arn)
        if listeners_response.get('Listeners'):
            print(f"Load Balancer {load_balancer_arn} still has active listeners.")
            return False  # Not safe to delete

        # 2. Check if the Load Balancer is Attached to Target Groups
        target_groups_response = elb_client.describe_target_groups(LoadBalancerArn=load_balancer_arn)
        for target_group in target_groups_response.get('TargetGroups', []):
            target_group_arn = target_group['TargetGroupArn']

            # 3. Check if the Target Group has any Active Targets
            target_health_response = elb_client.describe_target_health(TargetGroupArn=target_group_arn)
            if target_health_response.get('TargetHealthDescriptions'):
                print(f"Target Group {target_group_arn} still has registered targets.")
                return False  # Not safe to delete

        print(f"Load Balancer {load_balancer_arn} is safe to delete.")
        return True

    except Exception as e:
        print(f"Error checking dependencies for load balancer {load_balancer_arn}: {e}")
        return False
    
def delete_all_listeners(load_balancer_arn):
    """Deletes all listeners attached to a given Load Balancer."""
    try:
        listeners_response = elb_client.describe_listeners(LoadBalancerArn=load_balancer_arn)
        for listener in listeners_response.get('Listeners', []):
            listener_arn = listener["ListenerArn"]
            elb_client.delete_listener(ListenerArn=listener_arn)
            print(f"Deleted Listener: {listener_arn}")

    except Exception as e:
        print(f"Error deleting listeners for Load Balancer {load_balancer_arn}: {e}")

def delete_target_groups(target_group_arns):
    """Deletes the given Target Groups."""
    for tg_arn in target_group_arns:
        try:
            elb_client.delete_target_group(TargetGroupArn=tg_arn)
            print(f"Deleted Target Group: {tg_arn}")
        except Exception as e:
            print(f"Error deleting Target Group {tg_arn}: {e}")

def delete_lbs(bw_lbs):
    for lb in bw_lbs:
        can_delete = is_load_balancer_safe_to_delete(lb)
        print("Load balancer: %s can be deleted: %r" % (lb, can_delete))
        if can_delete == False:
            delete_all_listeners(lb)
        elb_client.delete_load_balancer(LoadBalancerArn=lb)
        print(f"Deleted Load Balancer: {lb}")

        # Delete target groups attached to LB:
        # Get Target Groups attached to the Load Balancer
        target_groups_response = elb_client.describe_target_groups(LoadBalancerArn=lb)
        target_group_arns = [tg["TargetGroupArn"] for tg in target_groups_response["TargetGroups"]]
        delete_target_groups(target_group_arns)


def get_lb_target_groups_by_tag(tag_key, tag_value):
    
    target_groups = []
    
    try:
        response = tagging_client.get_resources(
            TagFilters=[{"Key": tag_key, "Values": [tag_value]}],
            ResourceTypeFilters=["elasticloadbalancing:targetgroup"]
        )

        # Extract Target Group ARNs
        for resource in response["ResourceTagMappingList"]:
            tg_arn = resource["ResourceARN"]
            print(f"Target Group marked for deletion: {tg_arn}")
            target_groups.append(tg_arn)

    except Exception as e:
        print(f"Error fetching tagged Target Groups: {e}")

    return target_groups

tag_key = "to_delete"
tag_value = "yes"
target_groups_to_delete = get_lb_target_groups_by_tag(tag_key, tag_value)
delete_target_groups(target_groups_to_delete)

bw_lbs = get_lb_to_delete()
delete_lbs(bw_lbs)
