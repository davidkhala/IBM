### `panic: open resources/all.zh_Hant.json: file does not exist`
cause:IBM 官方的 cpd-cli 并没有提供 zh_Hant (繁体中文) 语言包

solution: manual config in advance

```
export LANG=zh_Hans.UTF-8
export LC_ALL=zh_Hans.UTF-8
```
