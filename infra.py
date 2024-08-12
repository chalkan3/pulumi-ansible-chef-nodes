import pulumi_aws as aws

vpc = aws.ec2.Vpc('main-vpc', aws.ec2.VpcArgs(
    cidr_block='10.0.0.0/16',
    enable_dns_hostnames=True,
))

public_subnet = aws.ec2.Subnet('public-subnet', aws.ec2.SubnetArgs(
    vpc_id=vpc.id,
))


group = aws.ec2.SecurityGroup('web-security-group', aws.ec2.SecurityGroupArgs(
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=22,
            to_port=22,
            cidr_blocks=['0.0.0.0/0'],
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=['0.0.0.0/0'],
        ),
    ]
))

user_data = '#!/bin/bash echo "Hello, World!" > index.html nohup python -m SimpleHTTPServer 80 &'

server = aws.ec2.Instance('web-server', aws.ec2.InstanceArgs(
    instance_type='t2.micro',
    vpc_security_group_ids=[group.id],
    ami='ami-c55673a0',
    associate_public_ip_address=True,
    user_data=user_data,
    tags={'Name': 'web-server'}
))



