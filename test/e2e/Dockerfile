FROM gcr.io/firebase-wellio/charger-apispec-py3.7:latest
LABEL maintainer="mkepple@getwellio.com"
LABEL description="Example Recipe app"

ADD ./recipe_service /recipe_service

RUN mkdir -p /recipe_service/deploy/openapi
WORKDIR /recipe_service

EXPOSE 80

CMD ["python" , "/recipe_service/app.py" ]
