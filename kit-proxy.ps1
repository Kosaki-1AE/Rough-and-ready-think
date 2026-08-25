$git = "C:\Program Files\Git\cmd\git.exe"

$ssid = (netsh wlan show interfaces |
    Select-String '^\s*SSID\s*:' |
    Select-Object -First 1).ToString().Split(':',2)[1].Trim()

if ($ssid -eq "KIT-WLAP2") {

    & $git config --global http.proxy  http://wwwproxy1.kanazawa-it.ac.jp:8080
    & $git config --global https.proxy http://wwwproxy1.kanazawa-it.ac.jp:8080

    Write-Host "KITinside : Proxy OFF"
}
else {

    & $git config --global --unset http.proxy  2>$null
    & $git config --global --unset https.proxy 2>$null

    Write-Host "KIToutside : Proxy ON"
}