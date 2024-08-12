import pulumi
import json
import network
import pulumi_aws as aws
import pulumi_command as command

from typing import Optional
from dataclasses import dataclass 

@dataclass
class ServerArgs:
    instance_type: str
    instance_user: str
    availability_zone: str
    public_key_path: str
    private_key_path: str
    subnet_name: str
    security_group_name: str
    net: Optional[network.Network] = None

    
class Server(pulumi.ComponentResource):
    def __init__(self, name: str, args: ServerArgs, opts: Optional[pulumi.ResourceOptions] = None):
        super().__init__('chalkan:chef:Host', name, None, opts)
        self._name = name
        self._args = args
        self.key_pair = self._create_key_pair()
        self.instance = self._create_instance()
    
    def _create_key_pair(self):
        public_key = open(self._args.public_key_path).read()

        return aws.ec2.KeyPair(f'{self._name}-key-pair', aws.ec2.KeyPairArgs(public_key=public_key), pulumi.ResourceOptions(parent=self))
    def _create_instance(self):
        if self._args.net is not None:
            ami = aws.ec2.get_ami(most_recent=True, owners=['amazon'], filters=[{'name': 'name', 'values': ['amzn2-ami-hvm-*-x86_64-gp2']}])

            return aws.ec2.Instance(f'{self._name}-instance', aws.ec2.InstanceArgs(
               instance_type=self._args.instance_type,
               key_name=self.key_pair.id,
               ami=ami.id,
               subnet_id=self._args.net.get_subnet(self._args.subnet_name).id,
               availability_zone=self._args.availability_zone,
               vpc_security_group_ids=[self._args.net.get_security_group(self._args.security_group_name).id]
            ), pulumi.ResourceOptions(parent=self))
    
    def ansible_provision(self, name:str, playbook: str, extra_vars: dict = {}):
        if self.instance is not None:
            extra_vars_json_dump = json.dumps(extra_vars)
            raw_command = self.instance.public_ip.apply(lambda public_ip: f"ansible-playbook -u {self._args.instance_user} -i {public_ip}, --private-key {self._args.private_key_path} -e '{extra_vars_json_dump}' ansible/{playbook}")

            self.provision_command = command.local.Command(f'provision-with-ansible-playbook-{name}', command.local.CommandArgs(
                create=raw_command,
                update=raw_command,
                environment={'ANSIBLE_HOST_KEY_CHECKING': 'False' },
            ), pulumi.ResourceOptions(parent=self, depends_on=[self.instance]))
        
        return self
        
