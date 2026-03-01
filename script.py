import os
import time
import oci
from oci.exceptions import ServiceError
from dotenv import load_dotenv

load_dotenv()

# Load OCI configuration from default location
config_path = os.path.join(os.path.expanduser("~"), ".oci", "config")
config = oci.config.from_file(config_path)

compute_client = oci.core.ComputeClient(config)

# Load configuration from environment variables
compartment_id = os.getenv("COMPARTMENT_ID", "YOUR_COMPARTMENT_OCID_HERE")
availability_domain = os.getenv("AVAILABILITY_DOMAIN", "YOUR_AVAILABILITY_DOMAIN_HERE")
shape = os.getenv("SHAPE", "VM.Standard.A1.Flex")

shape_ocpus = float(os.getenv("SHAPE_OCPUS", "4"))
shape_memory_in_gbs = float(os.getenv("SHAPE_MEMORY_IN_GBS", "24"))
shape_config = oci.core.models.LaunchInstanceShapeConfigDetails(
    ocpus=shape_ocpus,
    memory_in_gbs=shape_memory_in_gbs
)  

image_id = os.getenv("IMAGE_ID", "YOUR_IMAGE_OCID_HERE")
instance_name = os.getenv("INSTANCE_NAME", "your-instance-name")
subnet_id = os.getenv("SUBNET_ID", "YOUR_SUBNET_OCID_HERE")

# Path to your SSH public key file
default_ssh_key_path = os.path.join(os.path.expanduser("~"), ".ssh", "id_rsa.pub")
ssh_key_path = os.getenv("SSH_KEY_PATH", default_ssh_key_path)

def create_instance():
    try:
        create_instance_details = oci.core.models.LaunchInstanceDetails(
            compartment_id=compartment_id,
            availability_domain=availability_domain,
            shape=shape,
            shape_config=shape_config,
            display_name=instance_name,
            source_details=oci.core.models.InstanceSourceViaImageDetails(
                source_type="image",
                image_id=image_id
            ),
            create_vnic_details=oci.core.models.CreateVnicDetails(
                assign_public_ip=True,
                subnet_id=subnet_id
            ),
            metadata={
                "ssh_authorized_keys": open(ssh_key_path, "r", encoding="utf-8").read()
            }
        )

        instance = compute_client.launch_instance(create_instance_details)
        print(f"Instance {instance_name} created successfully with OCID: {instance.id}")
        print("__________________________________")
        return instance
    except ServiceError as e:
        print("Error during instance creation:")
        print(f"Message:", e.message)
        print(f"Opc Request ID:", e.request_id)
        print("__________________________________")
        return None

def create_instance_until_success():
    while True:
        print("__________________________________")
        instance = create_instance()
        if instance:
            break
        else:
            print("Instance creation failed. Retrying in 1 minute...")
            time.sleep(60) 

if __name__ == "__main__":
    create_instance_until_success()