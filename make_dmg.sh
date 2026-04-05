#!/bin/bash
#
# 漫画阅读器 - DMG 打包脚本
# 用法: bash make_dmg.sh
#
# 前置条件: dist/漫画阅读器.app 已存在（先 pyinstaller build.spec 打包）
#

set -e

APP_NAME="漫画阅读器"
APP_PATH="dist/${APP_NAME}.app"
DMG_NAME="${APP_NAME}"
DMG_FINAL="dist/${DMG_NAME}.dmg"
DMG_TEMP="dist/${DMG_NAME}_temp.dmg"
VOLUME_NAME="${APP_NAME}"
VOLUME_SIZE="80m"  # 留够余量

# 检查 app 是否存在
if [ ! -d "$APP_PATH" ]; then
    echo "❌ 错误: 找不到 $APP_PATH"
    echo "   请先运行: pyinstaller build.spec --distpath ./dist --workpath ./build --noconfirm"
    exit 1
fi

echo "📦 开始制作 DMG..."

# 清理旧文件
rm -f "$DMG_TEMP" "$DMG_FINAL"

# 1. 创建临时 DMG
echo "  → 创建临时磁盘映像..."
hdiutil create \
    -srcfolder "$APP_PATH" \
    -volname "$VOLUME_NAME" \
    -fs HFS+ \
    -fsargs "-c c=64,a=16,e=16" \
    -format UDRW \
    -size "$VOLUME_SIZE" \
    "$DMG_TEMP"

# 2. 挂载临时 DMG
echo "  → 挂载并配置..."
MOUNT_DIR=$(hdiutil attach -readwrite -noverify "$DMG_TEMP" | grep "/Volumes/" | sed 's/.*\/Volumes/\/Volumes/')

# 3. 添加 Applications 快捷方式（拖拽安装的关键）
ln -s /Applications "$MOUNT_DIR/Applications"

# 4. 设置 Finder 窗口样式（AppleScript）
echo "  → 设置窗口外观..."
osascript <<EOF
tell application "Finder"
    tell disk "$VOLUME_NAME"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set bounds of container window to {200, 120, 720, 400}
        set theViewOptions to the icon view options of container window
        set arrangement of theViewOptions to not arranged
        set icon size of theViewOptions to 80
        -- 摆放位置：app 在左边，Applications 在右边
        set position of item "${APP_NAME}.app" of container window to {130, 140}
        set position of item "Applications" of container window to {390, 140}
        close
        open
        update without registering applications
        delay 1
        close
    end tell
end tell
EOF

# 5. 设置权限
chmod -Rf go-w "$MOUNT_DIR" 2>/dev/null || true

# 6. 卸载
sync
hdiutil detach "$MOUNT_DIR" -quiet

# 7. 压缩为只读最终 DMG
echo "  → 压缩为最终 DMG..."
hdiutil convert "$DMG_TEMP" -format UDZO -imagekey zlib-level=9 -o "$DMG_FINAL"

# 8. 清理临时文件
rm -f "$DMG_TEMP"

# 完成
FINAL_SIZE=$(du -sh "$DMG_FINAL" | cut -f1)
echo ""
echo "✅ DMG 制作完成！"
echo "   文件: $DMG_FINAL"
echo "   大小: $FINAL_SIZE"
echo ""
echo "   用户双击打开 DMG → 把「${APP_NAME}」拖到 Applications → 完成安装"
