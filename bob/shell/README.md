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

`export BOBSHELL_API_KEY="your-api-key-here"` or `$env:BOBSHELL_API_KEY="your-api-key-here"` on windows

Then run `bob --auth-method api-key -p "Hi"`

### outbound request domain

from Github Codespace and oci singapore

- api.us-east.bob.ibm.com
- s3.us-south.cloud-object-storage.appdomain.cloud
