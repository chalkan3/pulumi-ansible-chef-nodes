import pulumi
import json
import uuid
import pulumi_command as command
import pulumi_random as random
from dataclasses import dataclass 
from typing import Optional, Sequence

@dataclass
class ChefArgs:
    private_key: str
    configuration: dict

class Chef(pulumi.ComponentResource):
    def __init__(self,  name: str, args: ChefArgs, opts: Optional[pulumi.ResourceOptions] = None) -> None:
        super().__init__('chalkan:chef:Knife', name, None, opts, False)
        self._name = name
        self._args = args
        self._configure_knife_command = self._configure_knife()

    def _configure_knife(self):
        extra_vars = json.dumps(self._args.configuration) 
        raw_command = f"ansible-playbook -i localhost, -e '{extra_vars}' ansible/pulumi/chef/playbooks/configure_knife.yml"

        return command.local.Command('configure-knife', command.local.CommandArgs(
           create=raw_command,
           update=raw_command,
           environment={'ANSIBLE_HOST_KEY_CHECKING': 'False' }
        ), pulumi.ResourceOptions(parent=self))
    
    def knife_node_list(self, name):
        raw_command = 'knife node list'
        command.local.Command(f'knife-node-list-{name}', command.local.CommandArgs(
            create=raw_command,
            update=raw_command,
        ), pulumi.ResourceOptions(parent=self, depends_on=[self._configure_knife_command]))

        return self

    def knife_cookbook_upload(self, cookbook: str):
        command_key = random.RandomString(f'cookbook-{cookbook}-{str(uuid.uuid4())}', length=5, special=False, opts=pulumi.ResourceOptions(parent=self))
        raw_command = f'knife cookbook upload {cookbook}'
        return command_key.result.apply(lambda name: command.local.Command(f'knife-cookbook-upload-{name}', command.local.CommandArgs(
            create=raw_command,
            update=raw_command,
        ), pulumi.ResourceOptions(parent=self, depends_on=[self._configure_knife_command])))

    def knife_data_bag_create(self, name: str):
        raw_command = f'knife data bag create {name}'
        return command.local.Command(f'knife-databag-create-{name}', command.local.CommandArgs(
            update=raw_command,
            create=raw_command,
        ), pulumi.ResourceOptions(parent=self, depends_on=[self._configure_knife_command]))

    def knife_data_bag_update(self, name: str, databag: str, content_path: str, depends_on: Sequence = []) -> command.local.Command:
        databag_file_asset = pulumi.FileAsset(content_path)
        raw_command = f'knife data bag from file {databag} {content_path}'
        return command.local.Command(f'update-databag-{name}', command.local.CommandArgs(
            create=raw_command,
            update=raw_command,
            triggers=[databag_file_asset],
        ), pulumi.ResourceOptions(parent=self, depends_on=[*[self._configure_knife_command], *depends_on]))

