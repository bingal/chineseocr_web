FROM node:12.22.1-alpine as builder

WORKDIR /data/project/backend/frontend

COPY backend/frontend/package*.json ./
RUN npm config set registry https://registry.npm.taobao.org/ && npm install
COPY backend/frontend/.* .
RUN npm run build


FROM python:3.6

LABEL Author="Pad0y<github.com/Pad0y>"
ENV LANG C.UTF-8 LC_ALL=C.UTF-8

WORKDIR /data/project/

#依赖层
COPY requirements.txt .
RUN pip3 install -r requirements.txt --no-cache-dir --index-url=https://mirrors.aliyun.com/pypi/simple/ 

#代码层
COPY . .
RUN rm -rf /data/project/backend/frontend
COPY --from=builder /data/project/backend/frontend backend/

#原有端口（不知用途）
EXPOSE 5000
EXPOSE 8000
#部署端口
EXPOSE 8080

ENTRYPOINT  ["python3", "backend/main.py"]