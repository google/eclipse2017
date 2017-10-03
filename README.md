**Installing development prerequisites**
```bash

# Install gerrit's hooks to ensure that pushes go to code review.
curl -Lo $(git rev-parse --git-dir)/hooks/commit-msg https://gerrit-review.googlesource.com/tools/hooks/commit-msg
chmod +x $(git rev-parse --git-dir)/hooks/commit-msg
git config remote.origin.push refs/heads/*:refs/for/*

sudo apt-get install docker-engine
# Install nvm
curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.32.1/install.sh | bash
source $HOME/.bashrc
# install node.js v6
nvm install 6
npm install

# Create a local_dev secret for HTTPS
./scripts/run create_secret local-dev
# Create a dev secret for HTTPS
./scripts/run create_secret dev

```

Follow
https://docs.docker.com/engine/installation/linux/ubuntulinux/#/create-a-docker-group to add yourself to the docker group.
(note, you must completely log out of your current session for group changes to
apply.  This includes exiting your entire window session.)

**If building/deploying for/to a new Google Cloud project**

Every developer should create a Google Cloud project with an id of the form
"eclipse-2017-dev-$USER".  Starting at https://console.cloud.google.com, in the
top blue bar, click your current project and select "Create Project".

Set the GCLOUD_PROJ variable to this id:

``` bash
export GCLOUD_PROJ=eclipse-2017-dev-$USER
```

Create credentials: Google Cloud Console > API Manager > Credentials.  Select
"Oauth consent screen" tab and set the product name to $GCLOUD_PROJ.  Click
"Create Credentials" and select "API Key".  Make Next, click "Create
Credentials" again, and select "OAuth Client ID".  Select "Web application";
fill the Name field with "Eclipse 2017 Dev $USER".  Add the following redirect
URIs: https://localhost/oauth2callback

Next, create a service account the gcloud project you wish to deploy to - To do
this: Google Cloud Console > IAM & Admin > Service Accounts > Create Service
Account. Assign the role Project > Editor (TODO: is this the correct role?) to
the service account. Select to furnish a new private key in JSON format and
create the service account. This will download a JSON key file to your downloads
folder. Rename this file to service_account_\<env\>.json (choosing the env with
which you want to associate this particular gcloud project) and move it to the
eclipse2017/conf directory.

Create a google cloud storage bucket to store photos. Google Could Console >
Storage > Create Bucket. Name your bucket GCLOUD_PROJ-photos. Assign your bucket
the standard storage class and location United States.

Set your gcloud project:

```bash
$ gcloud auth login
# Do the auth two-step
$ gcloud config set project $GCLOUD_PROJ
$ gcloud config set compute/zone us-central1-a
$ gcloud beta auth application-default login
$ gcloud container clusters get-credentials eclipse
```


You need to create a GKE cluster, however due to a strange Google Cloud
bug, you will need to visit https://console.cloud.google.com/kubernetes/list before
you can do this. You will see a loading wheel telling you that GKE is
initializing. Once this loading is complete, you are ready to create your
cluster as described below.

Create a container engine cluster. *Important: cluster must be named `eclipse`*

```bash
$ # Give the cluster full gcloud api access. TODO maybe change this in the future?
$ # Currently this is what enables the upload daemon to connect to datastore
$ gcloud container clusters create eclipse --num-nodes 1 --machine-type \
  n1-standard-4 --scopes "https://www.googleapis.com/auth/cloud-platform"
```

You need to create a file called <proj_root>/conf/secret_keys_\<env\>.py for each
env to which you wish to deploy. These files need to contain 4 module level
constants specific to the gcloud project you are associating with env (defined
in scripts/run):

    - FLASK_SESSION_ENC_KEY='<str>': a 24 byte random string used for flask session
      encryption. You can output this value from the command line as follows:
      `$ python -c "import os; print repr(os.urandom(24))"`
    - GOOGLE_OAUTH2_CLIENT_ID='<str>': obtained from your gcloud project in Console > API Manager > Credentials -> Oauth 2.0 Client IDs
    - GOOGLE_OAUTH2_CLIENT_SECRET='<str>': obtained from your gcloud project in Console > API Manager > Credentials -> Oauth 2.0 Client IDs
    - GOOGLE_HTTP_API_KEY='<str>': obtained from you gcloud project in Console > API Manager > Credentials -> API Key. This api key should
      be restricted to HTTP traffic from a specific list referrers only.
    - GOOGLE_MAPS_API_KEY='<str>': obtained from you gcloud project in Console > API Manager > Credentials -> API Key. This api key should not be restricted.

**Enable Cloud APIs**
In Console > API Manager > Library search for and enable:

    - Google Cloud Vision API
    - Google Maps JavaScript API
    - Google Places API Web Service

**To build the application**
```bash
$ # Note: prod env is currently unavailable
$ ./scripts/run build [local-dev|dev|test|prod]
```

*Note: the local-dev environment should only be used when you are planning to
run the profile or upload-server containers on your local machine. This option
currently builds the project using the same configuration as the dev option,
EXCEPT it adds an additional nginx server to emulate the cloud load balancer's
TLS termination behavior, i.e. it turns HTTPS requests into HTTP requests and
forwards them to the profile/upload-server nginx servers*

You also need to install the service_account.json (from creating a service
account in the Cloud Console) file to connect to Cloud Storage and Cloud
Datastore. This contains secret keys and therefore will not be checked into
source control. The file should be named conf/service_account_<env>.json, where
<env> is the environment type (local-dev/dev, test, prod) of the Cloud project
you are deploying to.


**To run the application locally**
```bash
# Clean up old running containers
$ ./scripts/run teardown local-dev
# Optional: this invalidates the docker cache, which increases build times.
# Clean up old images
$ ./scripts/run clean local-dev
# build the local-dev environment
$ ./scripts/run build local-dev
# make a dir for the upload server and daemon to share files
$ mkdir pending-uploads
# loose perms so that 'www-data' can access it
$ chmod ugo+rwx pending-uploads
# Run the various application containers
$ ./scripts/run deploy local-dev
# Take down the local-dev environment again
$ ./scripts/run teardown local-dev
```

The "nginx-lb-emulator" is a fake Cloud Load Balancer; it is available on your
workstation at http://localhost:80 and https://localhost:443.  If there are any
other processes binding to those ports, the container will fail.

**To deploy**

```bash
$ ./scripts/run push [dev|test|prod]
$ ./scripts/run deploy [dev|test|prod]
```

You're done!! Be patient, it takes some time for the ingress to connect to the
profile and upload services. You can monitor the status of your deployment as
follows - when you see both backends change from status "UNKNOWN" to "HEALTHY"
the app should be visible online:

```bash
$ watch -n 10 "kubectl describe ingress"
```

Get the external IP address by running:

```bash
$ kubectl get ingress
```


**To teardown down your deployment**

```bash
$ # Note: stage/prod envs are currently unavailable
$ ./scripts/run teardown [dev|test|prod]
```

**Misc Kubernetes Notes**

* Always run a local kube proxy.  Once you have the proxy running, you can
access the [Kubernetes console](http://localhost:8001/api/v1/proxy/namespaces/kube-system/services/kubernetes-dashboard/#/admin?namespace=default) as well as use the kubectl command line
application.


```bash
$ kubectl proxy &
```

* After you've pushed and deployed once.  If you want to update the containers
in your deployment.  You can simply run the following, wait a few seconds and
GKE should respawn your containers with the new images.

```bash
$ ./scripts/run clean [dev|test|prod]
$ ./scripts/run build [dev|test|prod]
$ ./scripts/run push [dev|test|prod]
```

* Teardown does not remove already pushed container images from GKE.  If you
redeploy it will continue to reuse your old containers.  The proper way to
fully redeploy.

```bash
$ ./scripts/run teardown [dev|test|prod]
$ ./scripts/run clean [dev|test|prod]
$ ./scripts/run build [dev|test|prod]
$ ./scripts/run push [dev|test|prod]
$ ./scripts/run deploy [dev|test|prod]
```


**Running tests:**

To run all tests, from the project root directory *(Note: before running this
command you will have to build for dev so that the necessary environment
specific files are generated/moved to the correct locations)*:

```bash
$ ./scripts/run unittest dev

```
