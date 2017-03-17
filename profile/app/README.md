**To run locally:**
After building the docker image and completing the following, you will be able to access the app at
http://localhost:8080

```bash
$ cd profile
$ docker run -p 8080:8080 <image>
```


**Note:**

The file `profile/tests/flask/test_flask_util.py` was copied from the
google/oauth2client GitHub repo (https://github.com/google/oauth2client). This
was included so we could subclass `FlaskOAuth2Tests` because the
oauth2client/tests module is not included in the oauth2client pypi distribution.


**Coming Soon**

To run system tests, you will need a copy of the latest selenium chromedriver
executable in your newly created profile/lib folder. You can download the driver
corresponding to your platform here:
http://chromedriver.storage.googleapis.com/index.html
