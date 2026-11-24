## Bob-Shell

### Install

```
curl -fsSL https://bob.ibm.com/download/bobshell.sh | bash
```

linux: root install
```
sudo npm install --registry=https://registry.npmjs.org/ --allow-scripts=@officecli/officecli -g @ibm/bob
```

windows install

```powershell
powershell -ep Bypass 'irm -Uri "https://bob.ibm.com/download/bobshell.ps1" | iex'
```

### Use API key

```
echo 'export BOB_API_KEY="your-api-key-here"' >> ~/.bashrc
```
or on windows 
```
[System.Environment]::SetEnvironmentVariable('BOB_API_KEY', 'your-api-key-here', 'User')
```

Then start TUI by `bob --accept-license`

### Connect to Bob Self-hosted

```
export BOB_GATEWAY_URL= # 
export BOB_WEB_LOGIN_URL= # 

bob --gateway-url $BOB_GATEWAY_URL --web-login-url $BOB_WEB_LOGIN_URL
```




### Ralph loop

see [ralph](./ralph/)

### outbound request domain

from Github Codespace and oci singapore

- api.us-east.bob.ibm.com
- s3.us-south.cloud-object-storage.appdomain.cloud
