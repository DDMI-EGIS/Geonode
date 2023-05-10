FROM nginx:1.23.3-alpine

RUN apk add --no-cache openssl inotify-tools

WORKDIR /etc/nginx/

COPY nginx.conf.envsubst nginx.https.available.conf.envsubst ./
COPY geonode.conf.envsubst ./sites-enabled/

ADD docker-autoreload.sh docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
RUN chmod +x /docker-autoreload.sh
RUN chmod +x /docker-entrypoint.sh

CMD ["nginx", "-g", "daemon off;"]
