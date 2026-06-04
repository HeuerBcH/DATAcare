# React Frontend (Vite)
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build application
RUN npm run build

# Stage 2: Serve with Nginx
FROM node:18-alpine

WORKDIR /app

# Install dependencies for serving
RUN npm install -g vite

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 3000
EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host"]
