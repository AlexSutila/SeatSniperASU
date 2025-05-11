# Start from the official Ubuntu base image
FROM ubuntu:22.04

RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    apt-get clean

WORKDIR /app
COPY . /app

RUN pip install -r requirements.txt
RUN playwright install
RUN playwright install-deps
CMD ["bash"]
