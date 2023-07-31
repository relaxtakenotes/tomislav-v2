$remote_dir = "/home/steam/tomislav-v2"
$local_dir = "."


[String[]]$domains = @("debian@164.132.206.72", "steam@74.91.113.114")
[String[]]$remote_dirs = @("/home/steam/tomislav-v2", "/home/steam/tomislav-v2")

For ($i=0; $i -lt $domains.Length; $i++) {
	$arguments = "$($domains[$i])"
	ssh ${arguments} 'sudo systemctl restart tomislav'
}

