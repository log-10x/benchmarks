---
icon: material/docker
---

Pulls Docker images from container registries for [compile](https://doc.log10x.com/compile/) pipeline [scanning](https://doc.log10x.com/compile/scan/) of source code, binaries, and configuration.

Only downloads images when their SHA256 hash differs from previously scanned [symbol files](https://doc.log10x.com/compile/scanner/symbol/).

!!! tenx-docker "Docker CLI"

    Requires [docker CLI](https://github.com/docker/cli) for authentication and export. Install locally or use the compiler [Docker image](https://doc.log10x.com/install/docker/).

Executed CLI commands:

``` bash

# check the docker cli client is available
docker version 

# check whether target image exists and its hash has not already been scanned
docker inspect manifest <image>

# create the container locally 
docker create <image>

# export the container to a .tar file
docker export <containerID> <temp-file-to-scan.tar>

# stop the container and remove the image from disk
docker stop <containerID>
docker rmi <containerID>
```

 