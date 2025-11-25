FROM node:16-alpine

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
RUN npm run build

EXPOSE 80
CMD ["npx", "serve", "-s", "build", "-l", "80"]
