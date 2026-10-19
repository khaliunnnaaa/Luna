#!/usr/bin/env bash
# AWS EC2 сервер үүсгэх (нэг удаа): m7i-flex.large (8GB, Free plan-д зөвшөөрөгдсөн) Ubuntu 24.04, 30GB, Docker.
# Түр демо: HOURS (default 48) цагийн дараа сервер өөрөө УНТРААД УСТАНА (диск, IP хамт) — төлбөр үргэлжлэхгүй.
# Хэрэглээ:  aws login  →  bash deploy/ec2-create.sh      (эрт устгах: bash deploy/ec2-destroy.sh)
# Гаралт: deploy/.instance (IP, instance id) — push.sh үүнийг уншина. SSH түлхүүр ~/.ssh/luna-key.pem.
set -euo pipefail
export AWS_REGION=${AWS_REGION:-ap-southeast-1}
NAME=luna
KEY=luna-key
KEY_FILE=~/.ssh/$KEY.pem
TYPE=${INSTANCE_TYPE:-m7i-flex.large}
HOURS=${HOURS:-48}
HERE=$(cd "$(dirname "$0")" && pwd)

if [ -f "$HERE/.instance" ]; then echo "deploy/.instance аль хэдийн бий — сервер үүссэн байна."; exit 1; fi

# 1) SSH түлхүүр
if ! aws ec2 describe-key-pairs --key-names $KEY >/dev/null 2>&1; then
  aws ec2 create-key-pair --key-name $KEY --query KeyMaterial --output text > "$KEY_FILE"
  chmod 400 "$KEY_FILE"
fi

# 2) Security group: SSH зөвхөн одоогийн IP-аас, HTTP/HTTPS бүгдэд
VPC=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=$NAME-web Name=vpc-id,Values=$VPC \
      --query 'SecurityGroups[0].GroupId' --output text)
if [ "$SG" = "None" ]; then
  SG=$(aws ec2 create-security-group --group-name $NAME-web --description "Luna web" --vpc-id "$VPC" \
        --query GroupId --output text)
  MYIP=$(curl -s https://checkip.amazonaws.com)
  aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 22 --cidr "$MYIP/32" >/dev/null
  aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 80 --cidr 0.0.0.0/0 >/dev/null
  aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 443 --cidr 0.0.0.0/0 >/dev/null
fi

# 3) Ubuntu 24.04 AMI, Docker + 2GB swap (torch build-д санах ой хүрэлцэхгүй байхаас сэргийлнэ)
AMI=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id \
       --query Parameter.Value --output text)
USERDATA=$(cat <<UD
#!/bin/bash
set -e
shutdown -h +$((HOURS * 60))   # shutdown-behavior=terminate тул устана
fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
# Ubuntu mirror sync үед apt update унадаг (2026-10-19 тохиолдсон) тул дахин оролдоно
for i in 1 2 3 4 5; do apt-get update -qq && break; sleep 20; done
for i in 1 2 3; do curl -fsSL https://get.docker.com | sh && break; sleep 20; done
usermod -aG docker ubuntu
apt-get install -y rsync
UD
)
ID=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$TYPE" --key-name $KEY \
      --security-group-ids "$SG" --user-data "$USERDATA" \
      --instance-initiated-shutdown-behavior terminate \
      --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=30,VolumeType=gp3}' \
      --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NAME}]" \
      --query 'Instances[0].InstanceId' --output text)
echo "Instance: $ID — асахыг хүлээж байна..."
aws ec2 wait instance-running --instance-ids "$ID"

# 4) Түр public IP (Elastic IP биш — устахад хамт чөлөөлөгдөнө)
IP=$(aws ec2 describe-instances --instance-ids "$ID" --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

printf 'IP=%s\nINSTANCE_ID=%s\nSG_ID=%s\nREGION=%s\n' "$IP" "$ID" "$SG" "$AWS_REGION" > "$HERE/.instance"
echo "Бэлэн: $IP ($HOURS цагийн дараа өөрөө устана)  → https://${IP//./-}.sslip.io"
echo "Docker суулгалт ~2 мин үргэлжилнэ. Дараа нь: bash deploy/push.sh"
