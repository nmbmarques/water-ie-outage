# Dockerfile
FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install --only=production

# Copy app code
COPY server.js ./server.js
COPY public ./public

EXPOSE 3000

CMD ["npm", "start"]
