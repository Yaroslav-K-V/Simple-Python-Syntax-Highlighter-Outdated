$chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
$rng = [System.Random]::new()
$tag = "v" + (-join (1..5 | ForEach-Object { $chars[$rng.Next(0, $chars.Length)] }))

git tag $tag
git push --tags

Write-Host "Created and pushed tag: $tag"
