import pulumi
import chef_nodes
import network
import server
import chef
import pulumi_aws as aws

from dataclasses import dataclass, field
from typing import Optional, Sequence, Dict 


NodeConfig = chef_nodes.ServerConfig

@dataclass
class DatabagConfig:
    name: str
    content_path: str

@dataclass
class NetworkConfig:
    availability_zone: str

@dataclass
class ServerConfig:
    configuration: server.ServerArgs
    provision_vars: Dict = field(default_factory=dict) 
@dataclass
class ClusterArgs:
    network_config: NetworkConfig
    chef_server: ServerConfig 
    nodes: Dict[str, NodeConfig] 
    cookbooks: Sequence[str]
    databags: Sequence[DatabagConfig]

class Cluster(pulumi.ComponentResource):
    def __init__(self, name: str, args: ClusterArgs, opts: Optional[pulumi.ResourceOptions] = None) -> None:
        super().__init__('chalkan:chef:Cluster', name, None, opts)
        self._name = name
        self._args = args
        self.network = self._create_network()
        self.chef_server = self._create_chef_servers()
        self.knife = self._configure_chef_knife()
        self.cookbooks = self._upload_default_cookbooks()
        self.databags = self._handle_databags()
        self.nodes = self._create_chef_nodes()
    
    def _create_network(self) -> network.Network:
        net = network.Network('main-network', network.NetworkArgs(
            vpc_cidrs_block='10.0.0.0/16',
            subnets={
                    'public-subnet': network.Subnet(cidr_block='10.0.1.0/24', public=True, availability_zone=self._args.network_config.availability_zone, tags={}),
                },
            ), pulumi.ResourceOptions(parent=self)
        )
        net.route_table('main-route', cidr_block=['0.0.0.0/0'], associate_subnet=['public-subnet'])
        net.create_security_group('main', 
            description='main-security-group', 
            ingress=[
                aws.ec2.SecurityGroupIngressArgs(from_port=22, to_port=22, protocol='tcp', cidr_blocks=['0.0.0.0/0']),
                aws.ec2.SecurityGroupIngressArgs(from_port=80, to_port=80, protocol='tcp', cidr_blocks=['0.0.0.0/0']),
                aws.ec2.SecurityGroupIngressArgs(from_port=443, to_port=443, protocol='tcp', cidr_blocks=['0.0.0.0/0']),
            ],
            egress=[aws.ec2.SecurityGroupEgressArgs(from_port=0, to_port=0, protocol="-1", cidr_blocks=['0.0.0.0/0'])]
        )
         
        return net

    def _configure_chef_knife(self):
        if self.chef_server.instance is not None:
            return self.chef_server.instance.public_ip.apply(lambda public_ip: chef.Chef('configure-knife', chef.ChefArgs(
                private_key='/Users/chalkan/.ssh/id_rsa',
                configuration={
                    'chef_server_host': public_ip,
                    'chef_server_url': public_ip,
                    'chef_organization_name': 'main-org',
                    'chef_node_name': 'root',
                    'chef_client_name': 'admin',
                }
            ), pulumi.ResourceOptions(parent=self, depends_on=[self.network, self.chef_server, self.chef_server.provision_command])

        )
    )
        

    def _create_chef_servers(self) -> server.Server:
        self._args.chef_server.configuration.net = self.network
        return server.Server('chef-server', 
            self._args.chef_server.configuration, 
            pulumi.ResourceOptions(parent=self, depends_on=[self.network])
        ).ansible_provision('configure-chef-server', playbook='pulumi/chef/playbooks/configure_chef_server.yml')   



    def _handle_databags(self):
        databags_update_command = []
        if self.knife is not None:
            def databags(chef_handler: chef.Chef):
                for databag in self._args.databags:
                    create_databag_command = chef_handler.knife_data_bag_create(databag.name)
                    databag_update_command = chef_handler.knife_data_bag_update(f'update-{databag.name}', databag=databag.name, content_path=f'chef/databags/{databag.content_path}', depends_on=[create_databag_command])
                    databags_update_command.append(databag_update_command)

            self.knife.apply(lambda chef_handler: databags(chef_handler))
        return databags_update_command

    def _upload_default_cookbooks(self):
        cookbooks_upload_command = []

        if self.knife is not None:
            def upload(chef_handler: chef.Chef):
                for cookbook in self._args.cookbooks:
                    cookbook_upload_command = chef_handler.knife_cookbook_upload(cookbook)
                    cookbooks_upload_command.append(cookbook_upload_command)

            self.knife.apply(lambda knife: upload(knife))

        return cookbooks_upload_command

    def _create_chef_nodes(self) -> Optional[chef_nodes.Nodes]:
        if self.chef_server.instance is not None and self.chef_server.provision_command is not None:
            return chef_nodes.Nodes(
                f'chef-nodes-{self._name}', 
                chef_nodes.NodesArgs(
                    chef_server_host=self.chef_server.instance.public_ip,
                    nodes_config=self._args.nodes,
                    network=self.network,
                ), 
                pulumi.ResourceOptions(
                    parent=self,
                    depends_on=[
                        self.network,
                        self.chef_server,
                        self.chef_server.provision_command,
                        *self.databags,
                        *self.cookbooks
                    ]
                )
            ) 

        return None
