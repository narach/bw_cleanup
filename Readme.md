The repository contains scripts to delete BossWireless resources.
Each script deletes existing resources for specified AWS service, as they shown in 
AWS Tag Editor. For example cleanup-ec2.py should drop all resources for Service Type
EC2: Instance, SecurityGroup, NetworkInterface, Volume.

The resources related for BossWireless are received using following filters:
1) IDT QA account(dev, qa, qa-rc environments): https://us-east-1.console.aws.amazon.com/resource-groups/tag-editor/find-resources?region=us-east-1#query=regions:!%28%27AWS::AllSupported%27%29,resourceTypes:!%28%27AWS::AllSupported%27%29,tagFilters:!%28%28key:%27tech:team_name%27,values:!%28team_boss_wireless,team_brmobile%29%29%29,type:TAG_EDITOR_1_0
2) IDT Prod account(uat, proc environments): https://us-east-1.console.aws.amazon.com/resource-groups/tag-editor/find-resources?region=us-east-1#query=regions:!%28%27AWS::AllSupported%27%29,resourceTypes:!%28%27AWS::AllSupported%27%29,tagFilters:!%28%28key:%27tech:team_name%27,values:!%28team_boss_wireless%29%29%29,type:TAG_EDITOR_1_0

CSVs with the existing resources list as for March 20 2025 are stored in this repository:
1) IDT_QA-BW-resources.csv
2) IDT_Prod-BW-resources.csv