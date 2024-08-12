import pulumi
import server
import network

from dataclasses import dataclass, field
from typing import Optional, Dict 


@dataclass
class ServerConfig:
    configuration: server.ServerArgs
    provision_vars: Dict = field(default_factory=dict)

@dataclass
class NodesArgs:
    nodes_config: Dict[str, ServerConfig]
    chef_server_host: pulumi.Input[str]
    network: network.Network

class Nodes(pulumi.ComponentResource):
    def __init__(self, name: str, args: NodesArgs, opts: Optional[pulumi.ResourceOptions] = None) -> None:
        super().__init__('chalkan:chef:Nodes', name, None, opts)
        self._name = name
        self._args = args
        self.servers = self._create_node()

    def _create_node(self) -> pulumi.Output[Dict[str, server.Server]]:
        if isinstance(self._args.chef_server_host, pulumi.Output):
            return self._args.chef_server_host.apply(lambda host_ip: {
                server_name: server.Server(
                    server_name, 
                    (
                        lambda network: setattr(server_config.configuration, 'net', network) or server_config.configuration
                    )(self._args.network), 
                    pulumi.ResourceOptions(parent=self) 
                ).ansible_provision(
                    f'{server_name}-configure-chef-node',
                    playbook='pulumi/chef/playbooks/configure_chef_node.yml',
                    extra_vars=(
                        lambda d: {**d, 'chef_server_host': host_ip }
                    )(server_config.provision_vars)
                )
                for server_name, server_config in self._args.nodes_config.items()
            })

        return pulumi.Output.from_input({})

