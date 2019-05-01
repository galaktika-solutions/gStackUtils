# gstackutils

## The workhorse of the `galaktika.gstack` project.

The project `gstack` is boilerplate or even a meta-framework that helps the
setup and operation of a single host Django web application deployment based on
Docker.

The software stack `gstack` refers to consists of the following:

- Postgresql as the backend database
- Django as the application server
- Nginx as the webserver

Based on the experience of maintaining and operating business critical Django
applications based on Docker we collected some common functions and patterns
and wrapped them in this python package.
