import pulumi
import server
import chef_cluster 
import pulumi_aws as aws

availability_zone = aws.get_availability_zones().names[0]

config = pulumi.Config()

cluster_configuration = config.require_object('chef-cluster')

cluster = chef_cluster.Cluster(cluster_configuration['name'], chef_cluster.ClusterArgs(
    network_config=chef_cluster.NetworkConfig(availability_zone=availability_zone),
    cookbooks=cluster_configuration['server']['cookbooks'],
    databags=[
        chef_cluster.DatabagConfig(name=name, content_path=content_path) 
        for name, content_path in cluster_configuration['server']['databags'].items()
    ],
    chef_server=chef_cluster.ServerConfig(
            configuration=server.ServerArgs(
                subnet_name=cluster_configuration['server']['infrastructure']['network']['subnet']['name'],
                security_group_name=cluster_configuration['server']['infrastructure']['security-group']['name'],
                instance_type=cluster_configuration['server']['infrastructure']['instance']['type'],
                instance_user=cluster_configuration['server']['infrastructure']['instance']['ssh']['user'],
                availability_zone=availability_zone,
                public_key_path=cluster_configuration['server']['infrastructure']['instance']['ssh']['public-key'],
                private_key_path=cluster_configuration['server']['infrastructure']['instance']['ssh']['private-key'],   
        ),
    ),
    nodes={
        node_name: chef_cluster.NodeConfig(
            configuration=server.ServerArgs(
                subnet_name=node['infrastructure']['network']['subnet']['name'], 
                security_group_name=node['infrastructure']['security-group']['name'], 
                instance_type=node['infrastructure']['instance']['type'],
                instance_user=node['infrastructure']['instance']['ssh']['user'],
                availability_zone=availability_zone,
                public_key_path=node['infrastructure']['instance']['ssh']['public-key'],
                private_key_path=node['infrastructure']['instance']['ssh']['private-key'],
            ),
            provision_vars=node['client.rb']
        )
        for node_name, node in cluster_configuration['nodes'].items()      
    }
))



pulumi.export('amazon-vpc-id', cluster.network.vpc.id)

if cluster.chef_server.instance and cluster.chef_server.instance.public_ip:
    pulumi.export('chef-server-host', cluster.chef_server.instance.public_ip)

if cluster.nodes and cluster.nodes.servers:
    pulumi.export('chef-nodes', cluster.nodes.servers.apply(lambda nodes: {
            chef_node_name: node.instance.public_ip
            for chef_node_name, node in nodes.items() 
            if node.instance and node.instance.public_ip
        }
    ))

