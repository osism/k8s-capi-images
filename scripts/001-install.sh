while fuser /var/lib/dpkg/lock >/dev/null 2>&1; do sleep 5; done;
while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; do sleep 5; done;

sudo apt-get update
sudo apt-get install -y qemu-kvm curl git software-properties-common make python3-pip patch

curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo apt-key add -
sudo apt-add-repository "deb [arch=amd64] https://apt.releases.hashicorp.com jammy main"
sudo apt-add-repository --yes --update ppa:ansible/ansible
sudo apt-get install -y ansible

wget -O packer-provisioner-goss.zip https://github.com/YaleUniversity/packer-provisioner-goss/releases/download/v3.1.3/packer-provisioner-goss-v3.1.3-linux-amd64.zip
unzip packer-provisioner-goss.zip -d /tmp
mkdir -p ~/.packer.d/plugins
mv /tmp/packer-provisioner-goss ~/.packer.d/plugins

# echo "Host *" >> /etc/ssh/ssh_config
# echo "    PubkeyAcceptedAlgorithms +ssh-rsa" >> /etc/ssh/ssh_config
# echo "    HostkeyAlgorithms +ssh-rsa" >> /etc/ssh/ssh_config
