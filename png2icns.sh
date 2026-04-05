#!/bin/bash
#
# 将 PNG 图片转换为 macOS .icns 图标文件
#
# 用法:
#   bash png2icns.sh input.png              # 输出到同目录下 input.icns
#   bash png2icns.sh input.png output.icns  # 指定输出路径
#
# 要求:
#   - macOS 系统（使用 sips + iconutil）
#   - 输入图片建议 1024x1024 或更大的正方形 PNG
#

set -e

# ========== 参数检查 ==========
if [ $# -lt 1 ]; then
    echo "用法: bash png2icns.sh <输入图片> [输出.icns]"
    echo "示例: bash png2icns.sh icon.png icon.icns"
    exit 1
fi

INPUT="$1"

if [ ! -f "$INPUT" ]; then
    echo "❌ 错误: 文件不存在: $INPUT"
    exit 1
fi

# 输出路径：默认与输入同名，后缀改为 .icns
if [ -n "$2" ]; then
    OUTPUT="$2"
else
    OUTPUT="${INPUT%.*}.icns"
fi

# ========== 创建临时 iconset 目录 ==========
ICONSET=$(mktemp -d)/icon.iconset
mkdir -p "$ICONSET"

echo "🎨 正在将 $INPUT 转换为 $OUTPUT ..."

# ========== 生成各尺寸图标 ==========
# macOS .icns 需要以下尺寸（含 @2x Retina 版本）
SIZES=(16 32 64 128 256 512 1024)

for SIZE in "${SIZES[@]}"; do
    # 标准分辨率
    if [ "$SIZE" -le 512 ]; then
        sips -z "$SIZE" "$SIZE" "$INPUT" --out "$ICONSET/icon_${SIZE}x${SIZE}.png" > /dev/null 2>&1
        echo "  ✓ ${SIZE}x${SIZE}"
    fi

    # @2x Retina 版本（实际像素是标称尺寸的两倍）
    HALF=$((SIZE / 2))
    if [ "$HALF" -ge 16 ] && [ "$HALF" -le 512 ]; then
        sips -z "$SIZE" "$SIZE" "$INPUT" --out "$ICONSET/icon_${HALF}x${HALF}@2x.png" > /dev/null 2>&1
        echo "  ✓ ${HALF}x${HALF}@2x (${SIZE}x${SIZE})"
    fi
done

# ========== 生成 .icns ==========
iconutil -c icns "$ICONSET" -o "$OUTPUT"

# ========== 清理临时文件 ==========
rm -rf "$(dirname "$ICONSET")"

# ========== 完成 ==========
FILE_SIZE=$(du -sh "$OUTPUT" | cut -f1)
echo ""
echo "✅ 转换完成！"
echo "   输出: $OUTPUT"
echo "   大小: $FILE_SIZE"
