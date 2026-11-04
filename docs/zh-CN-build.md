# 简体中文 APK 自动构建与签名

本仓库的汉化分支使用独立签名。**不要把 JKS、密码或私钥提交到 Git。** 同一汉化渠道的后续 APK 必须一直使用同一把密钥，否则 Android 会拒绝覆盖升级。

## 一次性配置 GitHub Actions

在仓库 Settings → Secrets and variables → Actions → New repository secret 中添加：

- `CYT_KEYSTORE_BASE64`：持久 JKS/PKCS12 签名文件的 Base64 内容
- `CYT_KEY_ALIAS`：密钥别名
- `CYT_KEY_PASSWORD`：私钥密码
- `CYT_KEYSTORE_PASSWORD`：密钥库密码

建议在可信任的本地电脑生成专用密钥并离线备份。示例（请自行替换密码和别名）：

```bash
keytool -genkeypair -v -keystore cyt-release.jks -alias cyt-release -keyalg RSA -keysize 4096 -validity 10000
base64 -w 0 cyt-release.jks
```

将 Base64 输出填入 `CYT_KEYSTORE_BASE64`，其余三项分别填入对应 Secret。不要把密钥文件或 Base64 输出发到聊天、Issue、PR 或提交记录中。

## 构建

推送到 `feature/zh-cn-localization` 会触发工作流；也可以在 Actions → Chinese APK (signed) → Run workflow 手动运行。成功后在该次运行的 Artifacts 下载 `CleanYourTV-zh-CN.apk`。

创建 `zh-v*` 标签并推送时，工作流还会把 APK 发布到 GitHub Release。请只在已配置密钥后使用标签发布。

## 安装与升级

此 APK 使用独立签名，首次安装前需要卸载签名不同的原版。卸载会清除原版应用数据。之后的汉化版升级必须使用同一 JKS；请离线备份密钥和密码。丢失密钥后，旧安装无法通过普通覆盖安装升级。

## 当前范围

该工作流只负责构建、签名、校验和分发，不代表界面翻译已经完成。汉化资源和动态文案必须经过代码审查与测试后再发布。
