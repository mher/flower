FROM ubuntu:12.04

RUN apt-get update
RUN apt-get install -y wget ca-certificates

# Install pip
RUN cd /tmp; wget https://raw.github.com/pypa/pip/master/contrib/get-pip.py;\
 python get-pip.py; rm get-pip.py;

# Install pip via package-manager 
RUN apt-get install -y python-pip

# add flower
RUN pip install redis flower

