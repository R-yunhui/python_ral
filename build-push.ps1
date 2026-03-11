# 构建并推送 Docker 镜像（带时间戳与 git 短哈希标签）
# 用法: .\build-push.ps1

$ErrorActionPreference = "Stop"

# 可修改：镜像仓库地址（不含标签）
$REGISTRY_IMAGE = "hub.kaolayouran.cn:5000/dev/bisheng-generator"

# 生成标签：时间戳-短 commit（7 位）
$IMG_TAG = "$(Get-Date -Format 'yyyyMMddHHmmss')-$(git rev-parse --short=7 HEAD)"
$FULL_IMAGE = "${REGISTRY_IMAGE}:${IMG_TAG}"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Build & Push: $FULL_IMAGE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 构建
Write-Host "`n[1/2] Building..." -ForegroundColor Yellow
docker build -f dockerfile -t $FULL_IMAGE .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

# 推送
Write-Host "`n[2/2] Pushing..." -ForegroundColor Yellow
docker push $FULL_IMAGE
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "`nDone. Image: $FULL_IMAGE" -ForegroundColor Green
