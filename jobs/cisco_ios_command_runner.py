# jobs/cisco_ios_command_runner.py

# Import necessary components from Nautobot and potentially other libraries
from nautobot.apps.jobs import Job, StringVar, ObjectVar, TextVar
from nautobot.dcim.models import Device
from netmiko import ConnectHandler # For SSH connection
from netmiko.exceptions import NetmikoAuthenticationException, NetmikoTimeoutException

# Define a grouping for your jobs in the UI (optional but recommended)
name = "Device Interaction Examples"

# Define the Job class, inheriting from nautobot.apps.jobs.Job
class CiscoIOSCommandRunner(Job):
    """
    A boilerplate job to connect to a Cisco IOS device via SSH and run a command.
    """
    # Job Metadata - how it appears in the Nautobot UI
    class Meta:
        name = "Cisco IOS Command Runner"
        description = "Connects to a selected Cisco IOS device via SSH and executes a single CLI command."
        # Optional: Specify field order in the UI form
        field_order = ["device", "command_to_run"]
        # Optional: requires_approval = True # If job runs need manual approval
        # Optional: commit_default = False # Default state of commit checkbox

    # Define input variables that the user will provide when running the job
    device = ObjectVar(
        model=Device,
        label="Target Device",
        description="Select the Cisco IOS device to connect to.",
        # Limit choices to devices with specific criteria (adjust as needed)
        query_params={
            'platform__slug': 'cisco_ios' # Example: Only show devices with platform slug 'cisco_ios'
        }
    )

    command_to_run = StringVar(
        label="CLI Command",
        description="Enter the Cisco IOS command to execute (e.g., 'show version')",
        required=True, # Make this field mandatory
        default="show version", # Provide a default value
    )

    # Define output variables (optional, good for structured results or display)
    output = TextVar(
        label="Command Output / Status",
    )

    # The main logic of the job goes into the 'run' method
    def run(self, data, commit):
        """
        The main execution method for the job.
        'data' dictionary contains the user-provided values for the variables defined above.
        'commit' is a boolean indicating if changes should be saved (True) or simulated (False).
        """
        selected_device = data['device']
        command = data['command_to_run']
        job_output = "" # Initialize an empty string for output

        self.log_info(f"Starting job for device: {selected_device.name}")
        self.log_info(f"Attempting to run command: '{command}'")

        # --- Get Device Connection Details ---
        # Ensure the device has a primary IP address configured in Nautobot
        if not selected_device.primary_ip4 and not selected_device.primary_ip6:
            self.log_failure(f"Device {selected_device.name} does not have a primary IPv4 or IPv6 address configured.")
            return # Stop the job if no IP

        # Prefer IPv4, fallback to IPv6 if needed
        ip_address = selected_device.primary_ip4.address.ip if selected_device.primary_ip4 else selected_device.primary_ip6.address.ip
        self.log_info(f"Using IP address: {ip_address}")

        # --- IMPORTANT: Credential Handling ---
        # NEVER hardcode credentials directly in your job code!
        # Options:
        # 1. Nautobot Secrets: Store credentials securely in Nautobot's Secrets Providers. Access them via `selected_device.get_secret_value(...)`. (RECOMMENDED)
        # 2. Environment Variables: Less secure, but possible in some setups.
        # For this boilerplate, we'll use placeholder variables. Replace with your chosen method.
        username = "YOUR_SSH_USERNAME" # <-- REPLACE or fetch securely
        password = "YOUR_SSH_PASSWORD" # <-- REPLACE or fetch securely

        # --- Define Netmiko Device Parameters ---
        # The 'device_type' often maps to the platform slug, but verify Netmiko's supported types.
        # You might need more sophisticated logic if your platform slugs don't map directly.
        device_params = {
            'device_type': 'cisco_ios', # Netmiko device type
            'host': str(ip_address),
            'username': username,
            'password': password,
            # Add other Netmiko options if needed (e.g., port, secret for enable mode)
            # 'port': 22,
            # 'secret': 'YOUR_ENABLE_PASSWORD', # For 'enable' mode commands
        }

        # --- Establish SSH Connection and Run Command ---
        try:
            self.log_info(f"Connecting to {selected_device.name} ({ip_address})...")
            with ConnectHandler(**device_params) as net_connect:
                self.log_info("Connection successful.")

                # If you need enable mode:
                # net_connect.enable()

                self.log_info(f"Sending command: '{command}'")
                cli_output = net_connect.send_command(command)
                self.log_success(f"Command executed successfully on {selected_device.name}.")

                # Store the output for display
                job_output = cli_output

        except NetmikoTimeoutException:
            error_msg = f"Connection timed out to {selected_device.name} ({ip_address}). Check reachability and firewall rules."
            self.log_failure(error_msg)
            job_output = error_msg
        except NetmikoAuthenticationException:
            error_msg = f"Authentication failed for {selected_device.name} ({ip_address}). Check username/password."
            self.log_failure(error_msg)
            job_output = error_msg
        except Exception as e:
            # Catch any other unexpected errors during connection or command execution
            error_msg = f"An unexpected error occurred while connecting or running command on {selected_device.name}: {e}"
            self.log_failure(error_msg)
            job_output = error_msg

        # --- Log Final Output ---
        # Log the command output (can be long, use log_debug or truncate if needed)
        self.log_info(f"Raw Output from {selected_device.name}:\n---\n{job_output}\n---")

        # You can also return structured data if needed, or just log results.
        # Setting the TextVar content makes it visible in the job results output section.
        self.data['output'] = job_output # Update the TextVar defined earlier
        return job_output # The return value is also logged