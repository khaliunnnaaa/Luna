#!/usr/bin/env bash
# Демо дууссаны дараа AWS-с бүгдийг устгана: сервер (диск, IP хамт), security group, SSH түлхүүр.
# Хэрэглээ:  bash deploy/ec2-destroy.sh
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/.instance"
export AWS_REGION=$REGION
aws ec2 terminate-instances --instance-ids "$INSTANCE_ID" >/dev/null 2>&1 || true  # өөрөө устсан байж болно
aws ec2 wait instance-terminated --instance-ids "$INSTANCE_ID"
aws ec2 delete-security-group --group-id "$SG_ID"
aws ec2 delete-key-pair --key-name luna-key
rm -f ~/.ssh/luna-key.pem "$HERE/.instance"
echo "Устгагдлаа. Үлдсэн нөөц шалгах:"
aws ec2 describe-instances --filters Name=tag:Name,Values=luna \
  --query 'Reservations[].Instances[].[InstanceId,State.Name]' --output text
