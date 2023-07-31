$local_dir = "."

[String[]]$domains = @("user@ip")
[String[]]$remote_dirs = @("/home/steam/tomislav-v2")


For ($i=0; $i -lt $domains.Length; $i++) {
	$arguments = "$($domains[$i]):$($remote_dirs[$i])"
	rsync -avhp --rsync-path="sudo rsync" --chmod=a+rwx --chown=steam:steam ${local_dir} ${arguments}
	$arguments = "$($domains[$i])"
	ssh ${arguments} 'sudo systemctl restart tomislav'
}

