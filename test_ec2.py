import pulumi
import unittest

from typing import Tuple, Optional, List

class Ec2InstanceMock(pulumi.runtime.Mocks):
    def new_resource(self, args: pulumi.runtime.MockResourceArgs) -> Tuple[Optional[str], dict]:
        if args.typ == 'aws:ec2/instance:Instance':
            props = args.inputs
            instance_id = 'i-1234567890abcdef0'
            outputs = {
                "instanceId": instance_id,
                "publicIp": "203.0.113.10", 
                "tags": props.get('tags'), 
                "vpcSecurityGroupIds": props.get('vpcSecurityGroupIds'),
            }

            return instance_id, outputs
        if args.typ == 'aws:ec2/securityGroup:SecurityGroup':
            props = args.inputs
            security_group_id = 'sg-903004f8'

            return security_group_id, props 
        return "", {}
    
    def call(self, args: pulumi.runtime.MockCallArgs) -> Tuple[dict, Optional[List[Tuple[str, str]]]]:
        if args.token == 'aws:ec2/securityGroup:getSecurityGroup':
            security_group_id = args.args.get('securityGroupId')
            return {}, None
        return {}, None


pulumi.runtime.set_mocks(Ec2InstanceMock(), preview=False)

import infra

class TestingWithMocks(unittest.TestCase):
    @pulumi.runtime.test
    def test_public_ip(self):
        def check_publick_ip(args):
            urn, public_ip = args
            self.assertIsNotNone(public_ip, f'server {urn} must have a public ip')
            self.assertTrue(public_ip == "203.0.113.10", f'server {urn} has public ip: {public_ip}') 
        return pulumi.Output.all(infra.server.urn, infra.server.public_ip).apply(check_publick_ip)
    @pulumi.runtime.test
    def test_tags(self):
        def check_tags(args):
            urn, tags = args
            self.assertIsNotNone(tags, f'server {urn} must have tags')
            self.assertIn('Name', tags, f'server {urn} must have Name tag')
        return pulumi.Output.all(infra.server.urn, infra.server.tags).apply(check_tags)
    @pulumi.runtime.test
    def test_security_group(self):
        def check_security_group_id(args):
            urn, security_groups_ids = args
            print(security_groups_ids)
        return pulumi.Output.all(infra.server.urn, infra.server.vpc_security_group_ids).apply(check_security_group_id)
