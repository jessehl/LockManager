# base image
#!/bin/bash

FROM ubuntu:latest AS base

# install cmake, gcc, g++, boost, and git
FROM base AS builder
RUN apt-get update &&\
    apt-get install -yq cmake gcc g++ &&\
    apt-get install -yq libcurl4-openssl-dev &&\
    apt-get install -yq libjsoncpp-dev &&\
    apt-get install -yq libboost-all-dev &&\
    apt-get install -yq libssl-dev &&\
    apt-get install -yq git &&\
# make a directory we will place DD in
    mkdir DoubleDutch
WORKDIR /DoubleDutch

# get crow's include/ dir
RUN git clone --branch v0.3 https://github.com/CrowCpp/crow &&\
    cp -r crow/include include &&\
# make a directory we'll use to build
    mkdir build

# copy all of the source files to the image
COPY ./ ./

# build
WORKDIR /DoubleDutch/build
RUN cmake .. &&\
    make

FROM base AS finalimage
COPY --from=builder /DoubleDutch/config.txt /
COPY --from=builder /DoubleDutch/build/src/server /

FROM finalimage AS dev
CMD [ "/bin/bash" ]

# Run tests in a Python image based on ubuntu.
FROM fnndsc/ubuntu-python3:ubuntu20.04-python3.8.10 as test
COPY --from=finalimage /config.txt /
COPY --from=finalimage /server /

WORKDIR /DoubleDutch/build
RUN pip install requests pytest
COPY tests/test_server.py test_server.py
RUN pytest
RUN echo "tests completed" >> /test_results.log

FROM finalimage AS production
COPY --from curlimages/curl:latest /usr/bin/curl /usr/bin/curl
COPY --from=test /test_results.log /test_results.log
ENTRYPOINT ["/server"]
