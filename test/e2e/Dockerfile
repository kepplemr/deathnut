FROM gcr.io/firebase-wellio/charger-apispec-py3.7:latest
LABEL maintainer="mkepple@getwellio.com"
LABEL description="Example Recipe app"

ADD ./recipe-service /recipe-service
WORKDIR /recipe-service

RUN pip install redis==3.3.11
RUN pip install flask-restplus~=0.12.1

ENV PYTHONPATH $PYTHONPATH:/recipe-service
ENV PYTHONPATH $PYTHONPATH:/

EXPOSE 80

CMD ["python" , "/recipe-service/flask/app-apispec.py", "--generate-openapi-template"]
