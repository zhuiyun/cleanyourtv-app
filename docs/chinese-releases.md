# 简体中文 APK 自动发布

`.github/workflows/chinese-apk.yml` 在 `main` 和 `feature/zh-cn-localization` 推送后构建，也可以在这两个分支手动运行。构建使用已有的 `CYT_*` 仓库签名 secrets，不生成或公开新的私钥。签名必须匹配 `signing/zh-cn-release-cert.pem`。

每次成功的中文签名构建会自动上传 GitHub Releases：

- 标签：`zh-v<versionName>-build.<run_number>.<run_attempt>`，指向实际构建的提交。
- APK：`CleanYourTV-zh-CN-<versionName>.apk`。
- 校验文件：`SHA256SUMS.txt`，在下载目录运行 `sha256sum -c SHA256SUMS.txt` 即可校验。
- `main` 的正式版本发布为正式 Release；本次构建仍对应当前主线时才设为 Latest。功能分支和 alpha/beta/rc 版本为预发布。
- 发布前先创建草稿，上传后重新下载并逐字节验证，再公开发布。验证失败时保留草稿供排查，不公开坏包。
- 同一次运行的已有附件只有内容一致才能复用。不会覆盖附件、强制移动标签或删除历史版本。
- 重新运行构建会使用新的 `run_attempt`，得到独立 Release。同版本重建不会自动增加 Android `versionCode`，修改版本仍在 `app/build.gradle.kts` 中进行。

构建作业只有仓库读取权限，只有发布作业拥有 Releases 所需的 `contents: write`。发布作业不检出或执行仓库源码，只读取同一次运行的已签名 APK 和校验文件。签名密钥和临时未签名 APK 会在签名步骤退出时清理，Release 只包含已签名 APK 与校验文件。

本流程不处理上游的 Play/F-Droid 发布，不修改电视端遮罩，也不代替真实电视联调。GitHub 并发队列可能合并尚未开始的快速连续推送；本流程保证的是每个实际成功完成的中文构建都进入发布步骤。

发布逻辑测试：

```sh
python3 -m unittest discover -s scripts/tests -p 'test_chinese_release.py' -v
```

测试用本地模拟的 GitHub CLI 覆盖正常发布、预发布、旧提交、重复运行、草稿恢复、下载损坏、冲突附件、冲突标签和访问错误，不访问网络。

手动构建：在 GitHub 的 Actions 中选择 `Chinese APK (signed)`，点击 `Run workflow` 并选择 `main` 或中文功能分支。不要用上游 `release` 流程替代此中文签名流程。
