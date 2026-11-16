# Live for Speed 接入

本分支通过本机 UDP 读取 LFS 的 OutSim 和 OutGauge，不安装额外插件，不写入游戏内存，不自动修改游戏配置。

读取方式参考 [LFS-Race-Engineer 的协议实现](https://github.com/fermga/LFS-Race-Engineer/tree/main/src/lfs_telemetry/telemetry/protocol)。协议来源及使用条件可查阅 [LFS 开发者文档](https://www.lfs.net/programmer/insim)、[OutSim](https://en.lfsmanual.net/wiki/OutSim) 和 [OutGauge](https://en.lfsmanual.net/wiki/OutGauge)，并以当前游戏安装目录中的 `docs/OutSimPack.txt` 为准。

## 配置与启动

先退出 LFS，并自行备份游戏根目录的 `cfg.txt`。在该文件中设置以下条目；若条目已经存在，请修改原条目，避免重复添加：

```text
OutSim Mode 1
OutSim Opts 1ff
OutSim Delay 1
OutSim IP 127.0.0.1
OutSim Port 30000
OutSim ID 0
OutGauge Mode 1
OutGauge Delay 1
OutGauge IP 127.0.0.1
OutGauge Port 30001
OutGauge ID 0
```

在 TinyPedal 的“API”菜单中选择 `Live for Speed`，再打开“选项”：

| 配置键 | 含义 |
| --- | --- |
| `outsim_port` / `outgauge_port` | 两个不同的本机 UDP 端口，须与游戏一致 |
| `track_name` | 必填的赛道及布局名称，例如 `FE2`；更换赛道后须更新 |
| `driver_name` | 人工填写的驾驶者名称或昵称 |
| `track_length` | 赛道长度，单位米；未知时保留 0 |
| `steering_range` | 游戏内方向盘总转角，单位度；未知时保留 0 |
| `engine_rpm_max` | 游戏车辆的最高转速，单位 RPM；未知时保留 0 |
| `fuel_capacity` | 油箱容量，单位升；未知时保留 0，只使用油量比例 |
| `connection_timeout` | 数据过期秒数，默认 1 秒 |

人工补充的数值须与游戏及车辆实际设置一致，程序不会自动猜测。为防止不同赛道的数据混到同一名称下，未填写 `track_name` 时不会启用实时叠加层。接口状态会提示填写赛道名。

应用选项后启动 LFS，进入车辆并使用驾驶舱或自定义车内视角。状态栏显示 `OutSim 1ff` 表示已收到扩展物理数据。游戏退出、暂停或切换到不输出遥测的视角后，过期数据会使叠加层隐藏。恢复驾驶后继续接收，无需重新绑定端口。

默认 `Mode 1` 只采集驾驶；若改成 `Mode 2`，回放也可能被采集。两路 UDP 本身不足以可靠辨认驾驶与回放，分析时请注明数据来源。

## 数据范围

| 数据 | 来源与边界 |
| --- | --- |
| 速度、位置、姿态、加速度、角速度 | 旧版及扩展 OutSim |
| 油门、刹车、离合 | 扩展 OutSim；旧版格式可由同时有效的 OutGauge 补充 |
| 转向输入、手刹、圈内距离 | 扩展 OutSim |
| 四轮载荷、悬架压缩、轮速、滑移率、滑移角、轮胎空气温度 | 扩展 OutSim，内部统一为 FL、FR、RL、RR |
| 挡位、转速 | 扩展 OutSim；OutGauge 也可提供 |
| 车型或 MOD ID、油量比例、增压、水温、油温、仪表灯 | OutGauge |

此版本只提供本车遥测，没有实现 InSim。因此，官方圈数、圈时、有效圈判定、分段、赛道自动识别、多人排名、天气、维修区状态和调教文件自动备份不受支持。轮胎压力、胎面温度、轮胎磨损、刹车温度、实际发动机扭矩和标准化力反馈也不在这两路协议的可用数据中。OutSim 的最大可用扭矩、转向扭矩和胎内空气温度不能当作上述同名近似指标使用。

建议先启用速度表、踏板、转向和悬架行程等有实际来源的组件。依赖赛事、损伤或未提供温度数据的组件应关闭；为兼容既有读取接口，这些组件的部分通道沿用零值或不可用哨兵值，不代表真实测量。

## 实现与修改位置

- `lfs_udp.py` 负责定长小端解码、数值检查、两个 socket 和接收线程。旧格式仅接受 64/68 字节，扩展格式仅接受 `1ff` 对应的 280 字节；OutGauge 接受 92/96 字节。其他掩码会拒绝并记录日志。
- UDP 独立校验递增时间戳，丢弃重复或乱序包。过期后允许接收重新开始的时钟，并更新重置计数。两路时间差超过 250ms 时不合并仪表数据。此同步方式使用最近有效包，不做插值。
- `lfs_reader.py` 把不可变快照映射到现有 `APIDataReader`。协议轮序 RL、RR、FL、FR 在解码时只转换一次。输入不加平滑或死区，位置从 1/65536 米换成米，发动机角速度换成 RPM。
- 加速度轴沿用参考实现的车身坐标解释；读取接口的纵向符号与现有模块保持一致，制动为正。导出会保留协议原始轴，真实车辆上的轴向和符号仍需手动核对。
- `lfs_connector.py` 创建并管理接收器，复用原有开始、停止和重载入口。绑定失败会显示在接口状态及日志中。没有自动改端口或关闭占用端口的软件。

若其他工具已占用同一 UDP 端口，请先停止该工具，或为 TinyPedal 和 LFS 配置另一对端口。此版本没有增加 UDP 转发功能。

## 最小手动验证

前置条件：已按中文 README 准备依赖和子模块，并安装支持扩展 OutSim 的 LFS。

在仓库根目录执行 `.\.venv\Scripts\python.exe run.py`，按上面的步骤设置游戏与接口。预期速度与游戏仪表一致，踏板从 0 到 1 变化，左右转向方向正确；驶过路肩时对应车轮的悬架行程变化。请另行核对加速度符号和四轮顺序。

随后暂停或退出 LFS，预期约 1 秒后停止使用旧数据；恢复驾驶、重启 API、切换到原有游戏再切回 LFS，预期能重新绑定端口。端口被占用时，预期在状态和日志中看到失败原因。

本次只做静态复核，尚未用真实 LFS 或 UDP 数据包运行验证。未执行测试，由用户自行验证。
