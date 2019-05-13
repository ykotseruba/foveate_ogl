FROM nvidia/cuda:10.0-cudnn7-devel-ubuntu16.04
#FROM tensorflow/tensorflow:1.13.0rc1-gpu-py3

ENV FOV_ROOT="/opt/FOV_ROOT"

################################################################################
# Prerequisites
################################################################################

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -yq \
    python3-pip python3-pillow 

#COPY requirements.txt FOV_ROOT/
WORKDIR FOV_ROOT

RUN pip3 install --upgrade pip
RUN pip3 install matplotlib numpy scipy PyOpenGL PyOpenGL_accelerate
RUN pip3 install simpleparse numpy "OpenGLContext==2.2.0a3" pydispatcher pillow

#RUN pip3 install -r requirements.txt
#RUN pip3 install pycuda==2017.1.1

#ENV PYTHONPATH=$FOV_ROOT/contrib/SALICONtf/src/:$PYTHONPATH
WORKDIR $FOV_ROOT

