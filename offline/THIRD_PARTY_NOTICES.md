# 离线 wheel 第三方许可证与版权通知

本页适用于随本仓库原样交付的 `offline/wheels/`：7 个纯 Python wheel 和 41 个 `rpds-py` 平台 wheel。`licenses/` 中的通知可离线阅读；上游链接仅用于复核。本页不变更上游许可，也不替代 wheel 内原有通知。

## Python 发行包

下表的成员路径均相对于对应 wheel 的 `<发行名>-<版本>.dist-info/`。

| 发行包 | 许可证 | wheel 内成员 | 离线原文 |
| --- | --- | --- | --- |
| `attrs` 26.1.0 | MIT | `licenses/LICENSE` | [LICENSE](licenses/python/attrs-26.1.0-LICENSE.txt) |
| `jsonschema` 4.26.0 | MIT | `licenses/COPYING` | [COPYING](licenses/python/jsonschema-4.26.0-COPYING.txt) |
| `jsonschema-specifications` 2025.9.1、`referencing` 0.37.0 | MIT | `licenses/COPYING` | [COPYING（两份字节相同）](licenses/python/jsonschema-specifications-and-referencing-COPYING.txt) |
| `rfc3339-validator` 0.1.4 | MIT | `LICENSE`、`AUTHORS.rst` | [LICENSE](licenses/python/rfc3339-validator-0.1.4-LICENSE.txt)、[AUTHORS](licenses/python/rfc3339-validator-0.1.4-AUTHORS.rst) |
| `six` 1.17.0 | MIT | `LICENSE` | [LICENSE](licenses/python/six-1.17.0-LICENSE.txt) |
| `typing-extensions` 4.16.0 | PSF-2.0 | `licenses/LICENSE` | [LICENSE](licenses/python/typing-extensions-4.16.0-LICENSE.txt) |
| `rpds-py` 0.30.0、2026.9.1 | MIT | `licenses/LICENSE` | [LICENSE](licenses/python/rpds-py-LICENSE.txt) |

`rfc3339-validator` 未声明 `License-File`，但 wheel 确有 `LICENSE`，以其中的原文为准。两个 `rpds-py` 版本的 wheel 许可证仅在 Windows 与其他平台之间存在 CRLF/LF 差异，离线副本保留 LF 版本。`rpds-py` 自身的 MIT 通知不覆盖下列原生依赖。

## `rpds-py` 原生 Rust 依赖

- **0.30.0（6 个 wheel）**：wheel 没有 SBOM 或 `THIRD_PARTY_LICENSES`。以 [v0.30.0 源码对应的 `Cargo.lock`](https://github.com/crate-py/rpds/blob/c38c9795cc6a1b4d95bd1863e7164f889a638adf/Cargo.lock)（与 [PyPI 源码包](https://files.pythonhosted.org/packages/20/af/3f2f423103f1113b36230496629986e0ef7e199d2aa8392452b484b38ced/rpds_py-0.30.0.tar.gz)内文件相同）及锁定 `.crate` 的依赖声明判断生产依赖。发布构建未传 `--locked`，因此这是源码侧证据，不是已发布二进制的逐项清单。
- **2026.9.1（35 个 wheel）**：以每份 wheel 的 `rpds_py-2026.9.1.dist-info/sboms/rpds-py.cyclonedx.json` 为准，均无 `THIRD_PARTY_LICENSES`。35 份 SBOM 的 crate 名、版本、SPDX、`scope` 和依赖关系一致。表中纳入全部 `required` 项，包括参与生成代码的过程宏；按同版本的[官方 `Cargo.lock`](https://github.com/crate-py/rpds/blob/v2026.9.1/Cargo.lock) 核对 `.crate` 的 SHA-256 后取原文。

`MIT OR Apache-2.0` 的条目随附上游 MIT 选项；对于 PyO3 另保留带独立版权行的 Apache 原文。`unicode-ident` 的 `Unicode-3.0` 是并列要求，单独收录。相同的上游通知只留一份。

| Crate | 0.30.0 | 2026.9.1 | SPDX | 离线原文（`.crate` 内文件名） |
| --- | --- | --- | --- | --- |
| `archery` | 1.2.2 | 1.2.3 | MIT | [LICENSE.md](licenses/rust-crates/orium-LICENSE-MIT.txt) |
| `rpds` | 1.2.0 | 1.2.1 | MIT | [LICENSE.md](licenses/rust-crates/orium-LICENSE-MIT.txt) |
| `triomphe` | 0.1.15 | 0.1.16 | MIT OR Apache-2.0 | [LICENSE-MIT](licenses/rust-crates/triomphe-LICENSE-MIT.txt) |
| `pyo3`、`pyo3-ffi` | 0.27.2 | 0.29.3 | MIT OR Apache-2.0 | [LICENSE-MIT](licenses/rust-crates/PyO3-LICENSE-MIT.txt)、[LICENSE-APACHE](licenses/rust-crates/PyO3-LICENSE-APACHE.txt) |
| `pyo3-macros`、`pyo3-macros-backend` | 0.27.2（过程宏） | 0.29.3 | MIT OR Apache-2.0 | [LICENSE-MIT](licenses/rust-crates/PyO3-LICENSE-MIT.txt)、[LICENSE-APACHE](licenses/rust-crates/PyO3-LICENSE-APACHE.txt) |
| `libc`（Rust FFI crate） | 0.2.177 | 0.2.177 | MIT OR Apache-2.0 | [LICENSE-MIT](licenses/rust-crates/libc-LICENSE-MIT.txt) |
| `memoffset` | 0.9.1 | — | MIT | [LICENSE](licenses/rust-crates/memoffset-LICENSE-MIT.txt) |
| `once_cell` | 1.21.3 | 1.21.3 | MIT OR Apache-2.0 | [LICENSE-MIT](licenses/rust-crates/common-LICENSE-MIT.txt) |
| `unindent` | 0.2.4 | — | MIT OR Apache-2.0 | [LICENSE-MIT](licenses/rust-crates/common-LICENSE-MIT.txt) |
| `indoc` | 2.0.7（过程宏） | — | MIT OR Apache-2.0 | [LICENSE-MIT](licenses/rust-crates/common-LICENSE-MIT.txt) |
| `heck` | 0.5.0（过程宏依赖） | 0.5.0 | MIT OR Apache-2.0 | [LICENSE-MIT](licenses/rust-crates/heck-LICENSE-MIT.txt) |
| `proc-macro2`、`quote`、`syn` | 1.0.103、1.0.42、2.0.111（过程宏依赖） | 1.0.103、1.0.42、2.0.111 | MIT OR Apache-2.0 | [LICENSE-MIT](licenses/rust-crates/common-LICENSE-MIT.txt) |
| `unicode-ident` | 1.0.22（过程宏依赖） | 1.0.22 | (MIT OR Apache-2.0) AND Unicode-3.0 | [LICENSE-MIT](licenses/rust-crates/common-LICENSE-MIT.txt)、[LICENSE-UNICODE](licenses/rust-crates/unicode-ident-LICENSE-UNICODE.txt) |
| `smallvec` | — | 1.15.1 | MIT OR Apache-2.0 | [LICENSE-MIT](licenses/rust-crates/smallvec-LICENSE-MIT.txt) |

未纳入的 Cargo 组件：`pyo3-build-config` 和 `target-lexicon` 在新版 SBOM 标为 `excluded`，旧版也只在宿主构建路径使用；旧版 `autocfg`、`rustversion` 和 Windows 构建辅助链 `python3-dll-a`、`cc`、`find-msvc-tools`、`shlex` 不属于目标运行库。两版锁文件的 `portable-atomic` 只适用于缺少原生 64 位原子操作的目标，不在现有 wheel 的目标集合内，新版 SBOM 也不列出它。

## 工具链运行库与未覆盖的范围

**Rust 标准库。** 扩展中的标准库源码路径指向 Rust [1.91.0](https://github.com/rust-lang/rust/tree/f8297e351a40c1439a467bbbb6879088047f50b3)、[1.91.1](https://github.com/rust-lang/rust/tree/ed61e7d7e242494fb7057f2657300d9e77bb4fcb)（`rpds-py` 0.30.0）和 [1.98.1](https://github.com/rust-lang/rust/tree/48a229ceaefd4985c50990b14116b6d856af0985)、[1.99.0](https://github.com/rust-lang/rust/tree/b940084d7eb6a299eb4bfeb8e34901bc051e7ac4)（`rpds-py` 2026.9.1）。随附四版共有的 [COPYRIGHT](licenses/rust-std/COPYRIGHT)、[LICENSE-MIT](licenses/rust-std/LICENSE-MIT) 和 [LICENSE-APACHE](licenses/rust-std/LICENSE-APACHE)。它们不是各目标最终链接的标准库或编译器运行库子组件清单；未逐项核验其第三方代码或平台运行库。上游 `COPYRIGHT` 也区分了通用通知和详细的 `COPYRIGHT-library.html`。

**不分发 `musllinux` wheel。** 这两个 `rpds-py` 版本的 `musllinux` wheel 附带独立 `libgcc_s`，对应源码尚未核实，故不纳入公开包。系统提供、未封装在 wheel 的动态库不在本页交付范围内。

## 维护者复核

1. 用 `offline/requirements.lock` 对照 wheel 的 SHA-256。使用 `python3 -I` 的 `zipfile` 只读检查每份 wheel 的 `METADATA` 和上表成员；除已说明的换行差异外，Python 通知可逐字节比较。不要安装或导入 wheel 来复核。
2. 更新 `rpds-py` 时，逐平台比较 wheel 自带的 SBOM 或第三方通知；没有这些材料时，按发布源码的 `Cargo.lock`、`Cargo.toml` 中的特性及目标条件复做依赖筛选。crates.io 原始归档地址为 `https://static.crates.io/crates/{crate}/{crate}-{version}.crate`；先用锁文件的 `checksum` 校验，再从 tar 成员中读取许可证原文。没有版权行的上游原文不补造版权归属。
3. 同时枚举 wheel 内的 `.so`、`.pyd`、`.dll`、`.dylib` 及 `.libs/` 文件；Cargo SBOM 不能替代原生轮包检查。记录独立运行库的文件名、哈希和构建来源，重新核验其通知及再分发条件。
