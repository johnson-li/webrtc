import os
import stat
import hashlib
import paramiko
from experiment.logging import logging, get_logger, logging_wrapper


logger = logging.getLogger(__name__)


def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def paramiko_connect(host, ftp=False):
    client = paramiko.SSHClient()
    client._policy = paramiko.WarningPolicy()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    ssh_config = paramiko.SSHConfig()
    user_config_file = os.path.expanduser("~/.ssh/config")
    try:
        with open(user_config_file) as f:
	        ssh_config.parse(f)
    except FileNotFoundError:
        print("{} file could not be found. Aborting.".format(user_config_file))
        return
    cfg = {'hostname': host['Name'], 'username': host["User"]}

    user_config = ssh_config.lookup(cfg['hostname'])
    for k in ('hostname', 'username', 'port'):
	    if k in user_config:
	        cfg[k] = user_config[k]
    if 'proxycommand' in user_config:
	    cfg['sock'] = paramiko.ProxyCommand(user_config['proxycommand'])
    client.connect(**cfg)
    if ftp:
        return paramiko.SFTPClient.from_transport(client.get_transport())
    return client


def execute_remote(client, cmd):
    output = ""
    stdin, stdout, stderr = client.exec_command(cmd)
    first_error = True
    first_stdout = True
    for line in stdout:
        line = line.strip('\n')
        if line:
            output += line if first_stdout else ("\n" + line)
            if first_stdout:
                logger.debug("╔════════════ DEBUG command: %s ═══════════════" % cmd)
                first_stdout = False
            logger.debug('║  ' + line)
    if not first_stdout:
        logger.debug('╚═══════════════════════════════════════════')
    for line in stderr:
        line = line.strip('\n')
        if line:
            if first_error:
                logger.warning("╔════════════ WARN command: %s ═══════════════" % cmd)
                first_error = False
            logger.warning('║  ' + line.strip('\n'))
    if not first_error:
        logger.warning('╚═══════════════════════════════════════════')
    exit_status = stdout.channel.recv_exit_status()
    return exit_status, output


def ftp_pull(client_ssh, client_sftp, remote_path, local_dir, executable=False):
    if not os.path.exists(local_dir):
        os.makedirs(local_dir)
    local_path = os.path.join(local_dir, remote_path.split('/')[-1])
    if os.path.isfile(local_path):
        local_hash = md5(local_path)
        _, remote_hash = execute_remote(client_ssh, "md5sum %s| awk '{ print $1 }'" % remote_path)
        if local_hash == remote_hash:
            return
    client_sftp.get(remote_path, local_path)
    if executable:
        os.chmod(local_path, os.stat(local_path).st_mode | stat.S_IEXEC)


def ftp_push(client_ssh, client_sftp, file_name, local_dir, remote_dir, executable=False, del_before_push=False):
    local_path = os.path.join(local_dir, file_name)
    remote_path = os.path.join(remote_dir, file_name)
    remote_dir = os.path.dirname(remote_path)
    execute_remote(client_ssh, 'mkdir -p %s' % (remote_dir))
    local_hash = md5(local_path)
    _, remote_hash = execute_remote(client_ssh, "md5sum %s 2> /dev/null| awk '{ print $1 }'" % remote_path)
    if local_hash == remote_hash:
        return
    execute_remote(client_ssh, "[ -e %s ] && rm %s" % (remote_path, remote_path))
    client_sftp.put(local_path, remote_path)
    if executable:
        execute_remote(client_ssh, "chmod +x %s" % remote_path)


