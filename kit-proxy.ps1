$ssid = (netsh wlan show interfaces |
    Select-String '^\s*SSID\s*:' |
    Select-Object -First 1).ToString().Split(':',2)[1].Trim()

if ($ssid -eq "KIT-WLAP2") {
    $env:http_proxy  = "http://wwwproxy1.kanazawa-it.ac.jp:8080"
    $env:https_proxy = "http://wwwproxy1.kanazawa-it.ac.jp:8080"

    git config --global http.proxy  http://wwwproxy1.kanazawa-it.ac.jp:8080
    git config --global https.proxy http://wwwproxy1.kanazawa-it.ac.jp:8080

    Write-Host "KITinside: Proxy ON"
}
else {
    Remove-Item Env:http_proxy  -ErrorAction SilentlyContinue
    Remove-Item Env:https_proxy -ErrorAction SilentlyContinue

    git config --global --unset http.proxy  2>$null
    git config --global --unset https.proxy 2>$null

    Write-Host "KIToutside: Proxy OFF"
}