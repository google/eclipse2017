// Copyright 2017 Google Inc.
// Licensed under the Apache License, Version 2.0 (the "License");

// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at

//     http://www.apache.org/licenses/LICENSE-2.0

// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

var upload = {
    POST_URL: '/services/upload/',
    count: 0,
  begin: function(files, uploadContainer, idToken) {
        for (var i = 0; i < files.length; i++) {
            var file        = files[i];
            var xhr         = new XMLHttpRequest();
            // Set up unique mapping between xhr events and progress bars
            xhr.upload.fileNum = upload.count;
            var progressBar = document.createElement("upload-progress");
            progressBar.setAttribute('id', upload.getPBId(upload.count));
            // Listener to update progress bar
            xhr.upload.addEventListener("progress", function(e) {
                        upload.updateProgress(e.loaded, e.total, this.fileNum);
                }, false);
            // Listener to update upload success/failure
            xhr.onreadystatechange = function() {
                // if request state is done
                if (this.readyState == 4) {
                    var success = this.status == 200;
                                upload.showFinalResult(success, this.upload.fileNum);
                        }
                };
            // Show progress bar
            progressBar.setAttribute('title', file.name);
            uploadContainer.append(progressBar);
            // Begin upload
            xhr.open("POST", upload.POST_URL, true);
            xhr.setRequestHeader("X-FILENAME", file.name);
            xhr.setRequestHeader("X-IDTOKEN", idToken);
            xhr.send(file);
            // Update global upload count
            upload.count++;
        }
    },
    getPBId: function(i) {
        return 'pb' + i;
    },
    showFinalResult: function(success, progressBarNum) {
      console.log("show final results");
        // var progressBar = document.querySelector('#' + upload.getPBId(progressBarNum));
        // progressBar.setAttribute('success', success ? 'true' : 'false');
    },
    updateProgress: function(completed, totalSize, progressBarNum) {
      console.log("updateProgress");
        // var progressBar = document.querySelector('#' + upload.getPBId(progressBarNum));
        // var percentage  = 100 * completed / totalSize;
        // progressBar.setAttribute('value', percentage);
    },
};
