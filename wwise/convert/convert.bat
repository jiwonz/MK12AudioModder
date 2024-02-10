.\WsourcesMaker.exe input
for %%s in (..\*.wproj) do %* convert-external-source "%%s" --source-file convert\list.wsources --output output
pause
