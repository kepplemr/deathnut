FROM gcr.io/firebase-wellio/charger-apispec-py3.7:latest
LABEL maintainer="mkepple@getwellio.com"
LABEL description="Example Recipe app"

ADD ./recipe_service /recipe_service

CMD ["python" , "/recipe_service/app.py" ]
