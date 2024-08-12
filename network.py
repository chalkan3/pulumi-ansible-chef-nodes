import pulumi
import pulumi_aws as aws

from typing import Optional, Sequence, Dict
from dataclasses import dataclass

@dataclass
class Subnet:
    cidr_block: str
    availability_zone: str
    public: bool
    tags: Dict[str, str]

@dataclass
class NetworkArgs:
    vpc_cidrs_block: str
    subnets: Dict[str, Subnet] 

class Network(pulumi.ComponentResource):
    def __init__(self, name: str, args: NetworkArgs, opts: Optional[pulumi.ResourceOptions] = None):
        super().__init__('chalkan:chef:Network', name, None, opts)
        self._name = name
        self._args = args
        self.vpc = self._create_vpc()
        self._subnets = self._create_subnets()
        self._route_tables = {}
        self._security_groups = {}

    def get_subnet(self, name: str) -> aws.ec2.Subnet:
        return self._subnets[name]
    def get_security_group(self, name: str) -> aws.ec2.SecurityGroup:
        return self._security_groups[name]

    def _create_vpc(self) -> aws.ec2.Vpc:
        return aws.ec2.Vpc(f'{self._name}-vpc', aws.ec2.VpcArgs(cidr_block=self._args.vpc_cidrs_block), pulumi.ResourceOptions(parent=self))

    def route_table(self, name: str, cidr_block: Sequence[str], associate_subnet: Sequence[str]):
        igw = aws.ec2.InternetGateway(f'{self._name}-{name}-internet-gateway', vpc_id=self.vpc.id, opts=pulumi.ResourceOptions(parent=self))
        route_table = aws.ec2.RouteTable(f'{self._name}-{name}-route-table', aws.ec2.RouteTableArgs(
            vpc_id=self.vpc.id,
            routes=[aws.ec2.RouteTableRouteArgs(cidr_block=cidr, gateway_id=igw.id) for cidr in cidr_block],
        ), pulumi.ResourceOptions(parent=self))

        self._route_tables[name] = route_table
        
        for subnet_name in associate_subnet:
            subnet = self._subnets[subnet_name]
            _ = aws.ec2.RouteTableAssociation(f'{self._name}-subnet-name-{subnet_name}-rt-assoc', subnet_id=subnet.id, route_table_id=route_table.id, opts=pulumi.ResourceOptions(parent=self))
        
    def create_security_group(self, name: str, description: str, ingress: Sequence[aws.ec2.SecurityGroupIngressArgs], egress: Sequence[aws.ec2.SecurityGroupEgressArgs]):
        self._security_groups[name] = aws.ec2.SecurityGroup(f'{self._name}-{name}-security-group', description=description, vpc_id=self.vpc.id, ingress=ingress, egress=egress, opts=pulumi.ResourceOptions(parent=self))
    def _create_subnets(self):
        return {
            subnet_name: aws.ec2.Subnet(f'{self._name}-{subnet_name}', vpc_id=self.vpc.id, cidr_block=values.cidr_block, map_public_ip_on_launch=values.public, availability_zone=values.availability_zone, tags=values.tags, opts=pulumi.ResourceOptions(parent=self))
            for subnet_name, values in self._args.subnets.items()
        }
