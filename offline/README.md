# 内网离线依赖包

将 `install.py`、`skill/` 和本目录 `offline/` 按原布局拷到内网。目标机器已有带 `venv` 和 `ensurepip` 的 CPython 即可；不需要预先下载包、安装 `uv` 或设置 `PIP_*`。在 `install.py` 所在目录运行：

```powershell
# Windows：目标项目目录必须已存在
py -3 install.py "C:\path\to\project"
```

```bash
# macOS / Linux
python3 install.py "/path/to/project"
```

`wheels/` 保存 48 个原始 PyPI wheel；`requirements.lock` 锁定版本与 SHA-256。安装器只安装与当前解释器兼容的文件，不复制整包到目标项目。缺文件、哈希不符或平台不匹配时，安装失败，不请求公网。模型不在依赖包中；自然语言需求分析和撰写 PRD 沿用客户端已经配好的内网推理服务。

## 支持范围

按**运行安装器的解释器**选择 wheel，限标准 CPython（默认 GIL 构建）：

| 系统 | 架构 | Python 小版本 |
| --- | --- | --- |
| Windows | x64、x86 | 3.10–3.15 |
| Windows | ARM64 原生 | 3.11–3.15（上游没有 3.10 的该架构 wheel） |
| macOS | Intel x86_64、Apple Silicon arm64 | 3.10–3.15 |
| Linux | x86_64、aarch64；glibc 2.17+ | 3.10–3.15 |

只有 `rpds-py` 需要区分本机平台与 Python ABI，其他依赖共用纯 Python wheel。以上列出的是随包文件覆盖范围，不代表每种组合都已实机测试。安装器不会尝试用源码编译缺少的 wheel。独立的 Python、操作系统运行库、客户端和模型由目标环境提供。

第三方版权与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。公开版不包含 `musllinux` wheel，因此不支持 Alpine 等 musl Linux 发行版的离线安装。

## 维护与验证

- 离线验收：从**源码仓库**运行 `python -I -B tests/prd-generator/run_installed_smoke.py --install`（POSIX 可用 `python3`，Windows 可用 `py -3`）。测试在临时目录从零创建 venv、保存分析、生成草稿、恢复中断并核验并发写入，不调用模型。可在操作系统层关闭外网后运行。
- 更新：维护者在联网机运行 `python3 -I tools/prepare_offline_wheels.py NEW_DIRECTORY`，在新目录生成 `wheels/` 和 `requirements.lock`。它核对 PyPI 文件哈希且不执行下载内容；用户安装不运行这个脚本。升级依赖时一并检查生产 `scripts/requirements.txt`、平台矩阵及第三方许可证。
- 生产 Schema 只用到 RFC 3339 的 `date-time` 格式，因此明确携带 `rfc3339-validator`，不打包另外十余个可选格式插件。若产品新增其他 `format`，需同步调整校验器、依赖和测试。
