"""界面翻译；配置键、枚举值、文件内容和用户输入保持原样。"""

from __future__ import annotations

_language = "zh_CN"


def set_language(language: str):
    """启动时设置语言，切换语言后重启以重建全部窗口。"""
    global _language
    _language = language if language in ("zh_CN", "en") else "zh_CN"


def tr(text: str) -> str:
    """翻译完整文案模板；调用方在翻译之后填入用户数据。"""
    return text if _language == "en" else TEXT.get(text, text)


def option_label(name: str) -> str:
    """格式化配置标签，原始英文键仍可用于搜索及核对。"""
    if _language == "en":
        return name
    if name in TEXT:
        return TEXT[name]
    return "".join(WORDS.get(word.lower(), word) for word in name.split())


TEXT = {
    "Driving Data Recorder": "驾驶数据记录与导出", "Browse": "浏览",
    "Driver / nickname": "驾驶者 / 昵称", "Comparison label": "本组对照名称",
    "Output folder": "输出目录", "Optional setup file": "调教文件（可选）",
    "Sampling interval": "采样间隔", "Notes": "备注",
    "Start Recording": "开始记录", "Stop Recording": "停止记录",
    "Export Analysis ZIP": "导出分析包 ZIP", "Ready to record": "准备记录",
    "Recording: {0} samples": "正在记录：{0} 条采样",
    "Stopped: {0} samples ({1})": "记录已结束：{0} 条采样（{1}）",
    "Describe setup changes, tyres, fuel, weather and the handling problem.": "请注明调教变化、轮胎、燃油、天气，以及想改善的驾驶现象。",
    "Recording starts only when requested. Pauses and missing data are not filled with zeros. Closing this window or changing the API stops recording.": "点击开始后才会记录。暂停和缺失数据不会补零；关闭此窗口或切换接口会结束当前记录。",
    "Recording failed. Partial files are kept in the output folder.": "记录失败，已经写入的文件保留在输出目录中。",
    "A recording is already running": "已有一轮记录正在进行。",
    "Please enter a driver name": "请填写驾驶者名称或昵称。",
    "Please choose an output folder": "请选择输出目录。",
    "Sampling interval must be 10..1000 ms": "采样间隔应为 10–1000 毫秒。",
    "No active telemetry. Start driving and check the API settings.": "没有有效遥测，请进入驾驶并核对接口设置。",
    "Select a .set or .svm setup file": "请选择 .set 或 .svm 调教文件。",
    "Setup file must be smaller than 16 MiB": "调教文件应不超过 16 MiB。",
    "Stop a recording before exporting": "请先结束记录，再导出分析包。",
    "Use a .zip filename": "请使用 .zip 扩展名保存分析包。",
    "user_stopped": "手动结束", "window_closed": "记录窗口已关闭",
    "api_stopped": "接口已停止或切换", "context_changed": "赛道、车辆或驾驶者发生变化",
    "failed": "记录失败",
    "Track Length": "赛道长度（米，人工填写）",
    "Steering Range": "方向盘总转角（度，人工填写）",
    "Engine RPM Max": "发动机最高转速（RPM，人工填写）",
    "Fuel Capacity": "油箱容量（升，人工填写）",
    "Outsim Port": "OutSim UDP 端口", "Outgauge Port": "OutGauge UDP 端口",
    "Enabled": "已启用", "Disabled": "已禁用", "Auto": "自动", "Off": "关闭",
    "overriding": "强制显示", "N/A": "不可用", "Show History": "显示历史",
    "Show Map": "显示地图", "Saved": "已保存", "Exported": "已导出",
    "Data Imported": "已导入数据", "Transfer Completed": "迁移完成",
    "Delete Preset": "删除预设", "Duplicate Preset": "复制预设", "Rename Preset": "重命名预设",
    "Lock Preset": "锁定预设", "Unlock Preset": "解锁预设", "Restore Style Preset": "恢复样式预设",
    "Create new default preset": "新建默认预设", "Reset Options": "重置选项",
    "Incorrect Tyre Allocation": "轮胎分配错误",
    "No data found.": "没有找到数据。", "No data selected.": "尚未选择数据。",
    "No lap time found.": "没有找到圈速。", "No tyre selected.": "尚未选择轮胎。",
    "Nothing to save.": "没有需要保存的内容。", "No backup file selected.": "尚未选择备份。",
    "No destination preset selected or found.": "尚未选择目标预设，或目标不存在。",
    "Invalid file name.": "文件名不合法。", "Invalid name.": "名称不合法。",
    "Invalid preset name.": "预设名称不合法。", "Invalid tyre name.": "轮胎名称不合法。",
    "Preset already exists.": "预设已经存在。", "Failed to create backup, please try again.": "备份创建失败，请重试。",
    "Cannot delete built-in heatmap preset.": "无法删除内置热图预设。",
    "Cannot reset selected heatmap preset.<br><br>Default preset does not exist.": "无法重置所选热图，默认预设不存在。",
    "Cannot import selected file.<br><br>Invalid vehicle data file.": "无法导入所选文件，车辆数据格式不合法。",
    "Cannot open selected file.<br><br>Invalid notes file.": "无法打开所选文件，笔记格式不合法。",
    "Cannot open selected file.<br><br>Invalid tyre strategy file.": "无法打开所选文件，轮胎策略格式不合法。",
    "Cannot set speed trap position while in pit lane.": "在维修区时无法设置测速点位置。",
    "Selected backup file is invalid and cannot be restored.": "所选备份不合法，无法恢复。",
    "No option type selected.<br><br>Select at least one option type and try again.": "请至少选择一种选项类型后重试。",
    "No preset setting selected.<br><br>Select at least one setting and try again.": "请至少选择一项预设设置后重试。",
    "Clear all log?": "清空全部日志吗？", "Copied all log to Clipboard.": "已将全部日志复制到剪贴板。",
    "Clear all key bindings?<br><br>This cannot be undone!": "清空全部快捷键绑定吗？<br><br>此操作无法撤销。",
    "<b>Delete selected row?</b>": "<b>删除所选行吗？</b>",
    "<b>Delete selected rows?</b>": "<b>删除所选行吗？</b>",
    "<b>Delete selected temperature?</b>": "<b>删除所选温度吗？</b>",
    "<b>Remove all tyres from list?</b><br><br>All allocated tyres will be removed from table.": "<b>移除列表中的全部轮胎吗？</b><br><br>表中已分配的轮胎也会移除。",
    "<b>Remove selected tyre from list?</b><br><br>Corresponding tyre will be removed from table.": "<b>移除所选轮胎吗？</b><br><br>表中对应轮胎也会移除。",
    "<b>Remove selected tyre from table?</b>": "<b>从表中移除所选轮胎吗？</b>",
    "Vehicle brand data imported.": "车辆品牌数据已导入。",
    "Scale: {0}{1}": "缩放：{0}{1}", "About {0}": "关于 {0}",
    "Spectating: <b>{0}</b>": "观战：<b>{0}</b>", "Playback Volume: {0}%": "播报音量：{0}%",
    "Key Binding - {0}": "快捷键绑定 - {0}", "{0} Keybinding": "{0} 快捷键绑定",
    "Version {0}": "版本 {0}", "Changes: {0}": "变更：{0}",
    "Pits: {0}": "进站：{0}", "Stints: {0}": "驾驶段：{0}",
    "Stock: {0} / {1}{2}": "库存：{0} / {1}{2}", "Used: {0}": "已使用：{0}",
    "Time: {0:+.2f}s": "时间：{0:+.2f} 秒", "{0} Name": "{0} 名称",
    "Select {0}": "选择 {0}", "Reset {0}": "重置 {0}", "From: <b>{0}</b>": "来源：<b>{0}</b>",
    "Notes saved at:<br><b>{0}</b>": "笔记已保存到：<br><b>{0}</b>",
    "Backup saved as:<br><b>{0}{1}</b>": "备份已保存为：<br><b>{0}{1}</b>",
    "Tyre strategy file exported at:<br><b>{0}</b>": "轮胎策略已导出到：<br><b>{0}</b>",
    "Tyre strategy file saved at:<br><b>{0}</b>": "轮胎策略已保存到：<br><b>{0}</b>",
    "Cannot find track map for<br><b>{0}</b><br>": "没有找到对应赛道地图：<br><b>{0}</b><br>",
    "Already opened <b>{0} dialog</b>.<br><br>Please close previous dialog first.": "<b>{0}</b> 窗口已经打开，请先关闭已有窗口。",
    "<b>{0}</b> all {1}s?": "<b>{0}</b>全部{1}吗？",
    "{0} <b>Overlay Combined Mode</b>?<br><br>{1}": "{0}<b>叠加层合并显示</b>吗？<br><br>{1}",
    "{0} <b>High DPI Scaling</b> and restart <b>TinyPedal</b>?<br><br><b>Window</b> and <b>Overlay</b> size and position will {1}": "{0}<b>高 DPI 缩放</b>并重启 <b>TinyPedal</b> 吗？<br><br><b>窗口</b>和<b>叠加层</b>的大小及位置将{1}",
    "be auto-scaled according to system DPI scaling setting.": "根据系统 DPI 设置自动缩放。",
    "not be scaled under high DPI screen resolution.": "保持原始像素大小。",
    "Lock <b>{0}</b> preset?<br><br>Changes to locked preset will not be saved.": "锁定 <b>{0}</b> 预设吗？<br><br>锁定期间的修改不会保存。",
    "Unlock <b>{0}</b> preset?": "解锁 <b>{0}</b> 预设吗？",
    "Create a backup file for <b>{0}</b> preset?<br><br>Backup file can be restored by click 'Restore' button.": "为 <b>{0}</b> 创建备份吗？<br><br>之后可以通过“恢复”按钮还原。",
    "Delete <b>{0}</b> preset permanently?<br><br>This cannot be undone!": "永久删除 <b>{0}</b> 预设吗？<br><br>此操作无法撤销。",
    "Delete <b>{0}</b> preset?<br><br>Changes are only saved after clicking Apply or Save Button.": "删除 <b>{0}</b> 预设吗？<br><br>点击“应用”或“保存”后生效。",
    "Delete all stats from<br><b>{0}</b> ?<br><br>This cannot be undone!": "删除 <b>{0}</b> 的全部统计吗？<br><br>此操作无法撤销。",
    "Remove all stats from <b>{0}</b>?<br><br>This cannot be undone!": "移除 <b>{0}</b> 的全部统计吗？<br><br>此操作无法撤销。",
    "Reset <b>{0}</b> data for<br><b>{1}</b> ?<br><br>This cannot be undone!": "重置 <b>{1}</b> 的 <b>{0}</b> 数据吗？<br><br>此操作无法撤销。",
    "Reset <b>{0}</b> lap time for <b>{1}</b>?<br><br>This cannot be undone!": "重置 <b>{1}</b> 的 <b>{0}</b> 圈速吗？<br><br>此操作无法撤销。",
    "{0} data has been reset for<br><b>{1}</b>": "已重置 <b>{1}</b> 的 {0} 数据。",
    "No {0} data found.<br><br>You can only reset data from active session.": "没有找到 {0} 数据。<br><br>只能重置当前会话的数据。",
    "Select all {0}s from list?": "选中列表中的全部{0}吗？", "Deselect all {0}s from list?": "取消选中全部{0}吗？",
    "Set position at <b>{0}</b> {1}?": "将位置设为 <b>{0}</b> {1} 吗？",
    "Set speed trap at position <b>{0}</b><br>for <b>{1}</b>?": "将 <b>{1}</b> 的测速点设在 <b>{0}</b> 吗？",
    "Settings are transferred from <b>{0}</b> to <b>{1}</b>.": "已将设置从 <b>{0}</b> 迁移到 <b>{1}</b>。",
    "Transfer selected settings from <b>{0}</b> to <b>{1}</b>?<br><br>This cannot be undone!": "将所选设置从 <b>{0}</b> 迁移到 <b>{1}</b> 吗？<br><br>此操作无法撤销。",
    "<b>{0}</b> already used for <b>{1}</b>.<br><br>Are you sure to assign the same key anyway?": "<b>{0}</b> 已绑定到 <b>{1}</b>，仍要重复使用吗？",
    "<b>{0}</b> already installed on <b>{1}</b> wheel.<br><br>Cannot install the same tyre on two wheels at the same time.": "<b>{0}</b> 已安装在 <b>{1}</b>，同一轮胎不能同时装在两个车轮上。",
    "<b>{0}</b> already used on <b>{1}</b> wheel.<br><br>Cannot allocate already used tyre on a different wheel.": "<b>{0}</b> 已用于 <b>{1}</b>，无法分配到其他车轮。",
    "<b>{0}</b> is a style preset.<br>Restoring this backup file will overwrite existing style preset.<br><br>Are you sure you want to restore and overwrite existing style preset?<br><br>This cannot be undone!": "<b>{0}</b> 是样式预设，恢复会覆盖现有内容。<br><br>确定恢复吗？此操作无法撤销。",
    "Unable to import vehicle data from {0} Rest API.<br><br>Make sure game is running and try again.": "无法从 {0} REST API 导入车辆数据。<br><br>请确认游戏正在运行后重试。",
    "Unable to load track map file from<br><b>{0}{1}{2}</b><br><br>Only support SVG file that generated with TinyPedal.": "无法加载地图：<br><b>{0}{1}{2}</b><br><br>仅支持 TinyPedal 生成的 SVG 文件。",
    "Unable to set speed trap position for selected track:<br><b>{0}</b><br><br>Only support to set speed trap position for current track:<br><b>{1}</b>": "无法设置所选赛道 <b>{0}</b> 的测速点。<br><br>只能设置当前赛道 <b>{1}</b>。",
    "Select <b>one or more values</b> from <b>distance</b> column to apply offset.": "请在<b>距离</b>列选择一个或多个值，再应用偏移。",
    "Select <b>one or more values</b> from <b>temperature</b> column to apply offset.": "请在<b>温度</b>列选择一个或多个值，再应用偏移。",
    "Select <b>one value</b> from <b>Speed trap</b> column to set position.": "请在<b>测速点</b>列选择一个值以设置位置。",
    "Select <b>one value</b> from <b>distance</b> column to set position.": "请在<b>距离</b>列选择一个值以设置位置。",
    "Widget": "仪表组件", "Module": "数据模块", "Preset": "预设",
    "Spectate": "观战", "Pacenotes": "路书", "Hotkey": "快捷键",
    "Overlay": "叠加显示", "Config": "设置", "Tools": "工具",
    "Window": "窗口", "Help": "帮助", "File": "文件", "Info": "信息",
    "About": "关于", "Contributors": "贡献者", "License": "许可证",
    "Third-Party Notices": "第三方声明", "Application": "应用设置",
    "Compatibility": "兼容性", "Notification": "通知", "Units": "单位",
    "User Path": "用户数据路径", "Global Font Override": "全局字体覆盖",
    "Open Folder": "打开文件夹", "Options": "选项", "Quit": "退出",
    "Reload": "重新加载", "Refresh": "刷新", "Save": "保存",
    "Save As": "另存为", "Save As...": "另存为…", "Apply": "应用",
    "Cancel": "取消", "Close": "关闭", "Ok": "确定", "OK": "确定",
    "Yes": "是", "No": "否", "&Yes": "是", "&No": "否",
    "&Save": "保存", "&Cancel": "取消", "&Close": "关闭",
    "Discard": "放弃", "Error": "错误", "Warning": "提示", "Confirm": "确认",
    "Add": "添加", "Delete": "删除", "Remove": "移除", "Replace": "替换",
    "Reset": "重置", "Sort": "排序", "Copy": "复制", "New": "新建",
    "Open": "打开", "Clear": "清空", "Clear All": "全部清空",
    "Duplicate": "创建副本", "Rename": "重命名", "Transfer": "迁移",
    "Restore": "恢复", "Restore Backup": "恢复备份", "Backup Preset": "备份预设",
    "Preset Transfer": "迁移预设", "Enter a new preset name": "请输入新预设名称",
    "Enable All": "全部启用", "Disable All": "全部禁用", "Enable": "启用",
    "Disable": "禁用", "ON": "开", "OFF": "关", "None": "无", " All ": " 全部 ",
    "Lock Overlay": "锁定叠加层位置", "Auto Hide": "自动隐藏",
    "Grid Move": "按网格移动", "VR Compatibility": "VR 兼容模式",
    "Combined Mode": "合并显示模式", "Overlay Combined Mode": "叠加层合并显示",
    "Reset Data": "重置数据", "Delta Best": "最佳圈时间差",
    "Energy Delta": "能量消耗差", "Fuel Delta": "燃油消耗差",
    "Consumption History": "消耗历史", "Sector Best": "最佳分段",
    "Track Map": "赛道地图", "Restart API": "重启遥测接口",
    "Restart TinyPedal": "重启 TinyPedal", "Show at Startup": "启动时显示窗口",
    "Minimize to Tray": "最小化到托盘", "Remember Position": "记住窗口位置",
    "Remember Size": "记住窗口大小", "Show Log": "查看日志", "Log": "日志",
    "Auto Refresh": "自动刷新", "Check for Updates": "检查更新",
    "Frequently Asked Questions": "常见问题", "User Guide": "使用指南",
    "Remember API Selection from Preset": "从预设恢复游戏接口选择",
    "Enable Legacy API Selection": "显示旧版游戏接口",
    "Enable Auto Backup Car Setup": "自动备份车辆调教",
    "Config Telemetry API": "配置遥测接口",
    "Toggle Window Color Theme": "切换窗口配色", "Toggle High DPI Scaling": "切换高 DPI 缩放",
    "High DPI Scaling": "高 DPI 缩放", "Center Horizontally": "水平居中",
    "Center Vertically": "垂直居中", "Reset to Default": "恢复默认值",
    "Fuel Calculator": "燃油计算器", "Tyre Strategy Planner": "轮胎策略规划",
    "Driver Stats Viewer": "驾驶统计", "Track Map Viewer": "赛道地图查看器",
    "Heatmap Editor": "热图编辑器", "Brake Editor": "刹车编辑器",
    "Tyre Compound Editor": "轮胎配方编辑器", "Vehicle Brand Editor": "车辆品牌编辑器",
    "Vehicle Class Editor": "车辆组别编辑器", "Track Info Editor": "赛道信息编辑器",
    "Track Notes Editor": "赛道笔记编辑器", "Display Order": "显示顺序",
    "Click & Drag to Reorder Display": "拖动条目调整显示顺序",
    "Configure Display Order": "调整显示顺序", " Type here to search options": " 输入中文或英文配置键搜索",
    "Font Name": "字体名称", "Font Size Addend": "字号增量", "Font Weight": "字重",
    "Enable Auto Font Offset": "自动调整字体偏移", "Font Offset Vertical Addend": "字体垂直偏移增量",
    "Preset Locked": "预设已锁定", "Spectate Mode Enabled": "观战模式已启用",
    "Global Hotkey Enabled": "全局快捷键已启用", "Global Hotkey Unavailable": "全局快捷键不可用",
    "Auto Backup Car Setup Enabled": "车辆调教自动备份已启用",
    "Auto Backup Car Setup Unavailable": "车辆调教自动备份不可用",
    "Pace Notes Playback Enabled": "路书播报已启用", "Checking For Updates...": "正在检查更新…",
    "View Updates On GitHub": "在 GitHub 查看更新", "Dismiss": "关闭通知",
    "  Playback Disabled  ": "  播报已关闭  ", "  Playback Enabled  ": "  播报已启用  ",
    "Enable Playback While Spectating": "观战时播报", "Enable Playback While in Pit Lane": "在维修区播报",
    "Global Offset:": "全局偏移：", "Maximum Duration:": "最长时长：",
    "Maximum Queue:": "最大队列：", "Manually Select Pace Notes File": "手动选择路书文件",
    "Playback Volume: 0%": "播报音量：0%", "Sound File Path:": "音频文件路径：", "Sound Format:": "音频格式：",
    "Spectating: <b>Disabled</b>": "观战：<b>已关闭</b>", "Auto Load Primary Preset": "自动加载首选预设",
    "Clear Primary Tag": "清除首选标记", "Set Primary for Class": "设为本组别首选",
    "Add Selected Data": "添加选中数据", "Fuel Usage": "燃油消耗", "Hide History": "隐藏历史",
    "Lap Time:": "圈速：", "Load File": "从文件读取", "Load Live": "读取当前遥测",
    "Wear Rate": "磨损率", "Remove Vehicle": "移除车辆", "Reset Lap Time": "重置圈速", "View Map": "查看地图",
    "Offset": "偏移", "Nodes:": "节点数：", "Position:": "位置：", "Zoom:": "缩放：",
    "Load Map": "加载地图", "Reset Map View": "重置地图视图", "Reset Map Zoom": "重置地图缩放",
    "Track Map Name": "赛道地图名称", "Set from Telemetry": "从遥测填入", "Set from Map": "从地图填入",
    "Add Tag": "添加标记", "Clear Tag": "清除标记", "Delete Rows": "删除行",
    "From Map": "从地图读取", "From Telemetry": "从遥测读取", "Hide Map": "隐藏地图",
    "Highlight on Map": "在地图中标出", "Insert": "插入", "Insert Row Above": "在上方插入行",
    "Insert Row Below": "在下方插入行", "Metadata Info": "元数据", "New Pace Notes": "新建路书",
    "New Track Notes": "新建赛道笔记", "Open Pace Notes": "打开路书", "Open Track Notes": "打开赛道笔记",
    "Pit": "维修区", "Set Pos": "设置位置", "Change Time": "更换耗时", "Compound Type": "轮胎配方",
    "Delete Row": "删除行", "Duplicate Row": "复制行", "Export As...": "导出为…",
    "Highlight New Tyre": "突出显示新胎", "Insert Above": "在上方插入", "Insert Below": "在下方插入",
    "Maximum Tyres": "轮胎数量上限", "New File": "新建文件", "New Row": "新建行",
    "Number of Stints": "驾驶段数", "Open File": "打开文件", "Remove Selected": "移除所选",
    "Restrict Allocation": "限制配额", "Sort By": "排序依据", "Import from": "导入来源",
    "JSON file": "JSON 文件", "Batch Offset": "批量偏移", "Batch Replace": "批量替换",
    "Column:": "列：", "Find:": "查找：", "Last Offset:": "上次偏移：", "Last Scale:": "上次缩放：",
    "Match Case": "区分大小写", "Match Whole Word": "匹配完整词", "Replace:": "替换为：", "Scale Mode": "缩放模式",
    "To:": "目标：", "Language (restart)": "界面语言（重启生效）",
    "<b>Save changes before continue?</b>": "<b>继续前保存修改吗？</b>",
    "Each <b>Widget</b> will be displayed in separate window.": "每个<b>仪表组件</b>会显示在独立窗口中。",
    "All <b>Widgets</b> will be combined and drawn in one single maximized window.": "全部<b>仪表组件</b>会合并绘制到一个最大化窗口中。",
    "Enabled: <b>{0}/{1}</b>": "已启用：<b>{0}/{1}</b>",
    "Loaded: <b>{0}{1}</b>": "当前预设：<b>{0}{1}</b>",
    "Invalid value for <b>{0}</b> option.<br><br>Changes are not saved.": "<b>{0}</b> 的值不合法。<br><br>修改尚未保存。",
    "Reset all <b>{0}</b> options to default?<br><br>Changes are only saved after clicking Apply or Save Button.": "将 <b>{0}</b> 全部恢复默认值吗？<br><br>点击“应用”或“保存”后才会保存修改。",
    "Cannot open folder:<br><b>{0}</b>": "无法打开文件夹：<br><b>{0}</b>",
    " (locked)": "（已锁定）",
    "Track name": "赛道名称", "Pit entry (m)": "维修区入口（米）", "Pit exit (m)": "维修区出口（米）",
    "Pit speed (m/s)": "维修区限速（米/秒）", "Speed trap (m)": "测速点（米）", "Orient (°)": "朝向（度）",
    "Sunrise": "日出", "Sunset": "日落", "Compound": "轮胎配方", "Vehicle": "车辆", "Class": "组别",
    "Brand": "品牌", "Heatmap": "热图", "Qualifying": "排位赛", "Race": "比赛", "Hours": "小时",
    "Finishes": "完赛次数", "Meters": "米", "Liters": "升", "Gallons": "加仑", "Miles": "英里",
}

for _preset, _label in (("brakes", "刹车"), ("brands", "品牌"), ("classes", "组别"),
                        ("compounds", "轮胎配方"), ("tracks", "赛道"), ("{0}", "{0}")):
    _source = ("Reset <b>" + _preset + (" preset" if _preset != "{0}" else "") +
               "</b>" + ("" if _preset != "{0}" else " preset") +
               " to default?<br><br>Changes are only saved after clicking Apply or Save Button.")
    TEXT[_source] = "将 <b>" + _label + "</b> 预设恢复默认值吗？<br><br>点击“应用”或“保存”后生效。"
TEXT["Reset <b>Display Order</b> to default?<br><br>Changes are only saved after clicking Apply Button."] = "恢复默认显示顺序吗？<br><br>点击“应用”后生效。"

# 配置标签采用集中词表，专用术语可在 TEXT 中覆盖。
WORDS = dict(pair.split("=", 1) for pair in """
above=上方 absolute=绝对 ackermann=阿克曼 activated=已触发 activation=触发 actual=实际
additional=附加 aero=空气动力 ahead=前车 alias=别名 all=全部 allocation=分配 allowed=允许
ambient=环境 and=及 animated=动画 arb=防倾杆 area=区域 arrow=箭头 as=作为 at=在
available=可用 axle=车轴 baseline=基准 behind=后车 below=下方 bind=绑定 blue=蓝色
body=车身 bottoming=触底 break=中断 bump=压缩 by=按 bypass=绕过 calculator=计算器
calm=无风 capacity=容量 caption=标题 car=车辆 chance=概率 change=变化 charge=充电
check=检查 classes=组别 classification=分类 cliff=性能骤降 clipping=截幅 closed=关闭
cold=冷态 collision=碰撞 comments=备注 compass=罗盘 cone=锥形 consistency=一致性
constant=常量 cooldown=冷却 coordinates=坐标 countdown=倒计时 course=赛程 coverage=覆盖率
critical=临界 cross=交叉 cruise=巡航 custom=自定义 cut=切弯 dark=深色 data=数据
day=白天 debugging=调试 decimal=小数 decreasing=递减 degree=度 deltalast=上圈差值
density=密度 detached=脱落 detail=详情 deviation=偏差 difference=差异 dimension=尺寸
disqualify=取消资格 distribution=分布 dot=点 double=双 downforce=下压力 drive=驱动
drop=下降 dry=干地 each=各 early=提前 edge=边缘 elevation=海拔 elms=ELMS empty=空
end=结束 entry=入口 exclusive=独占 exit=出口 exponential=指数 extended=扩展 extra=额外
extreme=极端 extremely=极其 fade=衰退 faster=更快 fastest=最快 field=阵容 fields=阵容
fixed=固定 flash=闪烁 flashes=闪烁次数 flat=平缓 flickering=闪烁 for=用于 forecast=预报
forecasts=预报 formatted=格式化 frames=帧 freeze=冻结 from=来源 full=完整 gale=大风
garage=车库 gauge=仪表 gear=挡位 gentle=轻微 go=行驶 grade=等级 gravitational=重力
green=绿色 gte=GTE hairpin=发卡弯 head=前端 headlights=车灯 heavy=强 highest=最高
highlight=突出显示 highlighted=高亮 hot=热态 hotlap=热圈 hyper=Hyper hypercar=Hypercar
icon=图标 if=如果 ignition=点火 image=图像 impact=碰撞 in=内 inactive=非活动 incidents=事故
increasing=递增 increment=增量 info=信息 instead=替代 into=进入 inverted=反向 lane=通道
language=语言 lateral=横向 layer=层 layout=布局 leader=领跑者 leading=前导 lengthy=较长
less=较少 level=级别 lifespan=寿命 liftforce=升力 light=浅色 lights=灯号 limits=限制
live=实时 lock=锁定 locking=抱死 logo=标志 long=长 longitudinal=纵向 loss=损失
lower=下限 major=主 manager=管理器 manual=手动 mark=标记 marked=已标记 matching=匹配
measurement=测量 median=中位数 medium=中等 migration=迁移 minor=次 minutes=分钟
mixed=混合 moderate=中等 more=更多 motion=运动 move=移动 multi=多 multiplier=倍数
near=近 nearby=附近 nearest=最近 negative=负 net=净值 neutral=空挡 night=夜间 node=节点
none=无 normal=普通 north=北 not=不 notify=通知 occupancy=占用 odometer=里程表
of=的 off=关 offroad=驶离路面 on=开 only=仅 option=选项 orientation=朝向
osculating=密切圆 others=其他 out=出 over=超出 overall=全场 overheat=过热 overlap=重叠
oversteer=转向过度 parts=部件 password=密码 paused=暂停 peak=峰值 per=每
performance=性能 phase=阶段 pitout=出站 pitstop=进站 places=名次 planner=规划器
platform=平台 players=玩家 plugin=插件 podium=领奖台 points=点数 positive=正
power=功率 practice=练习 predicted=预测 private=私人 progression=进度 proximity=接近
puncture=爆胎 qualify=排位 radius=半径 raininess=降雨量 rate=速率 reading=读数
readings=读数 rebound=回弹 recent=最近 red=红色 redline=红线 reduction=减少
refill=补充 refilling=补充中 refueling=加油 repairs=维修 requested=已请求 requests=请求
reserve=预留 restapi=REST接口 rev=转速 rubber=橡胶 safe=安全 safety=安全 same=相同
sampling=采样 scaled=缩放后 scheduled=计划 section=区段 sectors=分段 selector=选择器
setup=调教 setups=调教 shape=形状 short=短 shorten=缩短 side=侧 sign=符号 single=单
slope=坡度 slower=更慢 source=来源 spacing=间距 spectate=观战 spectating=观战中
speeding=超速 spot=位置 spring=弹簧 stalling=熄火 start=开始 starting=起始
stationary=静止 steep=陡坡 steer=转向 step=步长 stopped=已停止 storm=暴雨
straight=直道 strategy=策略 strength=强度 strong=强 styling=样式 suffix=后缀
sunlight=日照 sunrise=日出 sunset=日落 swap=交换 symbol=符号 symmetric=对称
synchronization=同步 system=系统 tail=尾部 tank=油箱 testday=测试 thickness=厚度
third=第三 through=通过 timer=计时器 tinypedal=TinyPedal to=至 totaled=全损 trace=轨迹
trailing=尾随 transient=瞬态 trap=测速点 trend=趋势 turning=转弯 type=类型 udp=UDP
under=低于 understeer=转向不足 unfiltered=未滤波 unsprung=簧下 updates=更新
upper=上限 uppercase=大写 url=URL usage=用量 vehicles=车辆 version=版本 very=很
view=视图 viewer=查看器 virtual=虚拟 vr=VR warmup=暖胎 wet=湿地 wheelbase=轴距
wheels=车轮 while=期间 wiper=雨刷 without=不含 yaw=横摆 yellow=黄色
enable=启用 show=显示 hide=隐藏 auto=自动 global=全局 default=默认
update=更新 interval=间隔 idle=空闲 minimum=最小 maximum=最大 active=活动
font=字体 name=名称 size=大小 weight=字重 offset=偏移 vertical=垂直 horizontal=水平
color=颜色 background=背景 foreground=前景 border=边框 width=宽度 height=高度
position=位置 left=左 right=右 front=前 rear=后 top=上 bottom=下 center=中心
text=文字 label=标签 title=标题 alignment=对齐 margin=边距 padding=内边距
widget=仪表 module=模块 application=应用 compatibility=兼容性 notification=通知
overlay=叠加层 preset=预设 telemetry=遥测 api=API units=单位 user=用户 path=路径
brake=刹车 braking=制动 bias=平衡 pressure=压力 temperature=温度 wear=磨损 compound=配方
tyre=轮胎 wheel=车轮 engine=发动机 motor=电机 electric=电动 battery=电池
fuel=燃油 energy=能量 consumption=消耗 delta=差值 best=最佳 last=上次 current=当前
lap=单圈 laps=圈数 laptime=圈速 time=时间 timing=计时 elapsed=已用 remaining=剩余
sector=分段 session=会话 stint=驾驶段 history=历史 driver=驾驶者 vehicle=车辆
class=组别 brand=品牌 model=型号 speed=速度 acceleration=加速度 force=力 torque=扭矩
steering=转向 throttle=油门 clutch=离合 pedal=踏板 suspension=悬架 travel=行程
deflection=压缩量 load=负载 camber=外倾角 toe=束角 slip=滑移 angle=角度 ratio=比率
track=赛道 map=地图 distance=距离 length=长度 progress=进度 heading=航向 navigation=导航
relative=相对位置 rivals=对手 standings=排名 radar=雷达 traffic=交通 flag=旗号
pit=维修区 stop=停车 stops=停车次数 estimate=估计 request=请求 limiter=限速器
qualifying=排位赛 qualification=排位 race=比赛 finish=完赛 status=状态 penalty=处罚
damage=损伤 integrity=完整度 friction=摩擦 circle=圆 roll=侧倾 rake=前后倾差
ride=车身 water=冷却液 oil=机油 turbo=涡轮 exhaust=排气
rotation=转动 range=范围 raw=原始 filtered=滤后 smoothing=平滑 samples=样本
value=数值 warning=警告 threshold=阈值 limit=上限 scale=比例 factor=系数
display=显示 order=顺序 row=行 column=列 gap=间隔 grid=网格 snap=吸附
locked=已锁定 primary=首选 backup=备份 settings=设置 config=配置 setting=设置
remember=记住 startup=启动 minimize=最小化 tray=托盘 window=窗口 theme=主题
high=高 low=低 dpi=DPI scaling=缩放 selection=选择 legacy=旧版 access=访问 mode=模式
character=字符 encoding=编码 connection=连接 timeout=超时 retry=重试 delay=延迟
host=主机 port=端口 memory=内存 prefix=前缀 process=进程 id=ID override=覆盖
player=玩家 index=索引 state=状态 detection=检测 failure=故障 reset=重置
speedometer=速度表 instrument=仪表 rpm=RPM led=LED drs=DRS abs=ABS tc=TC
onboard=车载 differential=差速器 deltabest=最佳圈差值 statistics=统计 stats=统计
ffb=FFB gain=增益 zero=零 input=输入 output=输出
unit=单位 meter=米 meters=米 second=秒 seconds=秒 percent=百分比 fraction=比例
format=格式 precision=精度 decimals=小数位 digits=位数 round=取整
clock=时钟 wind=风 direction=方向 weather=天气 rain=雨 wetness=湿度
average=平均 total=总计 number=数量 count=计数 target=目标 reference=参考
line=线条 outline=轮廓 marker=标记 indicator=指示器 bar=条 graph=图表 curve=曲线
style=样式 opacity=不透明度 transparency=透明度 visible=可见 toggle=切换
pace=节奏 notes=笔记 pacenotes=路书 playback=播报 volume=音量 sound=音频
file=文件 folder=文件夹 duration=时长 queue=队列 hotkey=快捷键 key=键
binding=绑定 shortcut=快捷键 modifier=修饰键 button=按钮 mouse=鼠标
heatmap=热图 mapping=地图生成 saver=节省 saved=已保存
hybrid=混合动力 emotor=电机 regen=回收 regeneration=能量回收 drain=消耗
split=分段 valid=有效 invalid=无效 prediction=预测 estimated=预计
personal=个人 theoretical=理论 optimal=最佳 fast=快速 slow=慢速
enabled=已启用 disabled=已禁用 unavailable=不可用
refresh=刷新 attempts=尝试次数 loading=加载 saving=保存
combined=合并 translucent=半透明 correction=修正 confirmation=确认 batch=批量
group=分组 search=搜索 resolution=分辨率 percentage=百分比 max=最大 min=最小
dynamic=动态 static=静态 inner=内侧 outer=外侧 middle=中间 surface=表面 carcass=胎体
boost=增压 push=超车 pass=超车 release=释放 lift=收油 coast=滑行
""".split())
