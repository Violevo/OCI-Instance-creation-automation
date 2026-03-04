import os
import sys
import time
import oci
import random
from oci.exceptions import ServiceError
from dotenv import load_dotenv

load_dotenv()

def get_required_env(var_name):
    value = os.getenv(var_name)
    if not value:
        print(f"Error: Environment variable '{var_name}' is missing in .env")
        sys.exit(1)
    return value

def get_availability_domains():
    domains = []
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                # Ignore comments
                if line.startswith("#"):
                    continue
                if line.startswith("OCI_AVAILABILITY_DOMAIN=") or line.startswith("OCI_AVAILABILITY_DOMAIN_"):
                    key_val = line.split("=", 1)
                    if len(key_val) == 2:
                        val = key_val[1].strip().strip("'\"")
                        for ad in val.split(','):
                            if ad.strip() and ad.strip() not in domains:
                                domains.append(ad.strip())
                                
    if not domains:
        env_val = os.getenv("OCI_AVAILABILITY_DOMAIN")
        if env_val:
            domains = [ad.strip() for ad in env_val.split(',') if ad.strip()]
            
    if not domains:
        print("Error: No Availability Domains found. Please set OCI_AVAILABILITY_DOMAIN in .env")
        sys.exit(1)
        
    return domains

def create_instance(compute_client, config_data):
    shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
        ocpus=config_data['ocpus'],
        memory_in_gbs=config_data['memory']
    )
    
    try:
        with open(config_data['ssh_key'], "r", encoding="utf-8") as f:
            ssh_key_data = f.read()
    except Exception as e:
        print(f"Could not read SSH key: {e}")
        return None

    create_instance_details = oci.core.models.LaunchInstanceDetails(
        compartment_id=config_data['compartment_id'],
        availability_domain=config_data['availability_domain'],
        shape=config_data['shape'],
        shape_config=shape_config,
        display_name=config_data['name'],
        source_details=oci.core.models.InstanceSourceViaImageDetails(
            source_type="image",
            image_id=config_data['image_id']
        ),
        create_vnic_details=oci.core.models.CreateVnicDetails(
            assign_public_ip=True,
            subnet_id=config_data['subnet_id']
        ),
        metadata={
            "ssh_authorized_keys": ssh_key_data
        }
    )

    try:
        instance = compute_client.launch_instance(create_instance_details)
        print(f"Instance '{config_data['name']}' created successfully! OCID: {instance.id}")
        return instance
    except ServiceError as e:
        print(f"API Error ({e.status}): {e.message}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def main():
    availability_domains = get_availability_domains()
    
    config_data = {
        'compartment_id': get_required_env("OCI_COMPARTMENT_ID"),
        'availability_domain': availability_domains[0],
        'image_id': get_required_env("OCI_IMAGE_ID"),
        'subnet_id': get_required_env("OCI_SUBNET_ID"),
        'name': get_required_env("OCI_INSTANCE_NAME"),
        'shape': get_required_env("OCI_SHAPE"),
        'ocpus': float(get_required_env("OCI_OCPUS")),
        'memory': float(get_required_env("OCI_MEMORY")),
        'ssh_key': os.path.expanduser(get_required_env("OCI_SSH_KEY")),
    }
    
    retry_interval = int(get_required_env("OCI_RETRY_INTERVAL"))
    oci_config_path = get_required_env("OCI_CONFIG_PATH")
    
    config_path = os.path.expanduser(oci_config_path)
    try:
        config = oci.config.from_file(config_path)
    except oci.exceptions.ConfigFileNotFound:
        print(f"OCI config file not found at {config_path}")
        sys.exit(1)
        
    compute_client = oci.core.ComputeClient(config)

    print(f"Starting instance creation for '{config_data['name']}'")
    ad_index = 0
    while True:
        current_ad = availability_domains[ad_index]
        config_data['availability_domain'] = current_ad
        print(f"Attempting to create instance (AD: {current_ad})")
        
        instance = create_instance(compute_client, config_data)
        if instance:
            break

        ad_index = (ad_index + 1) % len(availability_domains)
        next_ad = availability_domains[ad_index]
        
        delay = retry_interval + random.uniform((-retry_interval*0.15), (retry_interval*0.15)) 
        print(f"Retrying in {delay:.2f} seconds")
        time.sleep(delay)

if __name__ == "__main__":
    main()