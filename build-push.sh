#!/usr/bin/env bash
# 构建并推送 Docker 镜像（带时间戳与 git 短哈希标签）
# 用法: ./build-push.sh  或  bash build-push.sh

set -e

# 可修改：镜像仓库地址（不含标签）
REGISTRY_IMAGE="hub.kaolayouran.cn:5000/dev/bisheng-generator"

# 生成标签：时间戳-短 commit（7 位）
IMG_TAG="$(date +%Y%m%d%H%M%S)-$(git rev-parse --short=7 HEAD)"
FULL_IMAGE="${REGISTRY_IMAGE}:${IMG_TAG}"

echo "========================================"
echo "  Build & Push: $FULL_IMAGE"
echo "========================================"

# 构建
echo ""
echo "[1/2] Building..."
docker build -f dockerfile -t "$FULL_IMAGE" .

# 推送
echo ""
echo "[2/2] Pushing..."
docker push "$FULL_IMAGE"

echo ""
echo "Done. Image: $FULL_IMAGE"
