# ---------- 构建阶段 ----------
FROM node:20-alpine AS build
WORKDIR /app

# 必须连 package-lock.json 一起拷贝，并用 npm ci：
# 只拷 package.json + npm install 会忽略锁文件、每次重新求解版本，构建结果不可复现。
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .
RUN npm run build

# ---------- 运行阶段 ----------
FROM nginx:1.25-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
