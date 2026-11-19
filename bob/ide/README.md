# IBM IDE
- 可以生成 .docx
- 如果没有打开任何workspace，bob默认会在`~\.bob\playground`目录下执行命令
- 解锁workspace限制
  - Bob Settings -> Chat -> `Allow outside workspace tool requests`

## outbound request domain

- iam.cloud.ibm.com
- us-east.apprapp.cloud.ibm.com
- raw.githubusercontent.com
- ibm.gallery.vsassets.io

## Connect to Bob Self-host

需要配置`~/.bob/settings/settings.json`

```
{
  ...
  "gatewayUrl": "https://api.bob.ibm-bob.bob-d4375da7964138e25578b22062c779db-0000.jp-tok.containers.appdomain.cloud"
}

```