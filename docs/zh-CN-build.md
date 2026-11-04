# 简体中文 APK 自动构建与签名

本仓库使用独立签名。公开发布的是**签名证书**，私钥 JKS 和密码只放在 GitHub Actions Secrets 中。后续汉化版必须复用同一把私钥，否则 Android 不允许覆盖升级。

## 公开证书

证书文件：[`signing/zh-cn-release-cert.pem`](../signing/zh-cn-release-cert.pem)

SHA-256 指纹：

```
A7:5A:27:8D:80:B7:61:1F:BC:F3:3F:10:C8:CC:0A:46:28:75:16:F7:C4:92:D0:FF:A0:40:C7:2C:7D:F0:3A:67
```

证书只包含公钥，不可用于签署 APK。CI 在签名后应核对 APK 的签名证书指纹与上述值一致。

## 一次性配置 GitHub Actions

在仓库 Settings → Secrets and variables → Actions → New repository secret 中添加：

- `CYT_KEYSTORE_BASE64`：私有 JKS 文件的 Base64 内容
- `CYT_KEY_ALIAS`：`cyt-release`
- `CYT_KEY_PASSWORD`：私钥密码
- `CYT_KEYSTORE_PASSWORD`：密钥库密码

在可信任的本地电脑生成并备份专用密钥（仅作新密钥生成示例；本项目已经生成对应密钥，务必使用原来的 JKS，不能重新生成）：

```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes(".\\cleanyourtv-zhcn-release.jks")) | Set-Clipboard
```

将 Base64 内容填入 `CYT_KEYSTORE_BASE64`，其余三项填入对应 Secret。**不要把 JKS、Base64 或密码提交到 Git、Issue、PR 或聊天中。** 至少保留两份离线备份。

## 构建

推送到 `feature/zh-cn-localization` 会触发工作流；也可以在 Actions → Chinese APK (signed) → Run workflow 手动运行。成功后在该次运行的 Artifacts 下载 `CleanYourTV-zh-CN.apk`。

推送 `zh-v*` 标签会将 APK 发布到 GitHub Release。只在汉化资源完成审查、测试通过并配置密钥后发布。

## 安装与升级

首次安装前需卸载签名不同的原版，卸载会清除原版应用数据。之后每个汉化版都必须使用同一 JKS；丢失私钥后无法对已安装版本进行普通覆盖升级。

## 当前状态

自动构建与签名工作流是构建基础设施，不代表界面汉化已完成。界面资源、Compose 硬编码文案、电视端界面及系统应用说明仍需完成翻译、校验和回归测试后才能发布正式 APK。
