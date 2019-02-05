ReadMe of <rally-repo>/etc/docker dir
=====================================

We are using automated docker image builds on `Docker Hub
<https://hub.docker.com/>`_ which allows to reduce time of making new releases.

Docker Hub has one specific feature - each time it builds new image, it
updates the description of the image. The description it takes from README file
of the same directory as Dockerfile is located. That is why Dockerfile is
placed to the separate directory with 2 README files: one for Docker Hub,
another one (this one) for explanation of situation.
