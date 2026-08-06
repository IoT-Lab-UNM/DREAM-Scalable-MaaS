# do not execute it as a shell file
sudo apt-get update
sudo apt-get install -y git make gcc g++ pkg-config
cd ~
git clone https://github.com/kubeedge/mapper-framework.git
cd mapper-framework
make generate