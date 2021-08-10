FROM centos:7

LABEL Author="Pad0y<github.com/Pad0y>"
ENV LANG C.UTF-8 LC_ALL=C.UTF-8

WORKDIR /data/project/


#软件层
#RUN yum -y update \
RUN yum -y install gcc gcc-c++ wget make git libSM-1.2.2-2.el7.x86_64 libXrender libXext\
    && yum -y install zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel gdbm-devel db4-devel libpcap-devel xz-devel libffi-devel \
    && yum -y install python3-devel centos-release-scl scl-utils-build \
    && yum -y install  devtoolset-7-gcc* \
    && echo 'source /opt/rh/devtoolset-7/enable' >> ~/.bash_profile \
    && source ~/.bash_profile \
    && scl enable devtoolset-7 bash 

RUN pip3 install --user  -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple/  \ 
    && pip3 config set global.index-url https://mirrors.aliyun.com/pypi/simple/ 

#依赖层
COPY requirements.txt .
RUN source ~/.bash_profile && pip3 install -r requirements.txt

#代码层
COPY . .

#原有端口（不知用途）
EXPOSE 5000
EXPOSE 8000
#部署端口
EXPOSE 8080

ENTRYPOINT  ["python3", "backend/main.py"]