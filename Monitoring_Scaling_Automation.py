import boto3
import base64
import time
import uuid
import os

def Create_S3_Bucket(region_name):
    session = boto3.Session(
    aws_access_key_id=os.getenv('Access_Key'),
    aws_secret_access_key=os.getenv('Secret_Key'),
    region_name=region_name
    )

    s3_client = session.client('s3')

    bucket_name = 's3-'+str(uuid.uuid4())[:5] 

    s3_client.create_bucket(
        Bucket=bucket_name,
        CreateBucketConfiguration={
        'LocationConstraint': region_name
        },
        ObjectOwnership='BucketOwnerEnforced',
    )

    s3_client.put_bucket_website(
    Bucket=bucket_name,
    WebsiteConfiguration={
        'IndexDocument': {
            'Suffix': 'index.html'
        }
    }
    )

    print(f'Created S3 bucket for web app static files: {bucket_name}')

def Create_Security_Group(ec2_client, group_name, description, vpc_id):
    try:
        response = ec2_client.create_security_group(
            Description=description,
            GroupName=group_name,
            VpcId=vpc_id
        )
        security_group_id = response['GroupId']
        print(f"Security group '{group_name}' created with ID: {security_group_id}")
        return security_group_id
    except Exception as e:
        print(f"Error creating security group: {e}")
        return None

def Authorize_Ingress_Rules(ec2_client, security_group_id):
    try:
        ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]  
                }
            ]
        )

        ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )

        ec2_client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 5000,
                    'ToPort': 5000,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                }
            ]
        )

        print(f"Ingress rules added to security group ID: {security_group_id}")
    except Exception as e:
        print(f"Error authorizing ingress rules: {e}")

def Launch_EC2_Instance(ec2_client, image_id, instance_type, key_name, security_group_ids, user_data):
    try:
        instance = ec2_client.run_instances(
            ImageId=image_id,
            InstanceType=instance_type,
            MinCount=1,
            MaxCount=1,
            KeyName=key_name,
            SecurityGroupIds=[security_group_ids],
            UserData=user_data,
            TagSpecifications=[
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {
                            'Key': 'Name',
                            'Value': 'EC2-'+str(uuid.uuid4())[:5]
                        },
                    ]
                 },
            ]
        )
        instance_id = instance['Instances'][0]['InstanceId']
        print(f"Instance {instance_id} launched successfully.")
        return instance_id
    except Exception as e:
        print(f"Error launching EC2 instance: {e}")

def Launch_Load_Balancer(elbv2_client, subnet_ids, security_groups,region_name):
    alb_name='ALB-'+str(uuid.uuid4())[:5]
    response = elbv2_client.create_load_balancer(
        Name=alb_name,
        Subnets=subnet_ids,
        SecurityGroups=security_groups,
        Scheme='internet-facing',
        Tags=[
            {
                'Key': 'Name',
                'Value': alb_name
            },
        ],
    )

    print("DNS Name:", response['LoadBalancers'][0]['DNSName'])
    return response['LoadBalancers'][0]['LoadBalancerArn']

def Listener_Configuration(elbv2_client,vpc_id):
    listener_name='LN-'+str(uuid.uuid4())[:5]
    target_group_response = elbv2_client.create_target_group(
    Name=listener_name,
    Protocol='HTTP',
    Port=80,
    VpcId=vpc_id,
    HealthCheckProtocol='HTTP',
    HealthCheckPort='5000',
    HealthCheckPath='/',
    HealthCheckIntervalSeconds=30,
    HealthCheckTimeoutSeconds=5,
    HealthyThresholdCount=5,
    UnhealthyThresholdCount=2,
        Tags=[
            {
                'Key': 'Name',
                'Value': listener_name
            },
        ]
    )

    print('target_group_response:',target_group_response['TargetGroups'][0]['TargetGroupArn'])
    return target_group_response['TargetGroups'][0]['TargetGroupArn']

def Create_Listener(elbv2_client,load_balancer_arn):
    listener_port = 80
    protocol = 'HTTP'
    listener_response = elbv2_client.create_listener(
    LoadBalancerArn=load_balancer_arn,
    Protocol=protocol,
    Port=listener_port,
    DefaultActions=[
        {
            'Type': 'forward',
            'TargetGroupArn': target_group_arn
        },
    ]
    )

    print("Listener ARN:", listener_response['Listeners'][0]['ListenerArn'])

def Listener_Registration(elbv2_client,target_group_arn, instance_id):
    response = elbv2_client.register_targets(
        TargetGroupArn=target_group_arn,
        Targets=[
            {
                'Id': instance_id,
            },
        ]
    )
    print("Instance registered:", response)

def Generate_AMI_From_EC2_Instance(region_name,instance_id):
    session = boto3.Session(
    aws_access_key_id=os.getenv('Access_Key'),
    aws_secret_access_key=os.getenv('Secret_Key'),
    region_name=region_name
    )

    ec2_client = session.client('ec2')

    response = ec2_client.create_image(
    InstanceId=instance_id,
    Name='AMI-'+str(uuid.uuid4())[:5]
,  
    NoReboot=True
    )
    ami_id = response['ImageId']
    print(f'Created AMI ID: {ami_id}')
    return ami_id

def Create_ASG(auto_scaling_group_name,region_name,instance_id,subnet_ids,security_groups,instance_type,key_name,ami_id):
    session = boto3.Session(
    aws_access_key_id=os.getenv('Access_Key'),
    aws_secret_access_key=os.getenv('Secret_Key'),
    region_name=region_name
    )
    autoscaling_client = session.client('autoscaling')
    launch_configuration_name ='LCN-'+str(uuid.uuid4())[:5]
    instance_id = instance_id  
    security_group_ids = [security_groups]

    response = autoscaling_client.create_launch_configuration(
    LaunchConfigurationName=launch_configuration_name,
    ImageId=ami_id,  
    InstanceType=instance_type,  
    KeyName=key_name, 
    SecurityGroups=security_group_ids,
    )
    print(f'Created launch configuration: {launch_configuration_name}')

    min_size = 1 
    max_size = 3 
    desired_capacity = 2 
    subnets = subnet_ids

    response = autoscaling_client.create_auto_scaling_group(
        AutoScalingGroupName=auto_scaling_group_name,
        LaunchConfigurationName=launch_configuration_name,
        MinSize=min_size,
        MaxSize=max_size,
        DesiredCapacity=desired_capacity,
        VPCZoneIdentifier=','.join(subnets)
    )

    print(f'Created auto scaling group: {auto_scaling_group_name}')

def Create_ASG_Policy(auto_scaling_group_name,region_name):
    autoscaling_client = boto3.client('autoscaling', region_name=region_name)
    response = autoscaling_client.put_scaling_policy(
        AutoScalingGroupName=auto_scaling_group_name,
        PolicyName='ScaleOutPolicy',
        AdjustmentType='ChangeInCapacity',
        ScalingAdjustment=1,
        Cooldown=300,
    )
    print(f'Policy configured on auto scaling group')
    scaling_policy_arn = response['PolicyARN']
    return scaling_policy_arn

def Create_Cloud_Watch(region_name,scaling_policy_arn):
    cloudwatch_client = boto3.client('cloudwatch', region_name=region_name)

    response = cloudwatch_client.put_metric_alarm(
    AlarmName='CPUUtilizationHigh',
    AlarmDescription='Alarm when CPU exceeds 50%',
    MetricName='CPUUtilization',
    Namespace='AWS/EC2',
    Statistic='Average',
    ComparisonOperator='GreaterThanThreshold',
    Threshold=50.0,
    Period=300,
    EvaluationPeriods=1,
    AlarmActions=[scaling_policy_arn],
    )
    print(f'Cloud watch configuration done')

def Create_SNS_Topic(region_name):
    sns_client = boto3.client('sns', region_name=region_name)
    
    response = sns_client.create_topic(Name='ScalingNotifications')
    sns_topic_arn = response['TopicArn']

    response = sns_client.subscribe(
        TopicArn=sns_topic_arn,
        Protocol='email',
        Endpoint='pankajgacche.sdet@gmail.com',
    )
    print(f'SNS Topic configuration done')

def Check_Instance_Health(instance_id):
    response = ec2_client.describe_instance_status(
        InstanceIds=[instance_id],
        IncludeAllInstances=True
    )
    instance_status = response['InstanceStatuses'][0]['InstanceState']['Name']
    return instance_status == 'running'

def Scale_Instances(region_name,auto_scaling_group_name):
    autoscaling_client = boto3.client('autoscaling', region_name=region_name)
    response = autoscaling_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[auto_scaling_group_name]
    )
    current_capacity = response['AutoScalingGroups'][0]['DesiredCapacity']

    if current_capacity < 10:
        response = autoscaling_client.update_auto_scaling_group(
            AutoScalingGroupName=auto_scaling_group_name,
            DesiredCapacity=current_capacity + 1,
        )

def Monitor_And_Manage(instance_id):
    while True:
        if not Check_Instance_Health(instance_id):
            print(f'Monitoring Instance {instance_id} is unhealthy!')
            break
        else:
            print(f'Monitoring Instance {instance_id} is healthy!')

if __name__ == "__main__":
    instance_type = 't3.micro'
    region_name='eu-north-1'
    vpc_id='vpc-05154ead3bc4c56b7'
    instance_type = 't3.micro'
    key_name = 'My_Key_Pair'
    subnet_id = 'subnet-07f4de62d10359420'
    subnet_ids = ['subnet-07f4de62d10359420', 'subnet-013e69e3f15c5f917']
    security_groups = ['sg-0bf10eab4bb24c016']
    image_id = 'ami-07c8c1b18ca66bb07'
    ec2_client = boto3.client('ec2', region_name=region_name)
    elbv2_client = boto3.client('elbv2', region_name=region_name)
    userdata_script='''#!/bin/bash
                 sudo apt-get update -y
                 sudo apt-get install -y nginx
                 sudo mkdir -p /var/www/html/myproject
                 sudo chown -R ubuntu:ubuntu /var/www/html/myproject
                 sudo apt install python3
                 sudo apt install -y python3-pip
                 sudo apt install -y python3-flask
                 sudo apt install git
                 sudo git clone https://github.com/PankajGacche/Simple_Flask_Application.git /var/www/html/myproject
                 sudo service nginx restart
                 cd /var/www/html/myproject
                 sudo python3 simple_app.py
                 ''' 
    
userdata_script_encoded = base64.b64encode(userdata_script.encode()).decode('utf-8')
Create_S3_Bucket(region_name)
security_group_id = Create_Security_Group(ec2_client, 'SG-'+str(uuid.uuid4())[:5], 'SG-'+str(uuid.uuid4())[:5], vpc_id)

if security_group_id:
    Authorize_Ingress_Rules(ec2_client, security_group_id)
    instance_id=Launch_EC2_Instance(ec2_client, image_id, instance_type, key_name, security_group_id, userdata_script_encoded)
    load_balancer_arn=Launch_Load_Balancer(elbv2_client,subnet_ids,security_groups,region_name)
    target_group_arn=Listener_Configuration(elbv2_client,vpc_id)
    Create_Listener(elbv2_client,load_balancer_arn)
    time.sleep(60)
    Listener_Registration(elbv2_client,target_group_arn,instance_id)
    ami_id=Generate_AMI_From_EC2_Instance(region_name,instance_id)
    auto_scaling_group_name = 'ASG-'+str(uuid.uuid4())[:5]
    Create_ASG(auto_scaling_group_name,region_name,instance_id,subnet_ids,security_group_id,instance_type,key_name,ami_id)
    scaling_policy_arn=Create_ASG_Policy(auto_scaling_group_name,region_name)
    Create_Cloud_Watch(region_name,scaling_policy_arn)
    Create_SNS_Topic(region_name)
    Check_Instance_Health(instance_id)
    Scale_Instances(region_name,auto_scaling_group_name)
    Monitor_And_Manage(instance_id)