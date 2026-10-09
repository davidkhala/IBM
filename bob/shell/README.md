## Bob-Shell

### Install

```
curl -fsSL https://bob.ibm.com/download/bobshell.sh | bash
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



### outbound request domain

from Github Codespace and oci singapore

- api.us-east.bob.ibm.com
- s3.us-south.cloud-object-storage.appdomain.cloud
