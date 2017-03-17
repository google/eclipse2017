**To run locally:**

After building the docker image and completing the following, you will be able
to access the app at http://localhost:8080, however note that the only endpoints
are the POST only upload endpoint and the health check.

```bash
$ cd upload/server
$ docker run -p 8080:8080 <image>
```
