FROM node:20-alpine
WORKDIR /app
COPY package.json tsconfig.json vite.config.ts ./
RUN npm install
COPY index.html ./
COPY src ./src
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
