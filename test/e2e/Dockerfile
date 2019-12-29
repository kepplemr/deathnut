FROM gcr.io/firebase-wellio/charger-apispec-py3.7:latest
LABEL maintainer="mkepple@getwellio.com"
LABEL description="Example Recipe app"

ADD ./recipe-service /recipe-service

RUN mkdir -p /recipe-service/deploy/openapi

ENV PYTHONPATH $PYTHONPATH:/recipe-service

EXPOSE 80

CMD ["python" , "/recipe-service/app.py" ]
