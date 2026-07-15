# IBM Bob
>
> SDLC partner
AI Code assistant

- released as Bob IDE, Bob-Shell

Bob uses a model orchestration layer

- It dynamically selects from multiple model families
- customers don't need to manage model selection or updates
- model families: Claude, Mistral, Granite
- > At this stage, we are unable to provide a quote for Bob in Hong Kong and China due to restrictions related to Claude, which is one of the models we use.

### outbound request domain

- iam.cloud.ibm.com
- us-east.apprapp.cloud.ibm.com
- raw.githubusercontent.com
- ibm.gallery.vsassets.io


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

```
bob --auth-method api-key -p "Hi"
```

### outbound request domain

from Github Codespace and oci singapore

- api.us-east.bob.ibm.com
- s3.us-south.cloud-object-storage.appdomain.cloud
