import paramiko
import getpass
from scp import SCPClient

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# Utility functions
# Get current user
def get_current_user():
    return getpass.getuser()

# Copy a file via ssh
def scp_copy_file(user, host, source, dest):
    ssh.connect(host, '22', user)
    scp = SCPClient(ssh.get_transport())
    #print("Copy file %s from host %s to dest %s" % (source, host, dest))
    scp.get(source, dest)
    ssh.close()

# Copy a directory to a host
def scp_put_dir(user, host, directory, dest):
    ssh.connect(host, '22', user)
    scp = SCPClient(ssh.get_transport())  
    scp.put(directory, dest, recursive=True)
    ssh.close()
    
# Execute an SSH command at a host
def ssh_exec_command(username, host, command, throw_on_error=True):
    ssh.connect(host, '22', username)
    stdin, stdout, stderr = ssh.exec_command(command)
    # Raise an exception if an error was returned
    error = stderr.readlines()
    if error != []:
        print("ERROR: %s" % error)
        if throw_on_error:
            raise Exception(error)
    # Return stdout lines
    readlines = stdout.readlines()
    ssh.close()
    return readlines

# Generate threads number list
def generate_thread_num_list(available_threads):
    threads = []
    power = 1
    result = 1
    while result <= available_threads:
        threads.append(result)
        result = pow(2, power)
        power += 1
        
    # Necessary when available threads number is not power of 2
    # For example 18 threads
    if available_threads not in threads:
        threads.append(available_threads)
        
    return ",".join([str(num) for num in threads])

# Generate frequencies from min to maximum with step of 0.2 Ghz
def generate_frequencies(min_frequency, max_frequency):
    frequencies = []
    result = 1000000
    while result <= max_frequency:
        frequencies.append(result)
        result += 200000
    return ",".join([str(freq) for freq in frequencies])
