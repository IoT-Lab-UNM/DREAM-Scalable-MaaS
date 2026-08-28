cluster view:
%%%%%%%%%%%%%%
%%%%%%%%%%%%
echo "======================================================"
echo "      DREAM SCALABLE MaaS TESTBED - CLUSTER VIEW"
echo "======================================================"

echo
echo "===== KUBERNETES / KUBEEDGE NODES ====="
kubectl get nodes -o wide --show-labels

echo
echo "===== ALL RUNNING WORKLOADS ====="
kubectl get pods -A -o wide

echo
echo "===== ALL SERVICES / EXPOSED PORTS ====="
kubectl get svc -A -o wide

echo
echo "===== ALL DEPLOYMENTS ====="
kubectl get deployments -A -o wide

echo
echo "===== ALL DAEMONSETS ====="
kubectl get daemonsets -A -o wide

Microservices:
%%%%%%%%%%%%%%%%%%%%%
echo "===== MASTER NODE CONTROL PLANE ====="

kubectl -n kube-system get pods -o wide | \
grep -E 'kube-apiserver|etcd|kube-scheduler|kube-controller-manager'

Cloud MaaS orchestration layer:
%%%%%%%%%%%%%%
echo "======================================================"
echo "         DREAM CLOUD MaaS MICROSERVICES"
echo "======================================================"

kubectl -n dream-maas get pods,deployments,services -o wide

Show services and NodePorts:
%%%%%%%%%%%%%%%%%%%%
echo "===== MaaS SERVICE EXPOSURE ====="

kubectl -n dream-maas get svc \
  -o custom-columns='SERVICE:.metadata.name,TYPE:.spec.type,CLUSTER-IP:.spec.clusterIP,PORT:.spec.ports[*].port,NODEPORT:.spec.ports[*].nodePort'

monitoring services:
%%%%%%%%%%%%%%
echo "===== MONITORING SERVICES ====="

kubectl -n monitoring get svc \
  -o custom-columns='SERVICE:.metadata.name,TYPE:.spec.type,CLUSTER-IP:.spec.clusterIP,PORT:.spec.ports[*].port,NODEPORT:.spec.ports[*].nodePort'

KubeEdge Devices and Digital Twins:
%%%%%%%%%%%%%%%%%%%%%
echo "===== KUBEEDGE DEVICE MODELS ====="
kubectl get devicemodels -A

%%%%%%%%%%%%%%%%%%%%%%
echo "===== REGISTERED PHYSICAL DEVICES ====="
kubectl get devices -A -o wide

%%%%%%%%%%%%%%%%%%%%
echo "===== DIGITAL TWIN STATUS ====="
kubectl get devicestatus -A

show the printer twin:
%%%%%%%%%%%%%%%
echo "===== ENDER-3 DIGITAL TWIN ====="

kubectl get devicestatus ender3-printer-01 -n default -o json | \
jq -r '
  .status.twins[] |
  [.propertyName, .reported.value] | @tsv
'

RobotArm twin:
%%%%%%%%%%%
echo "===== ROBOTARM DIGITAL TWIN ====="

kubectl get devicestatus freenove-arm-01 -n default -o json | \
jq -r '
  .status.twins[] |
  [.propertyName, .reported.value] | @tsv
'

RobotArm physical edge stack:
%%%%%%%%%%%%
echo "======================================================"
echo "               ROBOTARM EDGE NODE"
echo "======================================================"

echo
echo "===== HOST ====="
hostname
hostname -I
uname -a

KubeEdge in robot:
%%%%%%%
echo "===== EDGECORE ====="

systemctl status edgecore --no-pager

Robot mapper:
%%%%%%%%%%
echo "===== DEVICE MAPPER ====="

systemctl status dream-device-mapper.service --no-pager

Freenove server:
%%%%%%%%%%
echo "===== PHYSICAL ROBOT SERVER ====="

systemctl status freenove-arm.service --no-pager

SDN setup in robot:
%%%%%%%%%%%%
echo "===== ROBOT SDN SERVICE ====="

systemctl status dream-robot-sdn.service --no-pager

RobotArm OVS:
%%%%%%%%%%%%%
echo "===== OVS BRIDGES ====="
sudo ovs-vsctl show

%%%%%%%%%
echo "===== BR-DREAM PORTS ====="
sudo ovs-ofctl -O OpenFlow13 show br-dream

%%%%%%%%%%%%%%
echo "===== ROBOT OPENFLOW TABLE ====="
sudo ovs-ofctl -O OpenFlow13 dump-flows br-dream

Robot network/listening services:
%%%%%%%%%%%%%%
echo "===== ROBOT LISTENING SERVICES ====="

sudo ss -lntup | \
grep -E ':1883|:5000|:9101|:9102'

3D-printer physical edge stack:
%%%%%%%%%%%%%%%%%
echo "======================================================"
echo "               ENDER-3 EDGE NODE"
echo "======================================================"

echo
echo "===== HOST ====="
hostname
hostname -I
uname -a

KubeEdge:
%%%%%%%%%
echo "===== EDGECORE ====="

systemctl status edgecore --no-pager

Printer mapper:
%%%%%%%%
echo "===== PRINTER DEVICE MAPPER ====="

systemctl status dream-printer-mapper.service --no-pager

SDN:
%%%%%%%
echo "===== PRINTER SDN SERVICE ====="

systemctl status dream-printer-sdn.service --no-pager

Printer OVS:
echo "===== PRINTER OVS ====="

sudo ovs-vsctl show

%%%%%%%%%%%%%%%
echo "===== PRINTER BR-DREAM ====="

sudo ovs-ofctl -O OpenFlow13 show br-dream

%%%%%%%%%%%%
Printer physical runtime:
%%%%%%%%%%%%%%%
echo "===== OCTOPRINT CONTAINER ====="

docker ps --filter name=octoprint

%%%%%%%%%%%%%%%%%%%%%%
echo "===== OCTOPRINT PORT ====="

sudo ss -lntup | grep ':5000'

serial hardware:
%%%%%%%%%%%
echo "===== PHYSICAL PRINTER SERIAL DEVICE ====="

ls -l /dev/ttyUSB*

Printer edge agents:
%%%%%%%%%%%%%%
echo "===== TELEMETRY ====="

curl -sS http://127.0.0.1:9101/metrics | \
grep '^dream_' | head -n 20

%%%%%%%%%%%%%%%%%
echo "===== SECURITY ====="

curl -sS http://127.0.0.1:9102/metrics | \
grep '^dream_' | head -n 20