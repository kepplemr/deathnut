FROM gcr.io/firebase-wellio/charger-apispec-py3.7:latest
LABEL maintainer="mkepple@getwellio.com"
LABEL description="Example Recipe app"

ADD ./recipe-service /recipe-service
WORKDIR /recipe-service

RUN pip install redis==3.3.11
RUN pip install flask-restplus~=0.12.1
RUN pip install falcon==2.0.0
RUN pip install falcon-apispec==0.3.0
RUN pip install fastapi==0.49.0
RUN pip install uvicorn==0.11.3

ENV PYTHONPATH $PYTHONPATH:/recipe-service
ENV PYTHONPATH $PYTHONPATH:/

EXPOSE 80

CMD ["tail", "-f", "/dev/null"]
